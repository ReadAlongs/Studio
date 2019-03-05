#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, division
from io import open
import logging, argparse
from lxml import etree
from collections import defaultdict

TAG_TO_ID = {
    'p': 'par',
    'u': 'utt',
    's': 'sen',
    'w': 'wor',
    'm': 'mor'
}

def add_ids(element, parent_id='', ids=defaultdict(0)):
    if "id" not in element.attrib:
        if element.tag in TAG_TO_ID:
            id = TAG_TO_ID[element.tag]
        elif element.tag == 'seg' and "type" in element.attrib:
            if element.attrib["type"] == 'syll':
                id = "syl"
            elif element.attrib["type"] in ["morph", "morpheme", "base", "root", "prefix", "suffix"]:
                id = 'mor'
        else:
            id = element.tag
        if id not in ids:
            ids[id] = 0
        full_id = parent_id + id + str(ids[id]).zfill(3)
        element.attrib["id"] = full_id
        ids[id] += 1
    for child in element:
        ids = add_ids(child, full_id, ids)
    return ids
