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
# The XML file needs to have xml:lang attributes; if tokenization is
# not performed (indicated with <w> elements) it will be attempted
# automatically.  Alignment can be done at any level of analysis; if
# there are, for example, morpheme tags (<m>), you can make that be
# the level of analysis with the option --unit m
#
##########################################################################

from __future__ import print_function, unicode_literals, division, absolute_import
from io import open
import logging, argparse
from copy import deepcopy
from lxml import etree

from .util import *
from .add_ids_to_xml import add_ids
from .tokenize_xml import tokenize_xml
from .convert_xml import convert_xml
from .make_fsg import make_fsg
from .make_jsgf import make_jsgf
from .make_dict import make_dict

try:
    unicode()
except:
    unicode = str


def end_to_end(mapping_dir, xml, input_filename, unit, word_unit, out_orth):
    xml = tokenize_xml(xml, mapping_dir)
    xml = add_ids(xml)
    converted_xml = convert_xml(mapping_dir, xml, word_unit, out_orth)
    jsgf = make_jsgf(converted_xml, input_filename, unit)
    pronouncing_dictionary = make_dict(converted_xml, input_filename, unit)
    return xml, jsgf, pronouncing_dictionary

def go(input_filename, mapping_dir, output_xml_filename, output_jsgf_filename, output_dict_filename, unit, word_unit, out_orth):
    xml = load_xml(input_filename)
    xml, jsgf, dct = end_to_end(mapping_dir, xml, input_filename, unit, word_unit, out_orth)
    save_xml(output_xml_filename, xml)
    save_txt(output_jsgf_filename, jsgf)
    save_txt(output_dict_filename, dct)

if __name__ == '__main__':
     parser = argparse.ArgumentParser(description='Convert XML to another orthography while preserving tags')
     parser.add_argument('input', type=str, help='Input XML')
     parser.add_argument('mapping_dir', type=str, help="Directory containing orthography mappings")
     parser.add_argument('output_xml', type=str, help="Output XML file")
     parser.add_argument('output_jsgf', type=str, help='Output .jsgf file')
     parser.add_argument('output_dict', type=str, help='Output .dict file')
     parser.add_argument('--unit', type=str, default='w', help='XML tag of the unit of analysis (e.g. "w" for word, "m" for morpheme)')
     parser.add_argument('--word_unit', type=str, default="w", help='XML element that represents a word (default: "w")')
     parser.add_argument('--out_orth', type=str, default="eng-arpabet", help='Output orthography (default: "eng-arpabet")')
     parser.add_argument('--debug', action='store_true', help='Enable debugging output')
     args = parser.parse_args()
     if args.debug:
         logging.basicConfig(level=logging.DEBUG)
     go(args.input,
        args.mapping_dir,
        args.output_xml,
        args.output_jsgf,
        args.output_dict,
        args.unit,
        args.word_unit,
        args.out_orth)
