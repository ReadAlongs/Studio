#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#########################################################################
#
# end_to_end.py
#
# Takes an XML file (preferrably using TEI conventions) and
# makes:
#
# 1. An XML file with added IDs for elements (if the elements didn't
#    already have ID attributes)
# 2. An FSG file where the transitions are those IDs.
# 3. A dictionary file giving a mapping between IDs and approximate
#    pronunciations in ARPABET
#
#
# The XML file needs to have xml:lang attributes and tokenization
# (indicated with <w> tags).  Alignment can be done at any level of
# analysis, however; if there are, for example, morpheme tags (<m>),
# you can make that be the level of analysis with the option
# --unit m
#
#
##########################################################################

from __future__ import print_function, unicode_literals, division
from io import open
import logging, argparse
from copy import deepcopy
from lxml import etree

from util import *
from add_ids_to_xml import add_ids
from convert_xml import convert_xml
from make_fsg_and_dict import make_fsg, make_dict

try:
    unicode()
except:
    unicode = str


def end_to_end(mapping_dir, xml, input_filename, unit):
    add_ids(xml)
    converted_xml = convert_xml(mapping_dir, xml)
    fsg = make_fsg(converted_xml, input_filename, unit)
    pronouncing_dictionary = make_dict(converted_xml, unit)
    return xml, fsg, pronouncing_dictionary

def go(input_filename, mapping_dir, output_xml_filename, output_fsg_filename, output_dict_filename, unit):
    xml = load_xml(input_filename)
    xml, fsg, dct = end_to_end(mapping_dir, xml, input_filename, unit)
    save_xml(output_xml_filename, xml)
    save_txt(output_fsg_filename, fsg)
    save_txt(output_dict_filename, dct)

if __name__ == '__main__':
     parser = argparse.ArgumentParser(description='Convert XML to another orthography while preserving tags')
     parser.add_argument('input', type=str, help='Input XML')
     parser.add_argument('mapping_dir', type=str, help="Directory containing orthography mappings")
     parser.add_argument('output_xml', type=str, help="Output XML file")
     parser.add_argument('output_fsg', type=str, help='Output .fsg file')
     parser.add_argument('output_dict', type=str, help='Output .dict file')
     parser.add_argument('--unit', type=str, default='m', help='XML tag of the unit of analysis (e.g. "w" for word, "m" for morpheme)')
     args = parser.parse_args()
     go(args.input, args.mapping_dir, args.output_xml, args.output_fsg, args.output_dict, args.unit)
