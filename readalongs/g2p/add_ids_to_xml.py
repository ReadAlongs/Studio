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
# The module does not expect any particular kind of markup,

The auto-generated IDs have formats like "s0w2m1" meaning
# "sentence 0, word 2, morpheme 1".  But it's flexible if some elements
# already have ids, or if the markup uses different tags than a TEI document.
#
###################################################

from __future__ import print_function, unicode_literals, division
from io import open
import logging, argparse, copy
from lxml import etree
from collections import defaultdict

TAG_TO_ID = {
    'p': 'p',
    'u': 'u',
    's': 's',
    'w': 'w',
    'm': 'm'
}

def add_ids_aux(element, parent_id='', ids=defaultdict(lambda:0)):
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
        full_id = parent_id + id + str(ids[id])
        element.attrib["id"] = full_id
        ids[id] += 1
    new_ids = copy.deepcopy(ids)
    for child in element:
        new_ids = add_ids_aux(child, full_id, new_ids)
    return ids

def add_ids(tree):
    ids=defaultdict(lambda:0)
    for child in tree:    # don't bother with the root element
        ids = add_ids_aux(child, ids)
    return tree

def go(input_filename, output_filename):
    with open(input_filename, "r", encoding="utf-8") as fin:
        tree = etree.fromstring(fin.read())
        add_ids(tree)
        with open(output_filename, "w", encoding="utf-8") as fout:
            fout.write(etree.tostring(tree, encoding="unicode"))

if __name__ == '__main__':
     parser = argparse.ArgumentParser(description='Convert XML to another orthography while preserving tags')
     parser.add_argument('input', type=str, help='Input XML')
     parser.add_argument('output', type=str, help='Output XML')
     args = parser.parse_args()
     go(args.input, args.output)
