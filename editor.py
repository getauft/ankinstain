import pickle
import sys
import getopt
import json

word = None

try:
    opts, args = getopt.getopt(sys.argv[1:], "w:", ["word="])
except getopt.GetoptError:
    print('editor.py -w <word>')
    sys.exit(2)
for opt, arg in opts:
    if opt == '-w':
        word = arg

def save(translate_word_object):
    with open('cache/words/' + translate_word_object['english'].lower() + '.pkl', 'wb') as output:
        pickle.dump(translate_word_object, output, pickle.HIGHEST_PROTOCOL) 

def load(word):
    with open('cache/words/' + word + '.pkl', 'rb') as input:
        return pickle.load(input)

if(word is not None):   
    word_object = load(word)
    print('1','english —',word_object['english'])
    print('2','word forms —',word_object['word_forms']['description'])
    print('3','transcription —',word_object['transcription'])
    print('4','russian —',word_object['russian'])
    i = input('Enter the item number: ')
    if(len(i) == 0):
        sys.exit()
    if(int(i) == 1):
        word_object['english'] = input('Enter new English word: ')
    elif(int(i) == 2):
        word_object['word_forms']['description'] = input('Enter new word forms: ')
    elif(int(i) == 3):
        word_object['transcription'] = input('Enter new word transcription: ')
    elif(int(i) == 4):
        word_object['russian'] = input('Enter new word translate: ')
    else:
        sys.exit()
    save(word_object)
