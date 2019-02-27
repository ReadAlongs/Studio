#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, division
from io import open
import logging, json, os, re

OPEN_BRACKET = "⦕"
CLOSED_BRACKET = "⦖"
ZFILL_AMT = 5
DIGIT_FINDER =  OPEN_BRACKET + "\\d+" + CLOSED_BRACKET
digit_finder_regex = re.compile(DIGIT_FINDER)

def make_bracketed_num(num):
    return OPEN_BRACKET + str(num).zfill(ZFILL_AMT) + CLOSED_BRACKET

class Converter:

    def __init__(self, filename):
        with open(filename, "r", encoding="utf-8") as fin:
            self.mapping = json.load(fin)

        # gather replacements
        self.replacements = {}
        self.regex_pieces = [DIGIT_FINDER]
        for io_pair in self.mapping["map"]:
            inp, outp = io_pair["in"], io_pair["out"]
            #inp = self.mapping["in_metadata"]["prefix"] + inp + self.mapping["in_metadata"]["suffix"]

            #outp = self.mapping["out_metadata"]["prefix"] + outp + self.mapping["out_metadata"]["suffix"]
            self.replacements[inp] = outp
            inp_with_digits = DIGIT_FINDER.join(c for c in inp)
            self.regex_pieces.append(inp_with_digits)

        # create regex
        self.regex_pieces = sorted(self.regex_pieces, key = lambda s:-len(s))
        pattern = "|".join(self.regex_pieces + ['.'])
        pattern = "(" + pattern + ")"
        self.regex = re.compile(pattern)

    def convert_and_tokenize(self, text):
        results = []
        current_index = 0
        matches = self.regex.findall(text)
        for s in matches:
            s_without_digits = digit_finder_regex.sub('', s)
            if not s_without_digits:
                # it's a number index
                s = s.lstrip(OPEN_BRACKET).rstrip(CLOSED_BRACKET)
                print("Index = %s" % int(s))
                current_index = int(s)
                continue
            if s_without_digits not in self.replacements:
                print("Not found: %s" % s_without_digits)
                result = s_without_digits
            else:
                result = self.replacements[s_without_digits]

            results.append({ "index": current_index,
                             "text": result })

        return results

    def convert(self, text):
        text_with_nums = make_bracketed_num(0)
        for i, c in enumerate(text):
            text_with_nums += c
            text_with_nums += make_bracketed_num(i+1)
        return self.convert_and_tokenize(text_with_nums)

if __name__ == '__main__':
    conv = Converter("mappings/eng_ipa_to_arpabet.json")
    with open("test_output.json", "w", encoding="utf-8") as fout:
        output = conv.convert("mutʃi")
        fout.write(json.dumps(output, ensure_ascii=False, indent=4))
