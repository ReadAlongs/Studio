#!/usr/bin/env python3
# -*- coding: utf-8 -*-

###################################################
#
# align_parent_nodes.py
#
###################################################

from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import argparse
import math
import os
from collections import defaultdict
from io import open

import pystache

from readalongs.g2p.util import load_xml, save_txt, xpath_default
from readalongs.log import LOGGER

SMIL_TEMPLATE = """<?xml version='1.0' encoding='utf-8'?>
<smil xmlns="http://www.w3.org/ns/SMIL" version="3.0">
    <body>
        {{#sentences}}
        <par id="par-{{text_id}}">
            <text src="{{text_path}}#{{text_id}}"/>
            <audio src="{{audio_path}}" clipBegin="{{start}}" clipEnd="{{end}}"/>
        </par>
        {{/sentences}}
    </body>
</smil>
"""


def iterate_over_children(element, ids, beginnings, endings):
    if "id" in element.attrib:
        id = element.attrib["id"]
        if id in ids:
            for filename, begin, end in ids[id]:
                beginnings[filename] = min([beginnings[filename], begin])
                endings[filename] = max([endings[filename], end])
    for child in element:
        beginnings, endings = iterate_over_children(child, ids, beginnings, endings)
    return beginnings, endings


def main(input_xml_path, input_smil_path, output_smil_path):
    xml = load_xml(input_xml_path)
    xml_filename = os.path.basename(input_xml_path)
    smil = load_xml(input_smil_path)

    ids = defaultdict(list)
    for par in xpath_default(smil, ".//i:par"):
        id = ""
        for text_src in xpath_default(par, ".//i:text/@src"):
            filename, id = text_src.split("#", 1)
            filename = os.path.basename(filename)
            if filename != xml_filename:
                continue
            for audio in xpath_default(par, ".//i:audio"):
                filename = audio.attrib["src"]
                begin = float(audio.attrib["clipBegin"])
                end = float(audio.attrib["clipEnd"])
                if not id:
                    continue
                ids[id].append((filename, begin, end))

    results = {"sentences": []}

    for sentence in xpath_default(xml, ".//i:s"):
        beginnings = defaultdict(lambda: 100000000000000.0)
        endings = defaultdict(lambda: -1.0)

        beginnings, endings = iterate_over_children(sentence, ids, beginnings, endings)

        for audio_path, beginning in beginnings.items():

            results["sentences"].append(
                {
                    "text_path": xml_filename,
                    "text_id": sentence.attrib["id"],
                    "audio_path": audio_path,
                    "start": beginning,
                    "end": endings[audio_path],
                }
            )

    output_smil_text = pystache.render(SMIL_TEMPLATE, results)
    save_txt(output_smil_path, output_smil_text)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert a SMIL file to a SVG file of its waveform, pitch, and units"
    )
    parser.add_argument("input_xml", type=str, help="Input XML file")
    parser.add_argument("input_smil", type=str, help="Input SMIL file")
    parser.add_argument("output_smil", type=str, help="Output SMIL file")
    parser.add_argument(
        "--tag",
        type=str,
        help='Element tag (e.g. "s") that you want to infer time annotations for',
    )
    args = parser.parse_args()
    main(args.input_xml, args.input_smil, args.output_smil)
