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
from io import open
import logging, json, os, re, argparse, glob, copy
from .util import *
from unicodedata import normalize

OPEN_BRACKET = "⦕"
CLOSED_BRACKET = "⦖"
ZFILL_AMT = 5
DIGIT_FINDER =  OPEN_BRACKET + "\\d+" + CLOSED_BRACKET
digit_finder_regex = re.compile(DIGIT_FINDER)


def make_bracketed_num(num):
    return OPEN_BRACKET + str(num).zfill(ZFILL_AMT) + CLOSED_BRACKET

class SimpleMappingG2P:

    def __init__(self, mapping_path):
        self.mapping = load_json(mapping_path)
        self.in_lang = self.mapping["in_metadata"]["lang"]
        self.out_lang = self.mapping["out_metadata"]["lang"]
        self.output_delimiter = self.mapping["out_metadata"]["delimiter"]
        self.case_insensitive = self.mapping["in_metadata"].get(
            "case_insensitive", False)

        # gather replacements
        self.replacements = {}
        self.regex_pieces = [DIGIT_FINDER]
        for io_pair in self.mapping["map"]:
            inp, outp = io_pair["in"], io_pair["out"]
            inp = normalize("NFKC", inp)
            outp = normalize("NFKC", outp)
            #inp = self.mapping["in_metadata"]["prefix"] + inp + self.mapping["in_metadata"]["suffix"]
            #outp = self.mapping["out_metadata"]["prefix"] + outp + self.mapping["out_metadata"]["suffix"]
            if self.case_insensitive:
                inp = inp.lower()
            self.replacements[inp] = outp
            inp_with_digits = DIGIT_FINDER.join(c for c in inp)
            self.regex_pieces.append(inp_with_digits)

        # create regex
        self.regex_pieces = sorted(self.regex_pieces, key = lambda s:-len(s))
        pattern = "|".join(self.regex_pieces + ['.'])
        pattern = "(" + pattern + ")"
        flags = 0
        if self.case_insensitive:
            flags |= re.I
        self.regex = re.compile(pattern, flags)

    def convert_and_tokenize(self, text):
        result_str = ''
        result_indices = []
        current_index = 0
        matches = self.regex.findall(text)
        for s in matches:
            if self.case_insensitive:
                s = s.lower()
            s_without_digits = digit_finder_regex.sub('', s)
            if not s_without_digits:
                # it's a number index
                s = s.lstrip(OPEN_BRACKET).rstrip(CLOSED_BRACKET)
                current_index = int(s)
                continue
            if s_without_digits not in self.replacements:
                result = s_without_digits
            else:
                result = self.replacements[s_without_digits]

            result_indices.append((current_index, len(result_str)))

            if not result:
                continue
            if result_str:
                result_str += self.output_delimiter + result
            else:
                result_str = result

        result_indices.append((current_index, len(result_str)))
        return result_str, result_indices


    def convert(self, text):
        text_with_nums = make_bracketed_num(0)
        for i, c in enumerate(text):
            text_with_nums += c
            text_with_nums += make_bracketed_num(i+1)
        return self.convert_and_tokenize(text_with_nums)
