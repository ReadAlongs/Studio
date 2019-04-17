#!/usr/bin/env python3
# -*- coding: utf-8 -*-

##################################################
#
# make_dict.py
#
# This module takes a text file, marked up with
# units (e.g. w for word, m for morpheme) and ids
# and converted to IPA, and produces a
# .dict file for processing by PocketSphinx.
#
##################################################


from __future__ import print_function, unicode_literals, division, absolute_import
from io import open
import logging, argparse
from lxml import etree
import pystache
from readalongs.g2p.util import *

try:
    unicode()
except:
    unicode = str


DICT_TEMPLATE = '''{{#items}}
{{id}}\t{{pronunciation}}
{{/items}}
'''

def make_dict(xml, input_filename, unit="m"):
    data = { "items": [] }
    for e in xml.xpath(".//" + unit):
        if "id" not in e.attrib:
            logging.error("%s-type element without id in file %s" % (unit, input_filename))
        text = e.text.strip()
        if not text:
            continue
        data["items"].append({
            "id": e.attrib["id"],
            "pronunciation": text
        })

    return pystache.render(DICT_TEMPLATE, data)

def go(input_filename, output_filename, unit):
    xml = load_xml(input_filename)
    dct = make_dict(xml, input_filename, unit)
    save_txt(output_filename, dct)

if __name__ == '__main__':
     parser = argparse.ArgumentParser(description="Make a pronunciation dictionary from a G2P'd XML file")
     parser.add_argument('input', type=str, help='Input XML')
     parser.add_argument('output', type=str, help='Output .dict file')
     parser.add_argument('--unit', type=str, default='m', help='XML tag of the unit of analysis (e.g. "w" for word, "m" for morpheme)')
     args = parser.parse_args()
     go(args.input, args.output, args.unit)
