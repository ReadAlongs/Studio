#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#######################################################################
#
# convert_orthography.py
#
# This module has two pieces of functionality.
#
# First, it has a simple converter object (e.g. for G2P mappings)
# that preserves indices between the input and the output.  That
# is important for the convert_xml.py module, which stitches converted
# text back into potentially complex XML markup.
#
# It also has functionality for composing converters into pipelines, e.g.
# composing Kwak'wala-orthography-to-IPA, Kwak'wala-IPA-to-English-IPA, and
# English-IPA-to-ARPABET to make a Kwak'wala-orthography-to-ARPABET converter.
#
# The system looks inside a mapping directory to see what converters and
# converter pipelines it can make, and greedily makes all it can.  (Converters
# are cheap to make; we might as well make all of them ahead of time rather
# than search through a possibility graph at the point of need.)
#
######################################################################

from __future__ import print_function, unicode_literals, division
from io import open
import logging, json, os, re, argparse, glob, copy

OPEN_BRACKET = "⦕"
CLOSED_BRACKET = "⦖"
ZFILL_AMT = 5
DIGIT_FINDER =  OPEN_BRACKET + "\\d+" + CLOSED_BRACKET
digit_finder_regex = re.compile(DIGIT_FINDER)

def make_bracketed_num(num):
    return OPEN_BRACKET + str(num).zfill(ZFILL_AMT) + CLOSED_BRACKET

def compose_indices(i1, i2):
    if not i1:
        return i2
    i2_dict = dict(i2)
    i2_idx = 0
    results = []
    for i1_in, i1_out in i1:
        highest_i2_found = -1
        while i2_idx <= i1_out:
            if i2_idx in i2_dict and i2_dict[i2_idx] > highest_i2_found:
                highest_i2_found = i2_dict[i2_idx]
            i2_idx += 1
        results.append((i1_in, highest_i2_found))
    return results

def concat_indices(i1, i2):
    if not i1:
        return i2
    results = copy.deepcopy(i1)
    offset1, offset2 = results[-1]
    for i1, i2 in i2[1:]:
        results.append((i1+offset1, i2+offset2))
    return results

def offset_indices(idxs, n1, n2):
    return [ (i1+n1,i2+n2) for i1, i2 in idxs ]

def trim_indices(idxs):
    result = []
    for i1, i2 in idxs:
        i1 = max(i1, 0)
        i2 = max(i2, 0)
        if (i1, i2) in result:
            continue
        result.append((i1,i2))
    return result





class Converter:

    def __init__(self, mapping):
        self.mapping = mapping
        self.in_lang = self.mapping["in_metadata"]["lang"]
        self.out_lang = self.mapping["out_metadata"]["lang"]
        self.output_delimiter = self.mapping["out_metadata"]["delimiter"]

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
        result_str = ''
        result_indices = []
        current_index = 0
        matches = self.regex.findall(text)
        for s in matches:
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


class CompositeConverter:

    def __init__(self, converter1, converter2):
        if converter1.out_lang != converter2.in_lang:
            logging.error("Cannot compose converter %s->%s and converter %s->%s" %
                            (converter1.in_lang, converter1.out_lang,
                            converter2.in_lang, converter2.out_lang))
        self.converter1 = converter1
        self.converter2 = converter2
        self.in_lang = self.converter1.in_lang
        self.out_lang = self.converter2.out_lang


    def convert(self, text):
        c1_text, c1_indices = self.converter1.convert(text)
        c2_text, c2_indices = self.converter2.convert(c1_text)
        final_indices = compose_indices(c1_indices, c2_indices)
        return c2_text, final_indices


class ConverterLibrary:

    def __init__(self, mappings_dir):

        self.converters = {}

        mappings_path = os.path.join(mappings_dir, "*.json")
        for mapping_filename in glob.glob(mappings_path):
            with open(mapping_filename, "r", encoding="utf-8") as fin:
                mapping = json.load(fin)
                if type(mapping) != type({}):
                    logging.error("File %s is not a JSON dictionary" % mapping_filename)
                    continue
                if mapping["type"] != "mapping":
                    logging.error("File %s is not a mapping file" % mapping_filename)
                    continue
                converter = Converter(mapping)
                if converter.in_lang == converter.out_lang:
                    logging.error("Cannot load reflexive (%s->%s) mapping from file %s" %
                        (converter.in_lang, converter.out_lang, mapping_filename))
                    continue
                self.add_converter(converter)

    def add_converter(self, converter):

        logging.debug("Adding converter between %s and %s" % (converter.in_lang, converter.out_lang))
        self.converters[(converter.in_lang, converter.out_lang)] = converter

        composites = []
        for (in_lang, out_lang), other_converter in self.converters.items():
            if converter.out_lang == in_lang and \
               converter.in_lang != out_lang and \
               (converter.in_lang, out_lang) not in self.converters:
               composite = CompositeConverter(converter, other_converter)
               self.add_converter(composite)
            elif converter.in_lang == out_lang and \
                 converter.out_lang != in_lang and \
                 (in_lang, converter.out_lang) not in self.converters:
                 composite = CompositeConverter(other_converter, converter)
                 self.add_converter(composite)

    def convert(self, text, in_lang, out_lang):
        if (in_lang, out_lang) not in self.converters:
            logging.error("No conversion found between %s and %s." % (in_lang, out_lang))
            return None, None
        converter = self.converters[(in_lang, out_lang)]
        return converter.convert(text)

if __name__ == '__main__':
    library = ConverterLibrary("mappings")
    result = library.convert("ƛʼiƛʼinʼa", "kwk-napa", "eng-arpabet")
    with open("test_output.json", "w", encoding="utf-8") as fout:
        fout.write(json.dumps(result,
                            ensure_ascii=False,
                            indent=4,
                            default=lambda o:o.to_json()))

# if __name__ == '__main__':
#     parser = argparse.ArgumentParser(description='Convert XML to another orthography while preserving tags')
#     parser.add_argument('mapping', type=str, help='Mapping filename')
#     parser.add_argument('input', type=str, help='Input XML')
#     parser.add_argument('output', type=str, help='Output XML')
#     args = parser.parse_args()
#     go(args.mapping, args.input, args.output)
