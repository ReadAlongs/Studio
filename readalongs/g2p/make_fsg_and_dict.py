#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, division
from io import open
import logging, argparse, os
from lxml import etree
from convert_orthography import *
from collections import defaultdict

try:
    unicode()
except:
    unicode = str

def make_fsg(xml, filename, unit="m"):
    name = os.path.basename(filename)
    name = os.path.splitext(name)[0]

    result = "FSG_BEGIN %s\n" % name

    states = []
    xpath_query = ".//" + unit
    for e in xml.xpath(xpath_query):
        if "id" not in e.attrib:
            continue
        states.append(e.attrib["id"])

    result += "NUM_STATES %s\n" % (len(states) + 1)
    result += "START_STATE 0\n"
    result += "FINAL_STATE %s\n\n" % len(states)

    for i, id in enumerate(states):
        result += "TRANSITION %s %s 1.0 %s\n" % (i, i+1, id)

    result += "FSG_END\n"

    return result


def make_dict(xml, unit="m"):
    pronouncing_dictionary = defaultdict(list)  # although IDs should be unique, this helps just in case they aren't.
    xpath_query = ".//" + unit
    for e in xml.xpath(xpath_query):
        key = e.attrib["id"] if "id" in e.attrib else e.attrib["orig"]
        pronouncing_dictionary[key].append(e.text)
    lines = []
    for key, values in pronouncing_dictionary.items():
        for value in values:
            lines.append("%s\t%s\n" % (key.strip(), value.strip()))
    return "".join(lines)

def go(input_filename, output_fsg_filename, output_dict_filename, unit):
    with open(input_filename, "r", encoding="utf-8") as fin:
        xml = etree.fromstring(fin.read())
        fsg = make_fsg(xml, input_filename, unit)
        pronouncing_dictionary = make_dict(xml, unit)
        with open(output_fsg_filename, "w", encoding="utf-8") as fout:
            fout.write(fsg)
        with open(output_dict_filename, "w", encoding="utf-8") as fout:
            fout.write(pronouncing_dictionary)

if __name__ == '__main__':
     parser = argparse.ArgumentParser(description='Convert XML to another orthography while preserving tags')
     parser.add_argument('input', type=str, help='Input XML')
     parser.add_argument('output_fsg', type=str, help='Output .fsg file')
     parser.add_argument('output_dict', type=str, help='Output .dict file')
     parser.add_argument('--unit', type=str, default='m', help='XML tag of the unit of analysis (e.g. "w" for word, "m" for morpheme)')
     args = parser.parse_args()
     go(args.input, args.output_fsg, args.output_dict, args.unit)
