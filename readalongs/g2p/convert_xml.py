#!/usr/bin/env python3
# -*- coding: utf-8 -*-

##############################################################
#
# convert_xml.py
#
# This takes an XML file with xml:lang attributes and text in
# some orthography, and converts it to use English ARPABET symbols
# for speech processing.  (Provided, of course, that a conversion
# pipeline for it is available through convert_orthography.py.)
# This XML file preserves complex markup, even within words
# (e.g. even if you have morpheme tags within words, it
# can perform phonological rules across those tags).
#
# Language attributes can be added at any level, even below the level of
# the word.  Like say I need to convert "Patrickƛən" (my name is Patrick)
# in Kwak'wala; neither an English nor Kwak'wala pipeline could appropriately
# convert this word.  I can mark that up as:
#
#  <w><m xml:lang="eng">Patrick</m><m xml:lang="kwk-napa">ƛən</m></w>
#
# to send the first part to the English conversion pipeline and the
# second part to the Kwak'wala pipeline.
#
# The only assumption made by this module about the structure of the XML
# is that it has word tags (using <w>, the convention used by TEI formats.)
# The reason for this is that the word is the domain over which phonological
# rules apply, and we particularly need to know it to be able to perform
# phonological rules at word boundaries.  We also only convert text that
# is part of words (i.e. we don't bother sending whitespace or punctuation
# through the G2P).
#
# So, if the XML file doesn't have word elements, tokenize it and add them.
#
# 3

from __future__ import print_function, unicode_literals
from __future__ import division, absolute_import
from unicodedata import normalize
import argparse
import copy

from .convert_orthography import ConverterLibrary
from .util import load_xml, save_xml, get_lang_attrib
from .util import concat_indices, offset_indices, trim_indices

try:
    unicode()
except:
    unicode = str


def iterate_over_text(element):
    lang = get_lang_attrib(element)
    if element.text:
        yield (lang, unicode(element.text))
    for child in element:
        for subchild in iterate_over_text(child):
            yield subchild
        if child.tail:
            yield (lang, unicode(child.tail))


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


def add_word_boundaries(xml, word_unit="w"):
    for word in xml.xpath(".//" + word_unit):
        word.text = '#' + (word.text if word.text else '')
        if word.getchildren():
            last_child = word[-1]
            last_child.tail = (
                last_child.tail if last_child.tail else '') + "#"
        else:
            word.text += '#'


def remove_word_boundaries(xml, word_unit="w"):
    for word in xml.xpath(".//" + word_unit):
        if word.text and word.text.startswith("#"):
            word.text = word.text[1:]
        if word.text and word.text.endswith("#"):
            word.text = word.text[:-1]
        if word.getchildren():
            last_child = word[-1]
            if last_child.tail and last_child.tail.endswith('#'):
                last_child.tail = last_child.tail[:-1]


def convert_words(xml, converter, word_unit="w",
                  output_orthography="eng-arpabet"):
    for word in xml.xpath(".//" + word_unit):
        # add_word_boundaries(word)
        # only convert text within words
        same_language_units = get_same_language_units(word)
        if not same_language_units:
            return
        all_text = ''
        all_indices = []
        for unit in same_language_units:
            text = normalize("NFD", unit["text"])
            text, indices = converter.convert(
                text,
                unit["lang"],
                output_orthography)
            all_text += text
            all_indices = concat_indices(all_indices, indices)
        replace_text_in_node(word, all_text, all_indices)

    return xml


def replace_text_in_node(word, text, indices):
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
                new_indices = offset_indices(
                    indices, -len(old_text), -len(new_text))
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
                    new_indices = offset_indices(
                        indices, -len(old_text), -len(new_text))
                    new_indices = trim_indices(new_indices)
                    child.tail = new_text
                    break

    return text, new_indices


def convert_xml(xml, word_unit="w",
                output_orthography="eng-arpabet", mapping_dir=None):
    converter = ConverterLibrary(mapping_dir)
    xml_copy = copy.deepcopy(xml)
    add_word_boundaries(xml_copy, word_unit)
    convert_words(xml_copy, converter, word_unit, output_orthography)
    remove_word_boundaries(xml_copy, word_unit)
    return xml_copy


def go(input_filename, output_filename, word_unit="w",
       output_orthography="eng-arpabet", mapping_dir=None):
    xml = load_xml(input_filename)
    converted_xml = convert_xml(xml, word_unit, output_orthography,
                                mapping_dir=mapping_dir)
    save_xml(output_filename, converted_xml)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Convert XML to another orthography while preserving tags')
    parser.add_argument('input', type=str, help='Input XML')
    parser.add_argument('output', type=str, help='Output XML')
    parser.add_argument('--mapping-dir',
                        type=str, help="Alternate directory containing "
                        "orthography mappings")
    parser.add_argument('--word_unit', type=str, default="w",
                        help='XML element that '
                        'represents a word (default: "w")')
    parser.add_argument('--out_orth', type=str, default="eng-arpabet",
                        help='Output orthography (default: "eng-arpabet")')
    args = parser.parse_args()
    go(args.input, args.output, args.word_unit, args.out_orth,
       mapping_dir=args.mapping_dir)
