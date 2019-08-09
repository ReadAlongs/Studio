#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#######################################################################
#
# context_mapping_g2p.py
#
# A context-sensitive G2P system, based on a mapping file, that keeps track of
# indices to the original. Uses the external g2p library.
#
######################################################################

from __future__ import print_function, unicode_literals, division
import re
from readalongs.log import LOGGER
from .util import load_json
from unicodedata import normalize
from text_unidecode import unidecode

from g2p.mappings import Mapping
from g2p.transducer import Transducer

#TODO: Add fallback mechanism
# # fallback characters for when a stray letter gets in; we just take a guess
# # what they might mean.  otherwise, we assume "a" represents IPA "a", etc.
UNIDECODE_MAPPING = {  # note, these replacements should always be something
    "c": "t͡ʃ",         # in the eng-ipa mapping, because these characters don't
    "j": "ʒ",          # go through the approximate mapping process
    "y": "j"
}

class ContextG2P:
    def __init__(self, mapping_path, strict=False):
        self._json_map = load_json(mapping_path)
        self.case_sensitive = not self._json_map["in_metadata"].get('case_insensitive', False)
        self.escape_special_characters = self._json_map["in_metadata"].get('escape_special_characters', False)
        self.normalization = self._json_map['in_metadata'].get('normalization', 'NFD')
        self.mapping = Mapping(self._json_map['map'], norm_form=self.normalization, case_sensitive=self.case_sensitive, escape_special_characters=self.escape_special_characters, **{k:v for k,v in self._json_map.items() if k != 'map'})
        self.as_is = self.mapping.kwargs["in_metadata"].get('as_is', False)
        self.transducer = Transducer(self.mapping, as_is=self.as_is)
        self.in_lang = self.mapping.kwargs["in_metadata"]["lang"]
        self.out_lang = self.mapping.kwargs["out_metadata"]["lang"]
        self.input_delimiter = self.mapping.kwargs["in_metadata"].get('delimiter', '')
        self.output_delimiter = self.mapping.kwargs["out_metadata"].get('delimiter', '')
        self.strict = strict #TODO: Add strict support

    def __repr__(self):
        return f"{self.__class__} object for {self.in_lang} and {self.out_lang}"

    def convert(self, text, debugger=False):
        return self.transducer(text, index=True, debugger=debugger, output_delimiter=self.output_delimiter)

