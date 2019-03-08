#!/usr/bin/env python3
# -*- coding: utf-8 -*-

##################################################
#
# make_fsg.py
#
# This module takes a text file, marked up with
# units (e.g. w for word, m for morpheme) and ids
# and converted to IPA, and outputs a FSG
# file for processing by PocketSphinx.
#
##################################################


from __future__ import print_function, unicode_literals, division
from io import open
import logging, argparse, os
from lxml import etree
import mustache
from util import *

try:
    unicode()
except:
    unicode = str


FSG_TEMPLATE = '''FSG BEGIN {{name}}
NUM_STATES {{num_states}}
START STATE 0
FINAL_STATE {{final_state}}

{{#states}}
TRANSITION {{current}} {{next}} 1.0 {{id}}
{{/states}}
FSG_END
'''


def make_fsg(xml, filename, unit="m"):
    data = {
        "name": os.path.splitext(os.path.basename(filename))[0],
        "states": [],
        "num_states": 0
    }

    for e in xml.xpath(".//" + unit):
        if "id" not in e.attrib:
            continue
        data["states"].append({
            "id": e.attrib["id"],
            "current": data["num_states"],
            "next": data["num_states"] + 1
        })
        data["num_states"] += 1

    data["final_state"] = data["num_states"]
    data["num_states"] += 1

    return mustache.render(FSG_TEMPLATE, data)


def make_fst_and_dict(input_filename, output_filename, unit):
    xml = load_xml(input_filename)
    fsg = make_fsg(xml, input_filename, unit)
    save_txt(output_filename, fsg)

if __name__ == '__main__':
     parser = argparse.ArgumentParser(description='Convert XML to another orthography while preserving tags')
     parser.add_argument('input', type=str, help='Input XML')
     parser.add_argument('output_fsg', type=str, help='Output .fsg file')
     parser.add_argument('--unit', type=str, default='m', help='XML tag of the unit of analysis (e.g. "w" for word, "m" for morpheme)')
     args = parser.parse_args()
     make_fst_and_dict(args.input, args.output_fsg, args.unit)
