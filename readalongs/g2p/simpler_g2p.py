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
import logging
from .util import load_json
from unicodedata import normalize

class SimplerG2P:

    def __init__(self, mapping_path):
        self.mapping = load_json(mapping_path)
        self.in_lang = self.mapping["in_metadata"]["lang"]
        self.out_lang = self.mapping["out_metadata"]["lang"]
        self.input_delimiter = self.mapping["in_metadata"]["delimiter"]
        self.output_delimiter = self.mapping["out_metadata"]["delimiter"]
        self.case_insensitive = self.mapping["in_metadata"].get(
            "case_insensitive", False)

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
