#!/usr/bin/env python3
# -*- coding: utf-8 -*-

################################
#
# util.py
#
# Just some shared functions
#
##############################

from __future__ import print_function, unicode_literals, division
from io import open
from lxml import etree
from copy import deepcopy

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

def merge_if_same_label(lst_of_dicts, text_key, label_key):
    results = []
    current_item = None
    for dct in lst_of_dicts:
        if label_key not in dct:
            dct[label_key] = None
        if not current_item:
            current_item = deepcopy(dct)
            continue
        if dct[label_key] == current_item[label_key]:
            current_item[text_key] += dct[text_key]
        else:
            results.append(current_item)
            current_item = deepcopy(dct)
    if current_item:
        results.append(current_item)
    return results



def load_xml(input_filename):
    with open(input_filename, "r", encoding="utf-8") as fin:
        return etree.fromstring(fin.read())

def save_xml(output_filename, xml):
    with open(output_filename, "w", encoding="utf-8") as fout:
        fout.write(etree.tostring(xml, encoding="unicode"))

def save_txt(output_filename, txt):
    with open(output_filename, "w", encoding="utf-8") as fout:
        fout.write(txt)
