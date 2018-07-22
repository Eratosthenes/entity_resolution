import re
import trie
import csv
import pickle
import time
import os
import pdb
import string
from fuzzywuzzy import fuzz 
from collections import defaultdict
from collections import OrderedDict

# decorator for timing
def time_fun(f):
    def run(*args):
        start = time.time()
        r = f(*args)
        print('%r: %2.2f s' % (f.__name__, time.time() - start))
        return r
    return run

# takes about 10 sec with pickled data, about 30 sec without
@time_fun
def read_data():
    # if indexed files do not yet exist, create them
    filenames = os.listdir()    
    if ('pol_data.p' in filenames) and ('res_data.p' in filenames):
        print('reading pickled data...')
        with open('pol_data.p', 'rb') as handle:
            pol_data = pickle.load(handle)
        with open('res_data.p', 'rb') as handle:
            res_data = pickle.load(handle)
    else:
        print('reading csv data...')
        res_data = read_res_data('resume_data_vendor.csv')
        pol_data = read_pol_data('political_data_vendor.csv')

        print('pickling data...')
        with open('pol_data.p', 'wb') as handle:
            pickle.dump(pol_data, handle, protocol=pickle.HIGHEST_PROTOCOL)
        with open('res_data.p', 'wb') as handle:
            pickle.dump(res_data, handle, protocol=pickle.HIGHEST_PROTOCOL)

    return pol_data, res_data

# pre-process full_name feature
def process_name(first, last):
    full_name = ' '.join([first, last]).lstrip().split(',')[0] # remove education and jr/sr
    return re.sub(r'[^\w\s-]', '', full_name) # strip punctuation except for hyphens

# return political data as an ordered dictionary
@time_fun
def read_pol_data(filename):
    reader = csv.reader(open(filename, 'r'))
    d = defaultdict(list)
    for i, row in enumerate(reader):
        if i == 0:
            continue
        pol_id, first, last, city, birth_year, gender = row
        full_name = process_name(first, last) 
        birth_year = int(birth_year) if birth_year != '' else None
        d[full_name] += [{'political_id': pol_id, 'city': city, 'birth_year': birth_year}]
    return OrderedDict(sorted(d.items(), key=lambda x: x))

# return resume data as a dictionary
@time_fun
def read_res_data(filename):
    reader = csv.reader(open(filename, 'r'), escapechar='\\')
    d = defaultdict(list)
    for i, row in enumerate(reader):
        if i == 0: 
            continue
        try:
            res_id, first, last, degree, degree_start, local_region = row
        except:
            pdb.set_trace()
        full_name = process_name(first, last) 
        city = local_region.split(',')[0]
        birth_year_est = int(degree_start) - 17 if degree_start != '' else None
        d[full_name] += [{'resume_id': res_id, 'city': city, 'birth_year_est': birth_year_est}]
    return d

# calculating scores to determine entity resolution
@time_fun
def calculate_scores(pol_data, res_data):
    # calculate name_score, city_score, birth_year score for names in res_data
    match_d = defaultdict(dict)
    pol_names = list(pol_data.keys()) # names in political data
    trie = build_trie(pol_names)

    print('calculating match scores...')
    for name in res_data.keys():
        if pol_data.get(name): # if there is a direct name match
            for res_d in res_data[name]:
                res_id = res_d['resume_id']
                for pol_d in pol_data[name]:
                    pol_id = pol_d['political_id']
                    match_d[res_id][pol_id] = {'name_score': 1, 'res_name': name, 'pol_name': name} 
                    check_city_match(match_d, res_d, pol_d, res_id, pol_id)
                    check_birth_year_match(match_d, res_d, pol_d, res_id, pol_id)
        else: # search for fuzzy match
            for res_d in res_data[name]:
                res_id = res_d['resume_id']
                chunk = make_chunk(trie, pol_names, name) # chunk of names in pol_data to check
                name_score, best_name = find_best_match(name, chunk)
                if name_score == 0 or best_name == '': # no name data or no fuzzy match
                    break 
                # NOTE: this gets expensive when there are a lot of duplicate
                # names for res and pol
                for pol_d in pol_data[best_name]: 
                    pol_id = pol_d['political_id']
                    match_d[res_id][pol_id] = {'name_score': name_score, 'res_name': name, 'pol_name': best_name} 
                    check_city_match(match_d, res_d, pol_d, res_id, pol_id)
                    check_birth_year_match(match_d, res_d, pol_d, res_id, pol_id)
    
    print('scores calculated for all potential matches!')
    return match_d

