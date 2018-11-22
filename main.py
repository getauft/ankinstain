from bs4 import BeautifulSoup
import urllib
import urllib.request
import re
import pickle
import os, sys
import string
import genanki
from random import randint
from tqdm import tqdm
import json
from pymystem3 import Mystem

txt_file_name = 'words.txt'
deck_name = 'English words'
package_name = 'English words'

#txt_file_name = 'top200verbs.txt'
#deck_name = '200 Most Common Verbs'
#package_name = '200 Most Common Verbs'


if not os.path.exists('cache'):
    os.makedirs('cache')
if not os.path.exists('cache/words/'):
    os.makedirs('cache/words/')

class WORKER(object):
    def get_source_word_list(self, file_name):
        if os.path.exists(file_name): 
            raw = open(file_name, 'r')
            text = raw.readlines()
        else:
            print('ERROR! FILE NOT FOUND.')
            sys.exit()
        word_list = []
        for line in text:
            _word = line.replace('\n', '', 1).strip()
            if(len(_word)>0 and _word not in word_list):
                word_list.append(_word.strip().lower())
        word_list.sort()
        return word_list
    def translate_word(self, word):        
        if os.path.exists('cache/words/' + word + '.pkl'):
            return self.load(word)
        
        soup = BeautifulSoup(urllib.request.urlopen('https://wooordhunt.ru/word/' + word).read(), 'html.parser')
        word_translated = None
        
        def _check_exist(soup):
            if(soup.find(id='word_not_found') is None):
                return True
            else:
                return False
        
        def _get_context(soup):
            context = []
            if(soup.find('h3',text='Примеры')):
                if(soup.find('h3',text='Примеры').next_sibling.next_sibling):
                    context_block = soup.find('h3',text='Примеры').next_sibling.next_sibling
                    context_item_english = context_block.findAll(class_='ex_o')
                    context_item_russian = context_block.findAll(class_='ex_t human')   
                    if(
                        len(context_block.findAll(class_='ex_o'))>0 and 
                        len(context_block.findAll(class_='ex_t human'))>0 and
                        len(context_block.findAll(class_='ex_o')) == len(context_block.findAll(class_='ex_t human'))
                    ):
                        for idx in range(0, len(context_item_english)-1):
                            context.append(
                                {
                                    'eng':context_item_english[idx].text.strip(),
                                    'rus':context_item_russian[idx].text.replace('☰','',1).strip()
                                }
                            )
            return (context, [{'eng': '','rus': ''}])[len(context) == 0]
        
        def _get_english(soup, word = None):
            english = None
            if(word is not None and soup.title.text.lower().strip() == word.lower().strip()):
                english = soup.title.text.lower().strip()
            elif(re.match(r'(\S*):.*', soup.title.text)):
                english = re.match(r'(\S*):.*', soup.title.text).group(1).lower().strip()
            elif(soup.find('h1').text.replace(' - перевод на русский','',1).strip()):
                english = soup.find('h1').text.replace(' - перевод на русский','',1).lower().strip()
            return english
        def _get_transcription(soup):
            transcription = ''
            if(soup.find(id='us_tr_sound')):
                if(soup.find(id='us_tr_sound').find(class_='transcription')):
                    transcription = soup.find(id='us_tr_sound').find(class_='transcription').text.replace('|','',2).strip()
            return transcription
        
        def _get_russian(soup, word = None):
            russian = None
            if(soup.find(class_='t_inline_en')):
                if(word is not None):
                    yandex_url = "https://translate.yandex.net/api/v1.5/tr.json/translate?lang=en-ru&format=plain&key=trnsl.1.1.20181026T095610Z.0f9e5b3c50d78498.83dff75a74e7d95e0712640c87b207295ef8842a&text=" + word.replace(' ','%20')
                    yandex_url_to = "https://translate.yandex.net/api/v1.5/tr.json/translate?lang=en-ru&format=plain&key=trnsl.1.1.20181026T095610Z.0f9e5b3c50d78498.83dff75a74e7d95e0712640c87b207295ef8842a&text=" +'to%20' + word.replace(' ','%20')
                    yandex_translate = urllib.request.urlopen(yandex_url).read()
                    yandex_translate_to = urllib.request.urlopen(yandex_url_to).read()
                    yd = json.loads(yandex_translate.decode("utf-8"))['text'][0].replace('чтобы','',1).strip().replace('себе','',1).strip()
                    yd_to = json.loads(yandex_translate_to.decode("utf-8"))['text'][0]
                    russian = soup.find(class_='t_inline_en').text.replace('\u2002',' ').replace('  ',' ').strip()
                    mystem = Mystem()
                    lemmas = mystem.lemmatize(yd)                    
                    ws = russian.split(',')
                    b = False
                    for idx in range(1, 3):
                        for w in ws:
                            if((not w.find(yd[:-idx]) == -1 or not w.find(lemmas[0][:-idx]) == -1) and b == False):
                                russian = russian.replace(w,'<b>' + w.upper() + '</b>', 1)
                                b = True                             
                    if(b == False):
                        wsl = ''
                        for idw, w in enumerate(ws):
                            wsl += str(idw) + ' — ' + w + ', '                  
                        ii = input('Выберети основной перевод слова «' + word + ' (to ' + word + ')» — «'+ yd + ' ('+ yd_to + ')»:\n' + wsl[:-2] + ': ')
                        russian = russian.replace(ws[int(ii)],'<b>' + ws[int(ii)].upper() + '</b>', 1)
                        print(russian)
                else:
                    russian = soup.find(class_='t_inline_en').text.replace('\u2002',' ').replace('  ',' ').strip()
            elif(soup.find(class_='light_tr')):
                russian = soup.find(class_='light_tr').text.replace('\u2002',' ').replace('  ',' ').strip()
            return russian
        
        def _get_word_forms(soup):
            word_forms = {'description':'','links': []}
            if(soup.find(id='word_forms')):
                word_forms['description'] = soup.find(id='word_forms').text.replace('\u2002',' ').replace('  ',' ').strip(),
                for link in soup.find(id='word_forms').findAll('a', href=True):
                    if(link['href'] not in word_forms['links']):
                        word_forms['links'].append(link['href'])
            return word_forms
        def _get_sound(soup, word):
            sound = {
                'us': '',
                'uk': ''
            }
            def __download(pref, word): 
                mp3 = b''
                if(len(word.split())==1):
                    response = urllib.request.urlopen('https://wooordhunt.ru/data/sound/word/' + pref + '/mp3/' + word + '.mp3')
                    if(response.headers['Content-Type'] == 'audio/mpeg'):
                        mp3 = response.read() 
                else:
                    for item in word.split():
                        response = urllib.request.urlopen('https://wooordhunt.ru/data/sound/word/' + pref + '/mp3/' + item + '.mp3')
                        if(response.headers['Content-Type'] == 'audio/mpeg'):
                            mp3 += response.read() 
                return mp3
            sound['us'] = __download('us', word)
            sound['uk'] = __download('uk', word)  
            return sound    
        
        
        if(_check_exist(soup) and _get_russian(soup) is not None):
            word_translated = {
                'english': _get_english(soup, word),
                'transcription':  _get_transcription(soup),
                'word_forms': _get_word_forms(soup),
                'context': _get_context(soup),
                'russian': _get_russian(soup, word),
                'audio': _get_sound(soup, word),
            }
        self.save(word_translated)
        return word_translated    
    
    def save(self, translate_word_object):
        with open('cache/words/' + translate_word_object['english'].lower() + '.pkl', 'wb') as output:
            pickle.dump(translate_word_object, output, pickle.HIGHEST_PROTOCOL) 
    
    def load(self, word):
        with open('cache/words/' + word + '.pkl', 'rb') as input:
            return pickle.load(input)   
    
    def extract_audio(self, translate_word_object, us = True, uk = False):
        extracted_us = False
        extracted_uk = False
        if(us and translate_word_object['audio']['us']):
            open(translate_word_object['english'].lower().replace(' ','_') + '_us.mp3','wb').write(translate_word_object['audio']['us'])
            extracted_us = True
        if(uk and translate_word_object['audio']['uk']):
            open(translate_word_object['english'].lower().replace(' ','_') + '_uk.mp3','wb').write(translate_word_object['audio']['uk'])
            extracted_uk = True
        return {'us':extracted_us,'uk':extracted_uk}
    def make_anki_deck(self, translated_words, need_reverse_card = False):
        model_id = 1607392319
        model_name = 'ankinstain_english'
        fields = [
            {'name': 'english'},
            {'name': 'russian'},
            {'name': 'transcription'},
            {'name': 'audio'},
            {'name': 'image'},
            {'name': 'context_rus'},
            {'name': 'context_eng'},
            {'name': 'word_forms'}
        ]
        templates = [
            {
                'name': 'ertai2cw',
                'qfmt': '<table id="main_table"><thead><tr id="english"><th>&nbsp;{{english}}&nbsp;</th></tr></thead><tbody><tr id="transcription"><td>&nbsp;{{transcription}}&nbsp;</td></tr><tr id="word_forms"><td>&nbsp;{{word_forms}}&nbsp;</td></tr><tr id="russian" class="hidden"><td>&nbsp;{{russian}}&nbsp;</td></tr><tr id="context_eng"><td>&nbsp;{{context_eng}}&nbsp;</td></tr><tr id="context_rus" class="hidden"><td>&nbsp;{{context_rus}}&nbsp;</td></tr><tr height=200px id="image" class="hidden"><td>{{image}}</td></tr></tbody><tfoot><tr id="audio"><td>&nbsp;{{audio}}&nbsp;</td></tr></tfoot></table>',
    
                'afmt': '<table id="main_table"><thead><tr id="english"><th>&nbsp;{{english}}&nbsp;</th></tr></thead><tbody><tr id="transcription"><td>&nbsp;{{transcription}}&nbsp;</td></tr><tr id="word_forms"><td>&nbsp;{{word_forms}}&nbsp;</td></tr><tr id="russian"><td>&nbsp;{{russian}}&nbsp;</td></tr><tr id="context_eng"><td>&nbsp;{{context_eng}}&nbsp;</td></tr><tr id="context_rus"><td>&nbsp;{{context_rus}}&nbsp;</td></tr><tr id="image" height=200px><td>{{image}}</td></tr></tbody><tfoot><tr id="audio"><td>&nbsp;{{audio}}&nbsp;</td></tr></tfoot></table>',
            }
        ]
        css = 'b{color:#E86F6F; font-size:110%}#main_table{width:100%;height:100%;min-height:100%;position:absolute;bottom:0;top:0;left:0;right:0;text-align:center}#image img{width:auto;max-width:100%;border-radius:5%}#english{font-size:150%;font-weight:700;text-transform:uppercase;color:#1b98f8}#transcription{color:#999;font-size:120%}#word_forms{color:#1b98f9;opacity:.7}#russian{color:#5aba59}#context_eng,#context_rus{font-style:italic}#context_rus{color:#5aba59}.hidden{visibility:hidden}'
        model = genanki.Model(model_id, model_name, fields, templates, css)
        deck = genanki.Deck(randint(1000000000, 9999999999), deck_name + ' (eng)')
        local_media_list = []    
        print('Заполнение колоды #1')
        for translated_word in tqdm(translated_words, bar_format = bar_format):
            extracted = self.extract_audio(translated_word)
            if(extracted['us']):
                local_media_list.append(translated_word['english'].replace(' ','_') + '_us.mp3')
            if(extracted['uk']):
                local_media_list.append(translated_word['english'].replace(' ','_') + '_uk.mp3')                          
            fields = [
                str(translated_word['english']),
                str(translated_word['russian']),
                str(translated_word['transcription']),
                str('[sound:' + translated_word['english'].replace(' ','_') + '_us.mp3' + ']'),
                str(''),
                str(translated_word['context'][0]['rus']),
                str(translated_word['context'][0]['eng']),
                str(translated_word['word_forms']['description'])
            ]
            note = genanki.Note(
                model=model,
                fields=fields
            )
            deck.add_note(note)   
        package = genanki.Package(deck)
        package.media_files = local_media_list
        package.write_to_file(package_name + ' (eng).apkg')
        
        model_id_reverse = 1607392320
        model_name_reverse = 'ankinstain_russian'
        fields_reverse = [
            {'name': 'english_reverse'},
            {'name': 'russian_reverse'},
            {'name': 'transcription_reverse'},
            {'name': 'audio_reverse'},
            {'name': 'image_reverse'},
            {'name': 'word_forms_reverse'}
        ]
        templates_reverse = [
            {
                'name': 'ertai2cwr',
                'qfmt': '<table id="main_table"><thead><tr id="english" class="hidden"><th>&nbsp;{{english_reverse}}&nbsp;</th></tr></thead><tbody><tr id="transcription" class="hidden"><td>&nbsp;{{transcription_reverse}}&nbsp;</td></tr><tr id="word_forms" class="hidden"><td>&nbsp;{{word_forms_reverse}}&nbsp;</td></tr><tr id="russian"><td>&nbsp;{{russian_reverse}}&nbsp;</td></tr><tr id="image"><td>{{image_reverse}}</td></tr></tbody><tfoot><tr id="audio"><td>&nbsp;</td></tr></tfoot></table>',

                'afmt': '<table id="main_table"><thead><tr id="english"><th>&nbsp;{{english_reverse}}&nbsp;</th></tr></thead><tbody><tr id="transcription"><td>&nbsp;{{transcription_reverse}}&nbsp;</td></tr><tr id="word_forms"><td>&nbsp;{{word_forms_reverse}}&nbsp;</td></tr><tr id="russian"><td>&nbsp;{{russian_reverse}}&nbsp;</td></tr><tr id="image" height=200px><td>{{image_reverse}}</td></tr></tbody><tfoot><tr id="audio"><td>&nbsp;{{audio_reverse}}&nbsp;</td></tr></tfoot></table>',
            }
        ]
        css_reverse = 'b{color:#E86F6F; font-size:110%}#main_table{width:100%;height:100%;min-height:100%;position:absolute;bottom:0;top:0;left:0;right:0;text-align:center}#image img{width:auto;max-width:100%;border-radius:5%}#english{font-size:150%;font-weight:700;text-transform:uppercase;color:#1b98f8}#transcription{color:#999;font-size:120%}#word_forms{color:#1b98f9;opacity:.7}#russian{color:#5aba59}#context_eng,#context_rus{font-style:italic}#context_rus{color:#5aba59}.hidden{visibility:hidden}'
        model_reverse = genanki.Model(model_id_reverse, model_name_reverse, fields_reverse, templates_reverse, css_reverse)
        deck_reverse = genanki.Deck(randint(1000000000, 9999999999), deck_name + ' (rus)')         
        print('Заполнение колоды #2')
        for translated_word in tqdm(translated_words, bar_format = bar_format):
            fields_reverse = [
                str(translated_word['english']),
                str(translated_word['russian']),
                str(translated_word['transcription']),
                str('[sound:' + translated_word['english'].replace(' ','_') + '_us.mp3' + ']'),
                str(''),
                str(translated_word['word_forms']['description'])
            ]
            note_reverse = genanki.Note(
                model=model_reverse,
                fields=fields_reverse
            )
            deck_reverse.add_note(note_reverse)        
        package_reverse = genanki.Package(deck_reverse)
        package_reverse.media_files = local_media_list
        package_reverse.write_to_file(package_name + ' (rus).apkg')        
        print('Удаление временных файлов')
        for file in tqdm(local_media_list, bar_format = bar_format):
            if os.path.exists(file):
                os.remove(file)
                
        return
        
worker = WORKER()

source_word_list = worker.get_source_word_list(txt_file_name)
translated_word_list = []
print('Перевод',len(source_word_list), 'слов:',', '.join(source_word_list))
bar_format='{desc}{percentage:3.0f}%|{bar}|[{n_fmt}/{total_fmt} {elapsed}<{remaining}]'
for _word in tqdm(source_word_list, bar_format = bar_format):
    tw = worker.translate_word(_word)
    translated_word_list.append(tw)


worker.make_anki_deck(translated_word_list)
    
