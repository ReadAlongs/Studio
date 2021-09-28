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


from __future__ import absolute_import, division, print_function, unicode_literals

import argparse
import datetime
import os

from readalongs.text.util import load_xml, save_txt

# ###################3
#
# For making an FSG from a SMIL, we have the following rules:
#
# -- All children of a SEQ element are subject to alignment, in the order they
# occur.
#
# -- Only one TEXT child of a PAR element is subject to alignment, with a
# for the first child.
#
# -- a BODY element is treated exactly as a SEQ
#
#
# TODO: AP: Do we need this? It doesn't appear to be used anywhere.
#       There's also an undefined variable error on line 90.
# TODO: Add numpy standard docstrings to functions
#########################


class GrammarComposite:
    def __init__(self, id):
        self.id = id
        self.children = []

    def append(self, child):
        self.children.append(child)

    def get_id_as_str(self):
        return "<%s>" % self.id


class GrammarChoice(GrammarComposite):
    def to_jsgf(self):
        results = []
        child_ids = " | ".join(c.get_id_as_str() for c in self.children)
        results.append("%s = %s" % (self.get_id_as_str(), child_ids))
        for child in self.children:
            results += child.to_jsgf()
        return results


class GrammarSequence(GrammarComposite):
    def to_jsgf(self):
        results = []
        child_ids = " ".join(c.get_id_as_str() for c in self.children)
        results.append("%s = %s" % (self.get_id_as_str(), child_ids))
        for child in self.children:
            results += child.to_jsgf()
        return results


def make_sequence(seq_node):
    for child in seq_node:
        # TODO: flake8 flags child_id as an unused variable, and indeed, this function
        # basically does nothing. Figure out what it's supposed to do and fix this
        # function! -EJ
        child_id = child.attrib["id"]


def make_jsgf(smil, unit="m"):
    body_node = xpath_default(smil, ".//i:body")[0]
    for child in body_node:
        print(child.tag)


def main(input_filename, output_filename, unit):
    smil = load_xml(input_filename)
    jsgf = make_jsgf(smil, unit)
    # save_txt(output_filename, jsgf)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Make an JSGF grammar from an XML file with IDs"
    )
    parser.add_argument("input", type=str, help="Input SMIL")
    parser.add_argument("output_jsgf", type=str, help="Output .jsgf file")
    parser.add_argument(
        "--unit",
        type=str,
        default="m",
        help="XML tag of the unit of analysis " '(e.g. "w" for word, "m" for morpheme)',
    )
    args = parser.parse_args()
    main(args.input, args.output_fsg, args.unit)
