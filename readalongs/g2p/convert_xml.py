#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, division
from io import open
import logging, argparse

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

def convert_words(tree, mapping):
    for word in utterance.xpath(".//w"):
        # only convert text within words
        same_language_units = get_same_language_units(word)
        if not same_language_units:
            continue
        same_language_units[0]["text"] = "#" + same_language_units[0]["text"]
        same_language_units[0]["index"] -= 1
        same_language_units[-1]["text"] += "#"
        print(same_language_units)

def go(mapping_filename, input_filename, output_filename):
    converter = Converter(mapping_filename)
    with open(input_filename, "r", encoding="utf-8") as fin:
        tree = etree.fromstring(fin.read())
        convert_words(tree)

# if __name__ == '__main__':
#     parser = argparse.ArgumentParser(description='Convert XML to another orthography while preserving tags')
#     parser.add_argument('mapping', type=str, help='Mapping filename')
#     parser.add_argument('input', type=str, help='Input XML')
#     parser.add_argument('output', type=str, help='Output XML')
#     args = parser.parse_args()
#     go(args.mapping, args.input, args.output)
