import difflib
import json
import re

import spacy


class CoffeeNlpCore:
    num_map = {}

    def __init__(self, speed: int = 0, menu_file: str = 'coffee_menu.txt'):
        print('Loading spacy model...', end='\r')
        if speed == 0:
            spacy_model = "en_core_web_trf"
        elif speed == 1:
            spacy_model = "en_core_web_lg"
        elif speed == 2:
            spacy_model = "en_core_web_md"
        else:
            spacy_model = "en_core_web_sm"
        self.nlp = spacy.load(spacy_model)
        print(f'Load success! Spacy model: {spacy_model}')
        self.__immediate_num_value__ = 0
        self.__processing_partial_order__ = False
        self.__processing_partial_order_in_result__ = False
        self.__partial_order_name__ = ''
        self.__partial_menu_items__ = set()
        self.complete_menu_items = set()
        self.load_menu(menu_file)

    @classmethod
    def __word2num__(cls, word) -> int:
        """
        Convert numbers in words to integer
        :param word: number in words
        :return: number in integer
        """
        if not CoffeeNlpCore.num_map:
            with open('core/word2num.json') as f:
                cls.num_map = json.load(f)
        return cls.num_map[cls.__get_nearest_word__(word, cls.num_map.keys())]

    @staticmethod
    def __get_nearest_word__(word, keys, cutoff: int = 0.75) -> str:
        """
        Extracts the nearest match word in the keys. If none matches, it will return blank string
        :param word: Word to search
        :param keys: List of words to match with
        :param cutoff: cutoff value 0-1 (Higher indicates stricter matching policy)
        :return: matched word from the keys
        """
        correct_word = difflib.get_close_matches(word, keys, n=1, cutoff=cutoff)
        if not correct_word:
            return ''
        return str(correct_word[0])

    def load_menu(self, menu_file):
        """
        Loads menu from a text file. The menu items need to be line separated
        :param menu_file: path to menu file
        :return: None
        """
        with open(menu_file) as f:
            self.__partial_menu_items__ = set()
            self.complete_menu_items = set()
            for line in f.readlines():
                words = line.lower().split()
                for i in range(len(words) - 1):
                    self.__partial_menu_items__.add(' '.join(words[:i + 1]))
                self.complete_menu_items.add(' '.join(words))

    def parse(self, sent: str):
        """
        Parses simple coffee order strings and returns dictionary of items, store and root verb details
        :param sent: input sentence
        :return: dictionary of 'items', 'store' and 'root_verb'
        """
        result = {'items': []}
        self.__processing_partial_order__ = False
        self.__processing_partial_order_in_result__ = False
        sent = re.sub(r'\b(a|an)\b', 'one', sent)
        processed_sent = self.nlp(sent)
        quantity = 1
        loc = 0
        for word in processed_sent:
            if self.__processing_partial_order__:
                if self.__process_order__(result, word.text, quantity):
                    continue
            if word.text.lower() == 'from' and word.pos_ == 'ADP':
                loc = 1
                result['store'] = ''
                continue
            if word.pos_ == 'VERB' and word.dep_ == 'ROOT':
                if 'root_verb' not in result:
                    result['root_verb'] = ''
                result['root_verb'] += word.text
            elif word.pos_ == 'NUM':
                quantity = self.__get_number__(word.text, word.dep_)
            elif loc == 1 and (word.pos_ == 'NOUN' or word.pos_ == 'PROPN'):
                result['store'] = result['store'] + ' ' + word.text  # multi worded store name
                continue
            else:
                self.__process_order__(result, word.text, quantity)
            loc = 0
        return result

    def __process_order__(self, result, word, quantity):
        """
        Internal function to process orders and add to result dictionary
        :param result: result dictionary to work with
        :param word: word to match with menu items
        :param quantity: Quantity to consider for adding to the result
        :return: boolean indicating that a valid item found (partial or full)
        """
        word = word.lower()
        if self.__processing_partial_order__:
            word = self.__partial_order_name__ + ' ' + word
        part_item_name = CoffeeNlpCore.__get_nearest_word__(word, self.__partial_menu_items__)
        if part_item_name.count(' ') != word.count(' ') or \
                any(word_a[0] != word_b[0] for word_a, word_b in zip(part_item_name.split(), word.split())):
            part_item_name = ''
        # we accept the menu suggestions if and only if:
        #          we have equal number of words
        #          all corresponding words starts with same character
        complete_item_name = CoffeeNlpCore.__get_nearest_word__(word, self.complete_menu_items)
        if complete_item_name.count(' ') != word.count(' ') or \
                any(word_a[0] != word_b[0] for word_a, word_b in zip(complete_item_name.split(), word.split())):
            complete_item_name = ''
        if complete_item_name:
            if self.__processing_partial_order_in_result__:
                result['items'][-1]['item'] = complete_item_name
            else:
                result['items'].append({
                    'quantity': quantity,
                    'item': complete_item_name
                })
            if part_item_name:
                self.__processing_partial_order__ = True
                self.__processing_partial_order_in_result__ = True
                self.__partial_order_name__ = part_item_name
            else:
                self.__processing_partial_order__ = False
                self.__processing_partial_order_in_result__ = False
        elif part_item_name:
            self.__processing_partial_order__ = True
            self.__processing_partial_order_in_result__ = False
            self.__partial_order_name__ = part_item_name
        else:
            self.__processing_partial_order__ = False
            self.__processing_partial_order_in_result__ = False
        return part_item_name != '' or complete_item_name != ''

    def __get_number__(self, word: str, word_dep: str) -> int:
        """
        Compute and store item count based on word sequence
        :param word:
        :param word_dep:
        :return: latest value computed
        """
        if word == 'hundred':
            if self.__immediate_num_value__ == 0:
                value = 100
            else:
                value = self.__immediate_num_value__ * 100
        else:
            if word.isnumeric():
                value = self.__immediate_num_value__ + int(word)
            else:
                value = self.__immediate_num_value__ + self.__word2num__(word)
        if word_dep == 'compound':
            self.__immediate_num_value__ = value
        else:
            self.__immediate_num_value__ = 0
        return value
