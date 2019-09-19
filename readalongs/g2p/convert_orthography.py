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

from __future__ import print_function, unicode_literals
from __future__ import division, absolute_import

from readalongs.log import LOGGER
import json
import os
import copy

from io import open
from typing import List, Tuple
from g2p.transducer.indices import Indices, IndexSequence
from readalongs.g2p.context_g2p import ContextG2P
from readalongs.g2p.lexicon_g2p import LexiconG2P

def compose_indices1(i1, i2):
    if not i1:
        return i2
    composed = dict(i2)
    print(i1)
    print(i2)
    for i, tup in enumerate(i1):
        try:
            i1_in, i1_out = i1[i][0], i1[i][1]
        except IndexError:
            i1_in, i1_out = i1[-1][0], i1[-1][1]
        try:
            i2_in, i2_out = i2[i][0], i2[i][1]
        except IndexError:
            i2_in, i2_out = i2[-1][0], i2[-1][1]
        highest_in = max(i1_in, i2_in)
        highest_out = max(i1_out, i2_out)
        composed[highest_in] = highest_out
    composed_tups = [(k, v) for k, v in composed.items()]
    print(f"composed: {composed_tups}")
    return composed_tups


def compose_indices(i1, i2):
    print(i1)
    print(i2)
    if not i1:
        return i2
    i2_dict = dict(i2)
    i2_idx = 0
    results = []
    for i1_in, i1_out in i1:
        highest_i2_found = 0 if not results else results[-1][1]
        while i2_idx <= i1_out:
            if i2_idx in i2_dict and i2_dict[i2_idx] > highest_i2_found:
                highest_i2_found = i2_dict[i2_idx]
            i2_idx += 1
        if results:
            assert(i1_in >= results[-1][0])
            assert(highest_i2_found >= results[-1][1])
        results.append((i1_in, highest_i2_found))
    print(f"composed: {results}")
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
    return [(i1 + n1, i2 + n2) for i1, i2 in idxs]


def trim_indices(idxs):
    result = []
    for i1, i2 in idxs:
        i1 = max(i1, 0)
        i2 = max(i2, 0)
        if (i1, i2) in result:
            continue
        result.append((i1, i2))
    return result

class CompositeConverter:
    def __init__(self, converter1, converter2):
        if converter1.out_lang != converter2.in_lang:
            LOGGER.error("Cannot compose converter %s->%s "
                         "and converter %s->%s" %
                         (converter1.in_lang, converter1.out_lang,
                          converter2.in_lang, converter2.out_lang))
        self.converter1 = converter1
        self.converter2 = converter2
        self.in_lang = self.converter1.in_lang
        self.out_lang = self.converter2.out_lang

    def __repr__(self):
        return f"{self.__class__} object for {self.in_lang} and {self.out_lang}"

    def debug(self, text, *converters):
        debugged = []
        for converter in converters:
            if isinstance(converter, ContextG2P):
                converted = converter.convert(text, debugger=True)
                debugged.append(converted)
                text = converted[0]
            elif isinstance(converter, CompositeConverter):
                debugged.append(self.debug(
                    text, converter.converter1, converter.converter2))
            else:
                LOGGER.error(
                    "Sorry, there are only debugging handlers for ContextG2P transducers.")
        return debugged

    def convert(self, text, debugger=False):
        if debugger:
            return self.debug(text, self.converter1, self.converter2)
        c1_text, c1_indices = self.converter1.convert(text)
        c2_text, c2_indices = self.converter2.convert(c1_text)
        final_indices = IndexSequence(c1_indices, c2_indices)
        return c2_text, final_indices


G2P_HANDLERS = {
    "mapping": ContextG2P,
    "lexicon": LexiconG2P
}


# class ConverterLibrary:
#     def __init__(self, mappings_dir=None):
#         self.converters = {}
#         for _, langdir in lang.lang_dirs(mappings_dir):
#             for mapping_filename in os.listdir(langdir):
#                 if not mapping_filename.endswith('json'):
#                     continue
#                 mapping_filename = os.path.join(langdir, mapping_filename)
#                 with open(mapping_filename, "r", encoding="utf-8") as fin:
#                     mapping = json.load(fin)
#                     if not isinstance(mapping, dict):
#                         LOGGER.error("File %s is not a JSON dictionary",
#                                      mapping_filename)
#                         continue
#                     if "type" not in mapping:
#                         LOGGER.error("File %s is not a supported "
#                                      "conversion format", mapping_filename)
#                         continue
#                     if mapping["type"] == "inventory":
#                         continue
#                     if mapping["type"] not in G2P_HANDLERS:
#                         LOGGER.error("File %s is not a supported "
#                                      "conversion format", mapping_filename)
#                         continue
#                     converter = G2P_HANDLERS[mapping["type"]](mapping_filename)
#                     if converter.in_lang == converter.out_lang:
#                         LOGGER.error("Cannot load reflexive (%s->%s) "
#                                      "mapping from file %s",
#                                      converter.in_lang, converter.out_lang,
#                                      mapping_filename)
#                         continue
#                     self.add_converter(converter)
#         self.transitive_closure()

#     def add_converter(self, converter):
#         # LOGGER.info("Adding converter between %s and %s",
#         #              converter.in_lang, converter.out_lang)
#         self.converters[(converter.in_lang, converter.out_lang)] = converter

#     def transitive_closure(self):
#         n_converters = -1
#         # FIXME: Might need to detect cycles here!
#         # Cycles are prohibited by the in_lang/out_lang comparisons. --Pat
#         while len(self.converters) != n_converters:
#             for converter in list(self.converters.values()):
#                 converters = list(self.converters.items())
#                 for (in_lang, out_lang), other_converter in converters:
#                     if (converter.out_lang == in_lang and
#                             converter.in_lang != out_lang and
#                             (converter.in_lang, out_lang) not in self.converters):
#                         composite = CompositeConverter(
#                             converter, other_converter)
#                         self.add_converter(composite)
#                     elif (converter.in_lang == out_lang and
#                           converter.out_lang != in_lang and
#                           (in_lang, converter.out_lang) not in self.converters):
#                         composite = CompositeConverter(
#                             other_converter, converter)
#                         self.add_converter(composite)
#             n_converters = len(self.converters)

#     def convert(self, text, in_lang, out_lang, debugger=False):
#         if (in_lang, out_lang) not in self.converters:
#             LOGGER.error("No conversion found between %s and %s.",
#                          in_lang, out_lang)
#             return None, None
#         converter = self.converters[(in_lang, out_lang)]
#         # breakpoint()
#         if debugger:
#             if isinstance(converter, ContextG2P) or isinstance(converter, CompositeConverter):
#                 return converter.convert(text, debugger=debugger)
#             else:
#                 LOGGER.info("'debugger' was set to True but debugger is only supported for a \
#                             ContextG2P converter and the converter you're trying to debug is % s", converter)
#         else:
#             return converter.convert(text)
