A method for [entity resolution](https://en.wikipedia.org/wiki/Record_linkage)
using a modified trie to retrieve the index of a name in one dataset with the longest 
matching prefix. 
This reduces the complexity of lookup to O(n x m), where n is the pattern length 
and m is the word length. 
The best match is found among multiple matches 
using [Levenshtein edit distance](https://en.wikipedia.org/wiki/Levenshtein_distance). 
