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

from g2p import make_g2p
from g2p.mappings.langs.utils import is_arpabet
from g2p.transducer import CompositeTransductionGraph, TransductionGraph

from readalongs.log import LOGGER
from readalongs.text.lexicon_g2p import getLexiconG2P
from readalongs.text.lexicon_g2p_mappings import __file__ as LEXICON_PATH
from readalongs.text.util import (
    compose_indices,
    compose_tiers,
    get_lang_attrib,
    increment_indices,
    increment_tiers,
    iterate_over_text,
    load_xml,
    offset_indices,
    save_xml,
    trim_indices,
    unicode_normalize_xml,
)


def get_same_language_units(element):
    character_counter = 0
    same_language_units = []
    current_sublang, current_subword = None, None
    for sublang, subword in iterate_over_text(element):
        if current_subword and sublang == current_sublang:
            current_subword += subword
            continue
        if current_subword:
            same_language_units.append(
                {
                    "index": character_counter,
                    "lang": current_sublang,
                    "text": current_subword,
                }
            )
            character_counter += len(current_subword)
        current_sublang, current_subword = sublang, subword
    if current_subword:
        same_language_units.append(
            {
                "index": character_counter,
                "lang": current_sublang,
                "text": current_subword,
            }
        )
    return same_language_units


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
        converter = make_g2p(lang, output_orthography)
        tg = converter(word)
        text = tg.output_string.strip()
        indices = tg.edges
        valid = converter.check(tg, shallow=True)
        if not valid and verbose_warnings:
            converter.check(tg, shallow=False, display_warnings=verbose_warnings)
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
        # only convert text within words
        same_language_units = get_same_language_units(word)
        if not same_language_units:
            return
        all_text = ""
        all_indices = []
        for unit in same_language_units:
            g2p_lang = unit["lang"]
            text_to_g2p = unit["text"]
            converter, tg, text, indices, valid = convert_word(
                text_to_g2p, g2p_lang, output_orthography, verbose_warnings
            )
            if not valid:
                # This is where we apply the g2p cascade
                for lang in g2p_fallbacks:
                    LOGGER.warning(
                        f'Could not g2p "{text_to_g2p}" as {g2p_lang}. Trying fallback: {lang}.'
                    )
                    g2p_lang = lang
                    converter, tg, text, indices, valid = convert_word(
                        text_to_g2p, g2p_lang, output_orthography, verbose_warnings
                    )
                    if valid:
                        break
                else:
                    all_g2p_valid = False
                    LOGGER.warning(
                        f'No valid g2p conversion found for "{unit["text"]}". '
                        f"Check its orthography and language code, "
                        f"or pick suitable g2p fallback languages."
                    )

            all_text += text
            all_indices += indices
        if tg and isinstance(tg, CompositeTransductionGraph):
            norm_form = converter._transducers[0].norm_form
            indices = increment_tiers(indices)
            all_indices = compose_tiers(indices)
        elif tg and isinstance(tg, TransductionGraph):
            norm_form = converter.norm_form
            indices = increment_indices(indices)
            all_indices = compose_indices([], indices)
        else:
            norm_form = None
            all_indices = indices
        if norm_form and norm_form != "none":
            word.text = ud.normalize(norm_form, word.text)
        replace_text_in_node(word, all_text, all_indices)
    return xml, all_g2p_valid


def replace_text_in_node(word, text, indices):
    old_text = ""
    new_text = ""
    # filter inputs
    new_indices = [x for x in {item[0]: item[1] for item in indices}.items()]
    # handle the text
    if word.text:
        for i1, i2 in new_indices:
            if i1 >= len(word.text):
                old_text = word.text[:i1]
                new_text = text[:i2]
                text = text[i2:]
                new_indices = offset_indices(indices, -len(old_text), -len(new_text))
                new_indices = trim_indices(new_indices)
                # word.attrib["orig"] = old_text
                word.text = new_text
                break

    for child in word:
        text, new_indices = replace_text_in_node(child, text, new_indices)
        if child.tail:
            for i1, i2 in new_indices:
                if i1 >= len(child.tail):
                    old_text = child.tail[:i1]
                    new_text = text[:i2]
                    text = text[i2:]
                    new_indices = offset_indices(
                        indices, -len(old_text), -len(new_text)
                    )
                    new_indices = trim_indices(new_indices)
                    child.tail = new_text
                    break
    return text, new_indices


def convert_xml(
    xml,
    word_unit="w",
    output_orthography="eng-arpabet",
    g2p_fallbacks=[],
    verbose_warnings=False,
):
    xml_copy = copy.deepcopy(xml)
    # FIXME: different langs have different normalizations, is this necessary?
    unicode_normalize_xml(xml_copy)
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
