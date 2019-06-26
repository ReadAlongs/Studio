#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#######################################################################
#
# simple_mapping_g2p.py
#
# A simple G2P system, based on a mapping file, that keeps track of
# indices to the original.
#
######################################################################

from __future__ import print_function, unicode_literals, division
import re
from readalongs.log import LOGGER
from .util import load_json
from unicodedata import normalize
from text_unidecode import unidecode


# fallback characters for when a stray letter gets in; we just take a guess
# what they might mean.  otherwise, we assume "a" represents IPA "a", etc.
UNIDECODE_MAPPING = {  # note, these replacements should always be something
    "c": "t͡ʃ",         # in the eng-ipa mapping, because these characters don't
    "j": "ʒ",          # go through the approximate mapping process
    "y": "j"
}

class SimplerG2P:

    def __init__(self, mapping_path, strict=False):
        self.mapping = load_json(mapping_path)
        self.in_lang = self.mapping["in_metadata"]["lang"]
        self.out_lang = self.mapping["out_metadata"]["lang"]
        self.input_delimiter = self.mapping["in_metadata"]["delimiter"]
        self.output_delimiter = self.mapping["out_metadata"]["delimiter"]
        self.case_insensitive = self.mapping["in_metadata"].get(
            "case_insensitive", False)
        self.strict = strict

        # gather replacements
        self.replacements = {}
        self.regex_pieces = []
        for io_pair in self.mapping["map"]:
            inp, outp = io_pair["in"], io_pair["out"]
            inp = normalize("NFD", inp)
            outp = normalize("NFD", outp)
            if self.case_insensitive:
                inp = inp.lower()
            self.replacements[inp] = outp
            self.regex_pieces.append(re.escape(inp))

        # create regex
        self.regex_pieces = sorted(self.regex_pieces, key=lambda s: -len(s))
        self.regex_pieces += '.'
        if self.input_delimiter:
            self.regex_pieces += self.input_delimiter
        pattern = "|".join(self.regex_pieces)
        pattern = "(" + pattern + ")"
        flags = re.DOTALL
        if self.case_insensitive:
            flags |= re.I
        self.regex = re.compile(pattern, flags)

    def convert_character(self, text):
        if text not in self.replacements:
            if self.strict:
                raise KeyError(text)
            if text in UNIDECODE_MAPPING.values():
                return text  # it's the output of a prior fallback... or
                             # if it isn't, you can let it go through anyway.
            text = unidecode(text).lower().strip()
            if text in self.replacements:
                return self.replacements[text]
            if not text.isalpha():
                return ''
            if text in UNIDECODE_MAPPING:
                return UNIDECODE_MAPPING[text]
            return text
        if text == self.input_delimiter:
            return self.output_delimiter
        return self.replacements[text]

    def convert(self, text):
        input_str = ''
        result_str = ''
        indices = []
        current_index = 0
        matches = self.regex.findall(text)
        for s in matches:
            input_str += s
            if self.case_insensitive:
                s = s.lower()
            s_converted = self.convert_character(s)
            if result_str and s_converted:
                result_str += self.output_delimiter
            result_str += s_converted
            indices.append((len(input_str), len(result_str)))

        assert(input_str == text)
        if indices[-1][0] != len(input_str) or indices[-1][1] != len(result_str):
            indices.append((len(input_str), len(result_str)))
        return result_str, indices
