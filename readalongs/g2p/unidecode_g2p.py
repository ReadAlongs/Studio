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
from text_unidecode import unidecode

class UnidecodeG2P:

    def __init__(self, mapping_path):
        self.mapping = load_json(mapping_path)
        self.in_lang = self.mapping["in_metadata"]["lang"]
        self.out_lang = self.mapping["out_metadata"]["lang"]
        self.input_delimiter = self.mapping["in_metadata"]["delimiter"]
        self.output_delimiter = self.mapping["out_metadata"]["delimiter"]
        self.case_insensitive = self.mapping["in_metadata"].get(
            "case_insensitive", False)

        self.replacements = { "#": "" }
        for io_pair in self.mapping["map"]:
            inp, outp = io_pair["in"], io_pair["out"]
            inp = normalize("NFD", inp)
            outp = normalize("NFD", outp)
            if self.case_insensitive:
                inp = inp.lower()
            self.replacements[inp] = outp

    def convert(self, text):
        if self.case_insensitive:
            text = text.lower()
        indices = [(0,0)]
        result = ''
        for i, c in enumerate(text):
            if c == self.input_delimiter:
                continue
            coverted = c if c in self.replacements else unidecode(c).lower().strip()
            for c2 in coverted:
                if c2 not in self.replacements:
                    logging.warning("Unknown character in unidecode input/output: %s/%s",
                        c, c2)
                    continue
                c_converted = self.replacements[c2]
                if result and c_converted:
                    result += self.output_delimiter
                result += c_converted
                indices.append((i+1, len(result)))

        if indices[-1][0] != len(text) or indices[-1][1] != len(result):
            indices.append((len(text), len(result)))
        return result, indices
#
# g2p = UnidecodeG2P("readalongs/lang/und/und_to_ipa.json")
# print(g2p.convert("foop"))
# print(g2p.convert("blump"))
# print(g2p.convert("oops"))
# print(g2p.convert("nugʷaʔəm"))
# print(g2p.convert("nugwa'a̱m"))
# print(g2p.convert("北京市"))
