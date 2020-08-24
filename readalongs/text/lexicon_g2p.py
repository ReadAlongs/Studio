#!/usr/bin/env python3
# -*- coding: utf-8 -*-


#######################################################################
#
# lexicon_g2p.py
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
# TODO: Move this to the G2P library
######################################################################

from __future__ import division, print_function, unicode_literals

import os
from collections import defaultdict
from unicodedata import normalize

from readalongs.log import LOGGER
from readalongs.text.util import load_json, load_txt


def sphinx_lexicon_loader(input_path):
    txt = load_txt(input_path)
    for line in txt.split("\n"):
        parts = line.strip().split("\t")
        if len(parts) < 2:
            continue
        key = normalize("NFKC", parts[0])
        value = normalize("NFKC", parts[1])
        yield key, value


LEXICON_LOADERS = {"sphinx": sphinx_lexicon_loader}


class LexiconG2P:
    def __init__(self, metadata_path):
        self.metadata = load_json(metadata_path)
        self.in_lang = self.metadata["in_metadata"]["lang"]
        self.out_lang = self.metadata["out_metadata"]["lang"]

        dirname = os.path.dirname(metadata_path)
        if "src" not in self.metadata:
            LOGGER.error("File %s does not specify a source document", metadata_path)
            return
        self.src_path = os.path.join(dirname, self.metadata["src"])

        self.entries = defaultdict(list)
        if "src_format" not in self.metadata:
            LOGGER.error(
                "File %s lacking a source format ('src_format') attribute",
                metadata_path,
            )
            return

        if self.metadata["src_format"] not in LEXICON_LOADERS:
            LOGGER.error(
                "File %s references an unknown lexicon format: %s",
                metadata_path,
                self.metadata["src_format"],
            )

        self.loader = LEXICON_LOADERS[self.metadata["src_format"]]

    def __repr__(self):
        return f"{self.__class__} object for {self.in_lang} and {self.out_lang}"

    def load_entries(self):
        for key, value in self.loader(self.src_path):
            self.entries[key].append(value)

    def convert(self, text):
        if len(self.entries) == 0:
            self.load_entries()
        len_text = len(text)
        text = text.strip("#").strip()
        text = text.upper()
        if text not in self.entries:
            raise KeyError(
                "Word %s not found in lexicon %s" % (text, self.metadata["src"])
            )
        result = self.entries[text][0]
        indices = [(0, 0), (len_text, len(result))]
        return result, indices
