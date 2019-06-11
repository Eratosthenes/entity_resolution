# given a word, quickly find the best approximate matching word from a large list
from trie import Trie
import time
from fuzzywuzzy import fuzz 
from tabulate import tabulate
from misspellings import word_pairs

def build_trie(words):
    """ Return a trie built from a set of 235,886 words """

    print('building trie...')
    root = Trie()
    for i, word in enumerate(words):
        root.add(word, i)
    print('done\n')
    return root

def find_best_match(misspelling, chunk):
    """ find best match in a chunk """
    best_ratio, best_word = 0, '' 
    ratios = []
    for word in chunk:
        ratio = fuzz.ratio(misspelling, word) / 100
        ratios.append((ratio, word))
        if ratio > best_ratio:
            best_ratio = ratio
            best_word = word

    return best_ratio, best_word

def make_chunk(trie, words, word):
    """ Chunk of words to search over in political words """
    idx = trie.find(word)
    max_bound, min_bound = min(len(words), idx + 50), max(0, idx - 50)
    return words[min_bound:max_bound] # fuzzy match on 200 names

def main(words, word_pairs):
    trie = build_trie(words)

    # calculate naive worst case
    start = time.time()
    misspelling = 'pronounciation'
    for word in words:
        fuzz.ratio(misspelling, word)
    elapsed = time.time() - start
    worst_case = round(1000 * elapsed, 2)

    # calculate average case with fast lookup
    rows = []        
    start = time.time()
    for correct, misspelling in word_pairs: 
        chunk = make_chunk(trie, words, misspelling)
        best_ratio, best_word = find_best_match(misspelling, chunk)
        rows.append((misspelling, correct, best_word, best_ratio))
 
    elapsed = time.time() - start
    sorted_rows = sorted(rows, key=lambda x: -x[3])
    avg_case = round(1000 * elapsed / len(word_pairs), 2)
    speedup = round(worst_case/avg_case, 2)

    # print results
    print(tabulate(sorted_rows,
        headers=[
            'Misspelled word',
            'Correct word',
            'Best match found',
            'Match ratio (%)'],
        floatfmt='.3f'))
    
    print('\nnaive worst case: {} ms'.format(worst_case))
    print('fast lookup avg time/word = {} ms'.format(avg_case))
    print('speedup over naive case = {}x'.format(speedup))

if __name__ == '__main__':
    words = open('/usr/share/dict/words').read().splitlines()
    main(words, word_pairs)
