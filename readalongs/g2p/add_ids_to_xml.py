#!/usr/bin/env python3
# -*- coding: utf-8 -*-

###################################################
#
# add_ids_to_xml.py
#
# In order to tell visualization systems, "highlight this
# thing at this time", the document has to be able to identify
# particular elements.  If the original document does NOT have
# id tags on its elements, this module adds some.
#
# The auto-generated IDs have formats like "s0w2m1" meaning
# "sentence 0, word 2, morpheme 1".  But it's flexible if some elements
# already have ids, or if the markup uses different tags than a TEI document.
#
###################################################

from __future__ import print_function, unicode_literals, division
from io import open
import logging, argparse
from copy import deepcopy
from lxml import etree
from collections import defaultdict
from util import *

TAG_TO_ID = {
    'p': 'p',
    'u': 'u',
    's': 's',
    'w': 'w',
    'm': 'm'
}

def add_ids_aux(element, ids=defaultdict(lambda:0), parent_id=''):
    if "id" not in element.attrib:
        if element.tag in TAG_TO_ID:
            id = TAG_TO_ID[element.tag]
        elif element.tag == 'seg' and "type" in element.attrib:
            if element.attrib["type"] == 'syll':
                id = "y"
            elif element.attrib["type"] in ["morph", "morpheme", "base", "root", "prefix", "suffix"]:
                id = 'm'
        else:
            id = element.tag
        if id not in ids:
            ids[id] = 0
        element.attrib["id"] = parent_id + id + str(ids[id])
        ids[id] += 1
    full_id = element.attrib["id"]
    new_ids = deepcopy(ids)
    for child in element:
        new_ids = add_ids_aux(child, new_ids, full_id)
    return ids

def add_ids(xml):
    xml = deepcopy(xml)
    ids=defaultdict(lambda:0)
    for child in xml:    # don't bother with the root element
        ids = add_ids_aux(child, ids)
    return xml

def go(input_filename, output_filename):
    xml = load_xml(input_filename)
    xml = add_ids(xml)
    save_xml(output_filename, xml)

if __name__ == '__main__':
     parser = argparse.ArgumentParser(description='Convert XML to another orthography while preserving tags')
     parser.add_argument('input', type=str, help='Input XML')
     parser.add_argument('output', type=str, help='Output XML')
     args = parser.parse_args()
     go(args.input, args.output)