#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, division
from io import open
import logging, argparse
from lxml import etree
from convert_orthography import *
from collections import defaultdict

try:
    unicode()
except:
    unicode = str

def get_lang_attrib(element):
    lang_path = element.xpath('./@xml:lang')
    if not lang_path and "lang" in element.attrib:
        lang_path = element.attrib["lang"]
    if not lang_path and element.getparent() is not None:
        return get_lang_attrib(element.getparent())
    if not lang_path:
        return None
    return lang_path[0]


def iterate_over_text(element):
    lang = get_lang_attrib(element)
    if element.text:
        yield (lang, element.text)
    for child in element:
        for subchild in iterate_over_text(child):
            yield subchild
        if child.tail:
            yield (lang, child.tail)

def get_same_language_units(element):
    character_counter = 0
    same_language_units = []
    current_sublang, current_subword = None, None
    for sublang, subword in iterate_over_text(element):
        if current_subword and sublang == current_sublang:
            current_subword += subword
            continue
        if current_subword:
            same_language_units.append({
                "index": character_counter,
                "lang": current_sublang,
                "text": current_subword})
            character_counter += len(current_subword)
        current_sublang, current_subword = sublang, subword
    if current_subword:
        same_language_units.append({
            "index": character_counter,
            "lang": current_sublang,
            "text": current_subword})
    return same_language_units

def add_word_boundaries(word):
    # add word boundaries
    word.text = '#' + (word.text if word.text else '')
    if word.getchildren():
        last_child = word[-1]
        last_child.tail = '#' + (last_child.tail if last_child.tail else '')
    else:
        word.text += '#'

def remove_word_boundaries(word):
    if word.text and word.text.startswith("#"):
        word.text = word.text[1:]
    if word.getchildren():
        last_child = word[-1]
        if last_child.tail and last_child.tail.endswith('#'):
            last_child.tail = last_child.tail[:-1]

def convert_words(tree, converter):
    pronouncing_dictionary = defaultdict(list)
    for word in tree.xpath(".//w"):
        add_word_boundaries(word)
        # only convert text within words
        same_language_units = get_same_language_units(word)
        if not same_language_units:
            continue
        #same_language_units[0]["text"] = "#" + same_language_units[0]["text"]
        #same_language_units[-1]["text"] += "#"
        all_text = ''
        all_indices = []
        for unit in same_language_units:
            text, indices = converter.convert(unit["text"], unit["lang"], "eng-arpabet")
            all_text += text
            all_indices = concat_indices(all_indices, indices)
        replace_text_in_node(word, all_text, all_indices)
        remove_word_boundaries(word)

        for morph in word.xpath(".//m"):
            key = morph.attrib["id"] if "id" in morph.attrib else morph.attrib["orig"]
            pronouncing_dictionary[key].append(morph.text)

    return pronouncing_dictionary

def replace_text_in_node(word, text, indices):
    print("Text: ", text, ", indices: ", indices)
    old_text = ''
    new_text = ''
    new_indices = indices

    # handle the text
    if word.text:
        for i1, i2 in new_indices:
            if i1 >= len(word.text):
                old_text = word.text[:i1]
                new_text = text[:i2]
                text = text[i2:]
                print("Replacing text [%s] with [%s]" % ([old_text], [new_text]))
                new_indices = offset_indices(indices, -len(old_text), -len(new_text))
                new_indices = trim_indices(new_indices)
                word.attrib["orig"] = old_text
                word.text = new_text
                break

    for child in word:
        text, new_indices = replace_text_in_node(child, text, new_indices)
        if child.tail:
            for i1, i2 in new_indices:
                if i1 >= len(child.tail):
                    old_text = child.tail[:i1]
                    new_text = text[:i2]
                    text = text[i2:]
                    print("Replacing text [%s] with [%s]" % ([old_text], [new_text]))
                    new_indices = offset_indices(indices, -len(old_text), -len(new_text))
                    new_indices = trim_indices(new_indices)
                    child.tail = new_text
                    break

    return text, new_indices

def save_pronouncing_dictionary(dict_filename, dictionary):
    with open(dict_filename, 'w', encoding='utf-8') as fout:
        for key, values in dictionary.items():
            for value in values:
                fout.write("%s\t%s\n" % (key.strip(), value.strip()))

def go(mapping_dir, input_filename, output_filename):
    converter = ConverterLibrary(mapping_dir)
    with open(input_filename, "r", encoding="utf-8") as fin:
        tree = etree.fromstring(fin.read())
        pronouncing_dictionary = convert_words(tree, converter)
        save_pronouncing_dictionary(output_filename, pronouncing_dictionary)

if __name__ == '__main__':
     parser = argparse.ArgumentParser(description='Convert XML to another orthography while preserving tags')
     parser.add_argument('mapping_dir', type=str, help="Directory containing orthography mappings")
     parser.add_argument('input', type=str, help='Input XML')
     parser.add_argument('output', type=str, help='Output XML')
     args = parser.parse_args()
     go(args.mapping_dir, args.input, args.output)
