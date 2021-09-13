#!/usr/bin/env python3
# -*- coding: utf-8 -*-

###################################################################
#
# make_smil.py
#
#   Turns alignment into formatted SMIL for ReadAlongs WebComponent
####################################################################


import argparse

import pystache

from readalongs.text.util import save_txt

SMIL_TEMPLATE = """<smil xmlns="http://www.w3.org/ns/SMIL" version="3.0">
    <body>
        {{#words}}
        <par id="par-{{id}}">
            <text src="{{text_path}}#{{id}}"/>
            <audio src="{{audio_path}}" clipBegin="{{start}}" clipEnd="{{end}}"/>
        </par>
        {{/words}}
    </body>
</smil>
"""

BASENAME_IDX = 0
START_TIME_IDX = 9
WORDS_IDX = 10
WORD_SPAN = 4
WORD_SUBIDX = 2
END_SUBIDX = 3


def parse_hypseg(text):
    """ Parse hypseg alignments file and return alignements

    Args:
        text(str): hypseg text

    Returns:
        dict: a dictionary of all start and end points for each word in text
    """
    results = {"words": []}
    tokens = text.strip().split()
    # results["basename"] = tokens[BASENAME_IDX]
    start = float(tokens[START_TIME_IDX]) * 0.01
    i = WORDS_IDX
    while i < len(tokens):
        word = tokens[i + WORD_SUBIDX]
        end = tokens[i + END_SUBIDX]
        end = float(end) * 0.01
        if word != "<sil>":
            results["words"].append({"id": word, "start": start, "end": end})
        start = end
        i += WORD_SPAN
    return results


def make_smil(text_path: str, audio_path: str, results: dict) -> str:
    """ Actually render the SMIL

    Args:
        text_path(str): path to text
        audio_path(str): path to audio
        results(dict): all alignements

    Returns:
        str: formatted SMIL
    """
    results["text_path"] = text_path
    results["audio_path"] = audio_path
    return pystache.render(SMIL_TEMPLATE, results)


def go(seg_path, text_path, audio_path, output_path):
    results = make_smil(text_path, audio_path, parse_hypseg(seg_path))
    save_txt(output_path, results)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert XML to another orthography while preserving tags"
    )
    parser.add_argument("input_seg", type=str, help="Input hypseg file")
    parser.add_argument("text_path", type=str, help="Text filename")
    parser.add_argument("audio_path", type=str, help="Audio filename")
    parser.add_argument("output", type=str, help="Output SMIL file")
    args = parser.parse_args()
    go(args.input_seg, args.text_path, args.audio_path, args.output)
