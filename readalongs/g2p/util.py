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
import logging, argparse
from copy import deepcopy
from lxml import etree

from add_ids_to_xml import add_ids
from make_fsg_and_dict import make_fsg, make_dict

try:
    unicode()
except:
    unicode = str


def load_xml(input_filename):
    with open(input_filename, "r", encoding="utf-8") as fin:
        return etree.fromstring(fin.read())

def save_xml(output_filename, xml):
    with open(output_filename, "w", encoding="utf-8") as fout:
        fout.write(etree.tostring(xml, encoding="unicode"))

def save_txt(output_filename, txt):
    with open(output_filename, "w", encoding="utf-8") as fout:
        fout.write(txt)
