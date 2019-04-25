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
###################################################

from __future__ import print_function, unicode_literals
from __future__ import division, absolute_import

from copy import deepcopy
from lxml import etree
import argparse, os
import logging
from glob import glob
from collections import defaultdict
import numpy as np
from unicodedata import normalize
from decimal import Decimal, getcontext

from readalongs.g2p.util import (load_xml, save_xml, load_json,
    get_lang_attrib, set_lang_attrib, iterate_over_text)
from readalongs.g2p.create_inv_from_map import create_inventory_from_mapping
from .. import lang


class LanguageIdentifier:

    def __init__(self, lang_dir, seen_factor=1.0, unseen_factor=0.01):
        self.seen_factor = seen_factor
        self.unseen_factor = unseen_factor
        self.langs = {}
        self.chars = {}
        self.inventories = {}  # mapping from lang to character inventories
        self.lang_dir = lang_dir
        self.load_inventories()
        self.calculate_prior_probs()

    def load_inventories(self):
        for _, subdir in lang.lang_dirs(self.lang_dir):
            for lang_filename in glob(os.path.join(subdir, "*.json")):
                try:
                    inv = load_json(lang_filename)
                except:
                    logging.error("Invalid JSON in file %s", lang_filename)
                    continue
                if not isinstance(inv, dict):
                    logging.error("File %s is not a JSON dictionary",
                                  mapping_filename)
                    continue
                if ("type" not in inv):
                    logging.error("File %s is not a supported "
                                  "conversion format", mapping_filename)
                    continue
                if inv["type"] == "inventory":
                    self.add_inventory(inv)
                    continue
                if inv["type"] == "mapping":
                    inv = create_inventory_from_mapping(inv, "in")
                    self.add_inventory(inv)
                    continue


    def add_inventory(self, inv):
        chars = set()
        lang = inv["metadata"]["lang"]
        if not inv["metadata"].get("display", False):
            return      # not an input orthography
        if lang not in self.langs:
            self.langs[lang] = len(self.langs) # make an index for it
        for s in inv["inventory"]:
            s = normalize("NFD", s)
            for c in s:
                if c not in self.chars:  # not yet seen in any lang
                    self.chars[c] = len(self.chars) # make an index for it
                chars.add(s)
        self.inventories[lang] = chars

    def calculate_prior_probs(self):
        probs = np.full((len(self.langs), len(self.chars)), self.unseen_factor)
        for lang, lang_index in self.langs.items():
            seen_indices = [ self.chars[c] for s in self.inventories[lang]
                                           for c in s ]
            probs[lang_index,seen_indices] = self.seen_factor
        probs /= probs.sum(axis=1, keepdims=True)
        self.logprobs = np.log(probs)

    def identify_text(self, s):
        # get the probabilities for each language
        logprobs = np.zeros((len(self.langs),))
        for c in s:
            if c not in self.chars:
                continue            # not a character we use for language id
            char_index = self.chars[c]
            logprobs += self.logprobs[:, char_index]

        logprobs -= np.max(logprobs)  # logprob scaling trick for normalization
        probs = np.exp(logprobs)      # turn back into probs
        probs /= probs.sum()          # normalize

        # return them in a more convenient format
        result = [ (lang, probs[i]) for lang, i in self.langs.items() ]
        return sorted(result, key=lambda x:x[1], reverse=True)


def add_lang_ids(xml, mapping_dir, unit="p"):
    lang_identifier = LanguageIdentifier(mapping_dir)

    elements = xml.xpath(".//" + unit)
    if not elements:
        elements = [xml]
    for element in elements:
        add_lang_ids_to_element(element, lang_identifier)
    return xml

def add_lang_ids_to_element(element, lang_identifier):
    if get_lang_attrib(element):
        return
    text = [ text for lang, text in iterate_over_text(element) ]
    text = "".join(text)
    text = normalize("NFD", text)
    lang_ids = lang_identifier.identify_text(text)
    lang_id = lang_ids[0][0]  # for now just take the most likely
    set_lang_attrib(element, lang_id)


def main(input_path, output_path, mapping_dir, unit="p"):
    xml = load_xml(input_path)
    add_lang_ids(xml, mapping_dir, unit)
    save_xml(output_path, xml)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Convert XML to another orthography while preserving tags')
    parser.add_argument('input', type=str, help='Input XML')
    parser.add_argument('output', type=str, help='Output XML')
    parser.add_argument('--mapping-dir', type=str,
            help="Alternate directory containing orthography mappings")
    parser.add_argument('--unit', type=str, default="p",
            help="Unit at which to do language identification")
    args = parser.parse_args()
    main(args.input, args.output, args.mapping_dir, args.unit)
