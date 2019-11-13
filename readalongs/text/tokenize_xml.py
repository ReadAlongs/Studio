#!/usr/bin/env python3
# -*- coding: utf-8 -*-

##################################################
#
# tokenize_xml.py
#
# The XML G2P conversion module expects XML with word
# annotations (specifically, <w> elements from the
# TEI conventions).  If this doesn't exist, this module
# attempts to make them.  It will assume alphanumeric characters
# are parts of words, and also any characters that it finds in the
# language's inventory (as indicated by xml:lang attributes on elements).
#
# The nice part about taking into account xml:lang tags and a
# language's inventory is that it can catch things like
# Mohawk ":" as being an alphabetic character after particular letters
# within Mohawk words, but not count colons as alphabetic characters
# in other circumstances (English words, after sounds that can't be
# geminated, etc.)
#
# Note that if you have *subword* annotations already, but
# not word annotations, this module will probably not do
# what you want; it will put the word annotations inside the
# subword annotations!  If you have subword annotations already,
# add the word annotations however is appropriate for your
# formatting conventions; the possibilities are too-opened ended
# for this module to attempt to guess for you.
#
##################################################


from __future__ import print_function, unicode_literals
from __future__ import division, absolute_import

import re
import argparse
from copy import deepcopy

from lxml import etree
from g2p.mappings import Mapping
from g2p.mappings.langs import MAPPINGS_AVAILABLE

from readalongs.log import LOGGER
from readalongs.text.util import get_lang_attrib, merge_if_same_label
from readalongs.text.util import load_xml, save_xml
from readalongs.text.util import unicode_normalize_xml, get_unicode_category

# TODO: AP: Is this for Python 2 support? Lots of other parts of this library will not support python2.
#           Maybe we should just get rid of this?
try:
    unicode()
except:
    unicode = str


class DefaultTokenizer:
    def __init__(self):
        self.inventory = []
        self.delim = ''
        self.case_sensitive = False

    def tokenize_aux(self, text):
        return text

    def is_word_charcter(self, c):
        if not self.case_sensitive:
            c = c.lower()
        if c in self.inventory:
            return True
        if self.delim and c == self.delim:
            return True
        assert(len(c) <= 1)
        if get_unicode_category(c) in [ "letter", "number", "diacritic" ]:
            return True
        return False

    def tokenize_text(self, text):
        text = unicode(text)
        matches = self.tokenize_aux(text)
        units = [{"text": m, "is_word": self.is_word_charcter(m)}
                 for m in matches]
        units = merge_if_same_label(units, "text", "is_word")
        return units


class Tokenizer(DefaultTokenizer):
    def __init__(self, mapping: Mapping):
        self.inventory = mapping.inventory('in')
        self.lang = mapping.kwargs.get('language_name', '')
        self.delim = mapping.kwargs.get('in_delimiter', '')
        self.case_sensitive = mapping.kwargs.get('case_sensitive', True)
        # create regex

        regex_pieces = sorted(self.inventory, key=lambda s: -len(s))
        regex_pieces = [re.escape(p) for p in regex_pieces]
        if self.delim:
            regex_pieces.append(self.delim)
        pattern = "|".join(regex_pieces + ['.'])
        pattern = "(" + pattern + ")"
        flags = re.DOTALL
        if not self.case_sensitive:
            flags |= re.I
        self.regex = re.compile(pattern, flags)

    def tokenize_aux(self, text):
        return self.regex.findall(text)


class TokenizerLibrary:
    def __init__(self):
        self.tokenizers = {None: DefaultTokenizer()}
        for x in MAPPINGS_AVAILABLE:
            mapping = Mapping(in_lang=x['in_lang'], out_lang=x['out_lang'])
            tokenizer_key = self.get_tokenizer_key(x['in_lang'], x['out_lang'])
            self.tokenizers[tokenizer_key] = Tokenizer(mapping)

    def get_tokenizer_key(self, in_lang, out_lang=None):
        if not out_lang:
            out_lang = in_lang + '-ipa'
        return in_lang + "-to-" + out_lang

    def add_word_children(self, element):
        tag = etree.QName(element.tag).localname
        nsmap = element.nsmap if hasattr(element, "nsmap") \
                            else element.getroot().nsmap
        if tag in ["w", "teiHeader", "head"]:   # don't do anything to existing words!
            new_element = deepcopy(element)
            new_element.tail = ''  # just take off their .tail so that it's not doubled
            return new_element     # as the calling method tends to it
        new_element = etree.Element(element.tag, nsmap=nsmap)
        for key, value in element.attrib.items():
            new_element.attrib[key] = value

        lang = get_lang_attrib(element)
        if lang:
            tokenizer_key = self.get_tokenizer_key(lang)
        else:
            tokenizer_key = None
        tokenizer = self.tokenizers.get(tokenizer_key,
                                        self.tokenizers[None])
        if element.text:
            new_element.text = ''
            for unit in tokenizer.tokenize_text(element.text):
                if unit["is_word"]:
                    new_child_element = etree.Element("w", nsmap=nsmap)
                    new_child_element.text = unit["text"]
                    new_element.append(new_child_element)
                    continue
                if new_element.getchildren():
                    if not new_element[-1].tail:
                        new_element[-1].tail = ''
                    new_element[-1].tail += unit["text"]
                    continue
                new_element.text += unit["text"]

        for child in element:
            # Comments Cause Crashes so Copy them Cleanly
            if child.tag is etree.Comment:
                new_element.append(child)
                continue
            new_child_element = self.add_word_children(child)
            new_element.append(new_child_element)
            if child.tail:
                # new_element.tail = ''  # in case it's a copy
                for unit in tokenizer.tokenize_text(child.tail):
                    if unit["is_word"]:
                        new_child_element = etree.Element("w")
                        new_child_element.text = unit["text"]
                        new_element.append(new_child_element)
                        continue
                    if not new_element[-1].tail:
                        new_element[-1].tail = ''
                    new_element[-1].tail += unit["text"]

        return new_element


def tokenize_xml(xml):
    tokenizer = TokenizerLibrary()
    xml = deepcopy(xml)
    unicode_normalize_xml(xml)
    words = xml.xpath(".//w")
    if words:
        LOGGER.info("Words (<w>) already present; skipping tokenization")
        return xml
    LOGGER.info("Words (<w>) not present; tokenizing")
    return tokenizer.add_word_children(xml)


def go(input_filename, output_filename):
    xml = load_xml(input_filename)
    xml = tokenize_xml(xml)
    save_xml(output_filename, xml)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Convert XML to another orthography while preserving tags')
    parser.add_argument('input', type=str, help='Input XML')
    parser.add_argument('output', type=str, help='Output XML')
    args = parser.parse_args()
    go(args.input, args.output)
