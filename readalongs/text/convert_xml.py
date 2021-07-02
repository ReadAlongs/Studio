#!/usr/bin/env python3
# -*- coding: utf-8 -*-

###########################################################################
#
# convert_xml.py
#
# This takes an XML file with xml:lang attributes and text in
# some orthography, and converts it to use English ARPABET symbols
# for speech processing.  (Provided, of course, that a conversion
# pipeline for it is available through the G2P library.)
# This XML file preserves complex markup, even within words
# (e.g. even if you have morpheme tags within words, it
# can perform phonological rules across those tags).
#
# Language attributes can be added at any level, even below the level of
# the word.  Like say I need to convert "Patrickƛən" (my name is Patrick)
# in Kwak'wala; neither an English nor Kwak'wala pipeline could appropriately
# convert this word.  I can mark that up as:
#
#  <w><m xml:lang="eng">Patrick</m><m xml:lang="kwk-napa">ƛən</m></w>
#
# to send the first part to the English conversion pipeline and the
# second part to the Kwak'wala pipeline.
#
# The only assumption made by this module about the structure of the XML
# is that it has word tags (using <w>, the convention used by TEI formats.)
# The reason for this is that the word is the domain over which phonological
# rules apply, and we particularly need to know it to be able to perform
# phonological rules at word boundaries.  We also only convert text that
# is part of words (i.e. we don't bother sending whitespace or punctuation
# through the G2P).
#
# So, if the XML file doesn't have word elements, tokenize it and add them.
#
# TODO: Document functions
############################################################################

from __future__ import absolute_import, division, print_function, unicode_literals

import argparse
import copy
import os
import unicodedata as ud

import text_unidecode
from g2p import make_g2p
from g2p.mappings.langs.utils import is_arpabet
from g2p.transducer import CompositeTransductionGraph, TransductionGraph

from readalongs.log import LOGGER
from readalongs.text.lexicon_g2p import getLexiconG2P
from readalongs.text.lexicon_g2p_mappings import __file__ as LEXICON_PATH
from readalongs.text.util import (
    get_lang_attrib,
    load_xml,
    save_xml,
    unicode_normalize_xml,
)


def convert_word(word: str, lang: str, output_orthography: str, verbose_warnings: bool):
    if lang == "eng":
        # Hack to use old English LexiconG2P
        # Note: adding eng_ prefix to vars that are used in both blocks to make mypy
        # happy. Since the two sides of the if and in the same scope, it complains about
        # type checking otherwise.
        assert output_orthography == "eng-arpabet"
        eng_tg = False
        eng_converter = getLexiconG2P(
            os.path.join(os.path.dirname(LEXICON_PATH), "cmu_sphinx.metadata.json")
        )
        try:
            eng_text, eng_indices = eng_converter.convert(word)
            eng_valid = is_arpabet(eng_text)
        except KeyError as e:
            if verbose_warnings:
                LOGGER.warning(f'Could not g2p "{word}" as English: {e.args[0]}')
            eng_text = word
            eng_indices = []
            eng_valid = False
        return eng_converter, eng_tg, eng_text, eng_indices, eng_valid
    else:
        if lang == "und":
            # First, we apply unidecode to map characters all all known alphabets in the
            # Unicode standard to their English representation, then we use g2p.
            text_to_g2p = text_unidecode.unidecode(word)
        else:
            text_to_g2p = word

        converter = make_g2p(lang, output_orthography)
        tg = converter(text_to_g2p)
        text = tg.output_string.strip()
        indices = tg.edges
        valid = converter.check(tg, shallow=True)
        if not valid and verbose_warnings:
            converter.check(tg, shallow=False, display_warnings=verbose_warnings)

        if lang == "und":
            # for now, we don't handle indices through unidecode, so overwrite the indices
            # converter returneed by just beginning-end index pairs
            # TODO: instead of this hack, prepend the indices from word to text_to_g2p to
            # indices.
            indices = [(0, 0), (len(word), len(text))]
            tg = None

        return converter, tg, text, indices, valid


def convert_words(
    xml,
    word_unit="w",
    output_orthography="eng-arpabet",
    g2p_fallbacks=[],
    verbose_warnings=False,
):
    all_g2p_valid = True
    for word in xml.xpath(".//" + word_unit):
        # if the word was already g2p'd, skip and keep existing ARPABET representation
        if "ARPABET" in word.attrib:
            arpabet = word.attrib["ARPABET"]
            if not is_arpabet(arpabet):
                LOGGER.warning(
                    f'Pre-g2p\'d text "{word.text}" has invalid ARPABET conversion "{arpabet}"'
                )
                all_g2p_valid = False
            continue
        # only convert text within words
        if not word.text:
            continue
        g2p_lang = (
            get_lang_attrib(word) or "und"
        )  # default to Undetermined if lang missing
        text_to_g2p = word.text
        converter, tg, g2p_text, indices, valid = convert_word(
            text_to_g2p, g2p_lang, output_orthography, verbose_warnings
        )
        if not valid:
            # This is where we apply the g2p cascade
            for lang in g2p_fallbacks:
                LOGGER.warning(
                    f'Could not g2p "{text_to_g2p}" as {g2p_lang}. Trying fallback: {lang}.'
                )
                g2p_lang = lang
                converter, tg, g2p_text, indices, valid = convert_word(
                    text_to_g2p, g2p_lang, output_orthography, verbose_warnings
                )
                if valid:
                    word.attrib["effective_g2p_lang"] = g2p_lang
                    break
            else:
                all_g2p_valid = False
                LOGGER.warning(
                    f'No valid g2p conversion found for "{text_to_g2p}". '
                    f"Check its orthography and language code, "
                    f"or pick suitable g2p fallback languages."
                )

        word.attrib["ARPABET"] = g2p_text

    return xml, all_g2p_valid


def convert_xml(
    xml,
    word_unit="w",
    output_orthography="eng-arpabet",
    g2p_fallbacks=[],
    verbose_warnings=False,
):
    xml_copy = copy.deepcopy(xml)
    xml_copy, valid = convert_words(
        xml_copy, word_unit, output_orthography, g2p_fallbacks, verbose_warnings
    )
    return xml_copy, valid


def go(
    input_filename, output_filename, word_unit="w", output_orthography="eng-arpabet"
):
    xml = load_xml(input_filename)
    converted_xml = convert_xml(xml, word_unit, output_orthography)
    save_xml(output_filename, converted_xml)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert XML to another orthography while preserving tags"
    )
    parser.add_argument("input", type=str, help="Input XML")
    parser.add_argument("output", type=str, help="Output XML")
    parser.add_argument(
        "--word_unit",
        type=str,
        default="w",
        help="XML element that " 'represents a word (default: "w")',
    )
    parser.add_argument(
        "--out_orth",
        type=str,
        default="eng-arpabet",
        help='Output orthography (default: "eng-arpabet")',
    )
    args = parser.parse_args()
    go(args.input, args.output, args.word_unit, args.out_orth)
