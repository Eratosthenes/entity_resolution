import pdb
import re

class Trie():
    """ Create a trie from a sorted list of words """
    
    def __init__(self, char='*'):
        self.char = char
        self.children = []
        self.idx = None 
        self.words = []

    def add(self, word, idx): 
        """
        Add a word to the trie
        idx =: index of the word being added
        """
        word = re.sub('\s', '', word)
        self.words += [word]
        node = self
        for char in word:
            found_in_child = False

            # search for the character in the children of the present `node`
            for child in node.children:
                if child.char == char:
                    node = child
                    if node.idx == None:
                        node.idx = idx
                    found_in_child = True
                    break

            # we did not find it so add a new chlid
            if not found_in_child:
                new_node = Trie(char)
                node.children.append(new_node)
                node = new_node
                node.idx = idx

    def find(self, prefix):
        """ Returns the first index from the set of words that contain the prefix """
        word = re.sub('\s', '', prefix)
        node = self
        if not self.children:
            return 

        for char in prefix:
            for child in node.children:
                if child.char == char:
                    node = child
                    break # go to next character

        return node.idx 

if __name__ == "__main__":
    words = open('/usr/share/dict/words').read().splitlines()
    root = Trie()
    for i, word in enumerate(words[:10]):
        root.add(word, i)

    for word in words[:10]:
        print('{}: {}'.format(word, root.find(word)))

    print('{}: {}'.format('aa', root.find('aa')))
    print('{}: {}'.format('aarmed', root.find('aarmed')))
    pdb.set_trace()
