#!/usr/bin/env python3
# -*- coding: utf-8 -*-

###################################################
#
# add_ids_to_xml.py
#
# In order to tell visualization systems, "highlight this
# thing at this time", the document has to be able to identify
# particular elements.  If the original document does NOT have
# id tags on its elements, this module adds some.
#
# The auto-generated IDs have formats like "s0w2m1" meaning
# "sentence 0, word 2, morpheme 1".  But it's flexible if some elements
# already have ids, or if the markup uses different tags than a TEI document.
#
# TODO: Add numpy standard docstrings to functions
###################################################

from __future__ import absolute_import, division, print_function, unicode_literals

import argparse
from unicodedata import normalize

import numpy as np
from g2p.mappings import Mapping
from g2p.mappings.langs import MAPPINGS_AVAILABLE
from g2p.mappings.utils import is_dummy, is_ipa, is_xsampa

from readalongs.text.util import (
    get_lang_attrib,
    iterate_over_text,
    load_xml,
    save_xml,
    set_lang_attrib,
)


class LanguageIdentifier:
    def __init__(self, seen_factor=1.0, unseen_factor=0.01):
        self.seen_factor = seen_factor
        self.unseen_factor = unseen_factor
        self.inventories_loaded = False
        # Use lazy initialization so this expensive code is only run when really needed
        # self.load_inventories()

    def load_inventories(self):
        self.chars = {}
        self.inventories = {}
        for x in MAPPINGS_AVAILABLE:
            if (
                not is_ipa(x["in_lang"])
                and not is_xsampa(x["in_lang"])
                and not is_dummy(x["in_lang"])
            ):
                mapping = Mapping(in_lang=x["in_lang"], out_lang=x["out_lang"])
                self.inventories[x["in_lang"]] = set(mapping.inventory("in"))
                for s in self.inventories[x["in_lang"]]:
                    for c in s:
                        if c not in self.chars:  # not yet seen in any lang
                            # make an index for it
                            self.chars[c] = len(self.chars)
        self.langs = {k: i for i, k in enumerate(self.inventories.keys())}
        self.calculate_prior_probs()
        self.inventories_loaded = True

    def calculate_prior_probs(self):
        probs = np.full((len(self.langs), len(self.chars)), self.unseen_factor)
        for lang, lang_index in self.langs.items():
            seen_indices = [self.chars[c] for s in self.inventories[lang] for c in s]
            probs[lang_index, seen_indices] = self.seen_factor
        probs /= probs.sum(axis=1, keepdims=True)
        self.logprobs = np.log(probs)

    def identify_text(self, s):
        if not self.inventories_loaded:
            # Trigger real initialization, we really need it now.
            self.load_inventories()
        # get the probabilities for each language
        logprobs = np.zeros((len(self.langs),))
        for c in s:
            if c not in self.chars:
                continue  # not a character we use for language id
            char_index = self.chars[c]
            logprobs += self.logprobs[:, char_index]

        logprobs -= np.max(logprobs)  # logprob scaling trick for normalization
        probs = np.exp(logprobs)  # turn back into probs
        probs /= probs.sum()  # normalize

        # return them in a more convenient format
        result = [(lang, probs[i]) for lang, i in self.langs.items()]
        return sorted(result, key=lambda x: x[1], reverse=True)


def add_lang_ids(xml, unit="p"):
    lang_identifier = LanguageIdentifier()
    elements = xml.xpath(".//" + unit)
    if not elements:
        elements = [xml]
    for element in elements:
        add_lang_ids_to_element(element, lang_identifier)
    return xml


def add_lang_ids_to_element(element, lang_identifier):
    if get_lang_attrib(element):
        return
    text = [text for lang, text in iterate_over_text(element)]
    text = "".join(text)
    text = normalize("NFD", text)
    lang_ids = lang_identifier.identify_text(text)
    lang_id = lang_ids[0][0]  # for now just take the most likely
    set_lang_attrib(element, lang_id)


def main(input_path, output_path, unit="p"):
    xml = load_xml(input_path)
    add_lang_ids(xml, unit)
    save_xml(output_path, xml)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert XML to another orthography while preserving tags"
    )
    parser.add_argument("input", type=str, help="Input XML")
    parser.add_argument("output", type=str, help="Output XML")
    parser.add_argument(
        "--unit",
        type=str,
        default="p",
        help="Unit at which to do language identification",
    )
    args = parser.parse_args()
    main(args.input, args.output, args.unit)