# build a trie from the names in the political data
# could pickle it, but it takes longer to read the pickle than to build
# takes 120ish seconds to run
@time_fun
def build_trie(pol_names):
    print('building trie...')
    t = trie.Trie()
    for i, name in enumerate(pol_names):
        t.add(name, i)
    return t

# find best match in a chunk
def find_best_match(name, chunk):
    best_ratio, best_name = 0, '' 
    ratios = []
    for pol_name in chunk:
        ratio = fuzz.ratio(name, pol_name) / 100
        ratios.append((ratio, pol_name))
        if ratio > best_ratio:
            best_ratio = ratio
            best_name = pol_name
    match = best_ratio if best_ratio > 0.80 else 0
    return match, best_name
    
# chunk of names to search over in political names
def make_chunk(trie, pol_names, name):
    idx = trie.find(name)
    if idx == None: # happens if name is an empty string
        return [] # don't bother searching
    max_bound, min_bound = min(len(pol_names), idx + 100), max(0, idx - 100)
    return pol_names[min_bound:max_bound] # fuzzy match on 200 names

# calculate score for birth_year match
def check_birth_year_match(match_d, res_d, pol_d, res_id, pol_id):
    if res_d.get('birth_year_est') and pol_d.get('birth_year'): 
        match = 1 if (pol_d['birth_year'] - res_d['birth_year_est'] >= 0) \
                and (pol_d['birth_year'] - res_d['birth_year_est'] <= 12) \
                else 0
    else:
        match = 0.5 # missing data, so there might be a match

    match_d[res_id][pol_id]['birth_score'] = match
    return match_d

# calculate score for city match
def check_city_match(match_d, res_d, pol_d, res_id, pol_id):
    match = 1 if res_d['city'] == pol_d['city'] else 0
    match_d[res_id][pol_id]['city_score'] = match
    return match_d

# check to see if you've already calculated the match dictionary :)
def check_for_match_d(pol_data, res_data):
    filenames = os.listdir()    
    if 'match_d.p' in os.listdir():
        print('reading pickled match_d...')
        with open('match_d.p', 'rb') as handle:
            match_d = pickle.load(handle)
    else:
        print('calculating match scores...')
        match_d = calculate_scores(pol_data, res_data)

        print('pickling match_d...')
        with open('match_d.p', 'wb') as handle:
            pickle.dump(match_d, handle, protocol=pickle.HIGHEST_PROTOCOL)

    return match_d

# analyze match dictionary and produce matches.csv and ambiguous_matches.csv
@time_fun
def analyze_match_dictionary(match_d, pol_data, res_data):
    # res_names dictionary to create uniqueness score
    res_names_d = defaultdict(int)
    for res_id, item in match_d.items():
        pol_id = list(item.keys())[0]
        res_name = item[pol_id]['res_name']
        res_names_d[res_name] += 1

    # sort match_d in to matches and ambiguous matches
    header = ['resume_id','political_id','resume_name','political_name','name_score','uniqueness_score','city_score','birth_score']
    match_rows = []
    ambiguous_match_rows = []
    for res_id, item in match_d.items():
        pol_id = list(item.keys())[0]
        pol_name, res_name = item[pol_id]['pol_name'], item[pol_id]['res_name']
        name_score, city_score, birth_score = item[pol_id]['name_score'], item[pol_id]['city_score'], item[pol_id]['birth_score']
        uniq_score = 1 / res_names_d[res_name]
        row = list(map(str, [res_id, pol_id, res_name, pol_name, name_score, uniq_score, city_score, birth_score]))

        tot_score = name_score + uniq_score + city_score + birth_score
        # everything matches
        # name match + unique + city match
        # partial name match + everything else
        if tot_score >= 3:
            match_rows.append(row)
        # variety of partial match combos
        if tot_score >= 2.5 and tot_score < 3: 
            ambiguous_match_rows.append(row)
    
    with open('matches.csv', 'w') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for row in match_rows:
            writer.writerow(row)

    with open('ambiguous_matches.csv', 'w') as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for row in ambiguous_match_rows:
            writer.writerow(row)
    
    print('clear matches = %2.2f%s' % (100 * len(match_rows) / len(res_data), '%'))
    print('ambiguous matches = %2.2f%s' % (100 * len(ambiguous_match_rows) / len(res_data), '%'))
    print('clear + ambiguous matches = %2.2f%s' % (100 * (len(match_rows) + len(ambiguous_match_rows)) / len(res_data), '%'))

@time_fun
def main():
    pol_data, res_data = read_data()
    match_d = check_for_match_d(pol_data, res_data)
    analyze_match_dictionary(match_d, pol_data, res_data)

if __name__=='__main__':
    main()
