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


from __future__ import absolute_import, division, print_function, unicode_literals

import argparse

import pystache

from readalongs.log import LOGGER
from readalongs.text.util import load_xml, save_txt

DICT_TEMPLATE = """{{#items}}
{{id}}\t{{pronunciation}}
{{/items}}
"""


def make_dict(xml, input_filename, unit="m"):
    data = {"items": []}
    nwords = 0
    for e in xml.xpath(".//" + unit):
        if "id" not in e.attrib:
            LOGGER.error(
                "%s-type element without id in file %s" % (unit, input_filename)
            )
        text = e.text.strip()
        if not text:
            continue
        nwords += 1
        data["items"].append({"id": e.attrib["id"], "pronunciation": text})
    if nwords == 0:
        raise RuntimeError("No words in dictionary!")
    return pystache.render(DICT_TEMPLATE, data)


def go(input_filename, output_filename, unit):
    xml = load_xml(input_filename)
    dct = make_dict(xml, input_filename, unit)
    save_txt(output_filename, dct)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Make a pronunciation dictionary from a G2P'd XML file"
    )
    parser.add_argument("input", type=str, help="Input XML")
    parser.add_argument("output", type=str, help="Output .dict file")
    parser.add_argument(
        "--unit",
        type=str,
        default="m",
        help="XML tag of the unit of analysis " '(e.g. "w" for word, "m" for morpheme)',
    )
    args = parser.parse_args()
    go(args.input, args.output, args.unit)
