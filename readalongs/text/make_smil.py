#!/usr/bin/env python3
# -*- coding: utf-8 -*-

###################################################################
#
# make_smil.py
#
#   Turns alignment into formatted SMIL for ReadAlongs WebComponent
####################################################################


import chevron

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


def make_smil(text_path: str, audio_path: str, results: dict) -> str:
    """Actually render the SMIL

    Args:
        text_path(str): path to text
        audio_path(str): path to audio
        results(dict): all alignements

    Returns:
        str: formatted SMIL
    """
    results["text_path"] = text_path
    results["audio_path"] = audio_path
    return chevron.render(SMIL_TEMPLATE, results)
