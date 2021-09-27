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
# formatting conventions; the possibilities are too open ended
# for this module to attempt to guess for you.
#
##################################################


from __future__ import absolute_import, division, print_function, unicode_literals

import argparse
from copy import deepcopy

from g2p.mappings.tokenizer import get_tokenizer
from lxml import etree

from readalongs.log import LOGGER
from readalongs.text.util import (
    get_lang_attrib,
    is_do_not_align,
    load_xml,
    save_xml,
    unicode_normalize_xml,
)


class XMLTokenizer:
    def add_word_children(self, element):
        tag = etree.QName(element.tag).localname
        nsmap = element.nsmap if hasattr(element, "nsmap") else element.getroot().nsmap
        if tag in ["w", "teiHeader", "head"]:  # don't do anything to existing words!
            new_element = deepcopy(element)
            new_element.tail = ""  # just take off their .tail so that it's not doubled
            return new_element  # as the calling method tends to it

        if is_do_not_align(element):  # skip elements marked do-not-align="true"
            new_element = deepcopy(element)
            new_element.tail = ""  # don't add spurious whitespace
            return new_element

        new_element = etree.Element(element.tag, nsmap=nsmap)
        for key, value in element.attrib.items():
            new_element.attrib[key] = value

        lang = get_lang_attrib(element)
        tokenizer = get_tokenizer(lang)
        if element.text:
            new_element.text = ""
            for unit in tokenizer.tokenize_text(element.text):
                if unit["is_word"]:
                    new_child_element = etree.Element("w", nsmap=nsmap)
                    new_child_element.text = unit["text"]
                    new_element.append(new_child_element)
                    continue
                if new_element.getchildren():
                    if not new_element[-1].tail:
                        new_element[-1].tail = ""
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
                        new_element[-1].tail = ""
                    new_element[-1].tail += unit["text"]

        return new_element


def tokenize_xml(xml):
    tokenizer = XMLTokenizer()
    xml = deepcopy(xml)
    # FIXME: different langs have different normalizations, is this necessary?
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert XML to another orthography while preserving tags"
    )
    parser.add_argument("input", type=str, help="Input XML")
    parser.add_argument("output", type=str, help="Output XML")
    args = parser.parse_args()
    go(args.input, args.output)
