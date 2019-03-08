#!/usr/bin/env python3
# -*- coding: utf-8 -*-

##################################################
#
# make_fsg_and_dict.py
#
# This module takes a text file, marked up with
# units (e.g. w for word, m for morpheme) and ids
# and converted to IPA, and outputs the FSG and
# .dict files for processing by PocketSphinx.
#
##################################################


from __future__ import print_function, unicode_literals, division
from io import open
import logging, argparse, os
from lxml import etree
from convert_orthography import *
from collections import defaultdict
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

DICT_TEMPLATE = '''{{#items}}
{{id}}\t{{pronunciation}}
{{/items}}
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


def make_dict(xml, input_filename, unit="m"):
    data = { "items": [] }
    for e in xml.xpath(".//" + unit):
        if "id" not in e.attrib:
            logging.error("%s-type element without id in file %s" % (unit, input_filename))
        data["items"].append({
            "id": e.attrib["id"],
            "pronunciation": e.text
        })

    return mustache.render(DICT_TEMPLATE, data)


def make_fst_and_dict(input_filename, output_fsg_filename, output_dict_filename, unit):
    xml = load_xml(input_filename)
    fsg = make_fsg(xml, input_filename, unit)
    dct = make_dict(xml, input_filename, unit)
    save_txt(output_fsg_filename, fsg)
    save_txt(output_dict_filename, dct)

if __name__ == '__main__':
     parser = argparse.ArgumentParser(description='Convert XML to another orthography while preserving tags')
     parser.add_argument('input', type=str, help='Input XML')
     parser.add_argument('output_fsg', type=str, help='Output .fsg file')
     parser.add_argument('output_dict', type=str, help='Output .dict file')
     parser.add_argument('--unit', type=str, default='m', help='XML tag of the unit of analysis (e.g. "w" for word, "m" for morpheme)')
     args = parser.parse_args()
     make_fst_and_dict(args.input, args.output_fsg, args.output_dict, args.unit)
