#!/usr/bin/env python3

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

import argparse
import copy
import os
import re

from readalongs.log import LOGGER
from readalongs.text.lexicon_g2p import getLexiconG2P
from readalongs.text.lexicon_g2p_mappings import __file__ as LEXICON_PATH
from readalongs.text.util import (
    get_attrib_recursive,
    get_lang_attrib,
    load_xml,
    save_xml,
)
from readalongs.util import getLangs


def convert_words(  # noqa: C901
    xml, word_unit="w", output_orthography="eng-arpabet", verbose_warnings=False,
):
    """Helper for convert_xml(), with the same Args and Return values, except
    xml is modified in place returned itself, instead of making a copy.
    """

    if output_orthography != "eng-arpabet":
        LOGGER.info(f"output_orthography={output_orthography}")

    # Defer expensive import of g2p to do them only if and when they are needed
    from g2p.mappings.langs.utils import is_arpabet

    try:
        # g2p > 0.5.20211029 uses its own exceptions for make_g2p errors
        from g2p import InvalidLanguageCode, NoPath, make_g2p
    except ImportError:
        # g2p <= 0.5.20211029 used NetworkXNoPath and FileNotFoundError
        from g2p import NetworkXNoPath as NoPath
        from g2p import make_g2p

        InvalidLanguageCode = FileNotFoundError

    # Tuck this function inside convert_words(), to share common arguments and imports
    def convert_word(word: str, lang: str):
        """Convert one individual word through the specified cascade of g2p mappings.

        Args:
            word (str): input word to map through g2p
            lang (str): the language code to use to attempt the g2p mapping

        Returns:
            g2p_text (str), valid(bool):
              - g2p_text is the word mapping from lang to output_orthography
              - valid is a flag indicating whether g2p conversion yielded valid
                output, which includes making sure IPA output was valid IPA and
                ARPABET output was valid ARPABET, at all intermediate steps as
                well as in the final output.
        """

        if lang == "eng":
            # Hack to use old English LexiconG2P
            # Note: adding eng_ prefix to vars that are used in both blocks to make mypy
            # happy. Since the two sides of the if and in the same scope, it complains about
            # type checking otherwise.
            assert "eng-arpabet" in output_orthography
            eng_converter = getLexiconG2P(
                os.path.join(os.path.dirname(LEXICON_PATH), "cmu_sphinx.metadata.json")
            )
            try:
                eng_text, _ = eng_converter.convert(word)
                eng_valid = is_arpabet(eng_text)
            except KeyError as e:
                if verbose_warnings:
                    LOGGER.warning(f'Could not g2p "{word}" as English: {e.args[0]}')
                eng_text = word
                eng_valid = False
            return eng_text, eng_valid
        else:
            try:
                converter = make_g2p(lang, output_orthography)
            except InvalidLanguageCode as e:
                raise ValueError(
                    f'Could not g2p "{word}" as "{lang}": invalid language code. '
                    f"Use one of {getLangs()[0]}"
                ) from e
            except NoPath as e:
                raise ValueError(
                    f'Count not g2p "{word}" as "{lang}": no path to "{output_orthography}". '
                    f"Use one of {getLangs()[0]}"
                ) from e
            tg = converter(word)
            text = tg.output_string.strip()
            valid = converter.check(tg, shallow=True)
            if not valid and verbose_warnings:
                converter.check(tg, shallow=False, display_warnings=verbose_warnings)
            return text, valid

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
        g2p_lang = get_lang_attrib(word) or "und"  # default: Undetermined
        g2p_fallbacks = get_attrib_recursive(word, "fallback-langs")
        text_to_g2p = word.text
        try:
            g2p_text, valid = convert_word(text_to_g2p, g2p_lang.strip())
            if not valid:
                # This is where we apply the g2p cascade
                for lang in re.split(r"[,:]", g2p_fallbacks) if g2p_fallbacks else []:
                    LOGGER.warning(
                        f'Could not g2p "{text_to_g2p}" as {g2p_lang}. '
                        f"Trying fallback: {lang}."
                    )
                    g2p_lang = lang.strip()
                    g2p_text, valid = convert_word(text_to_g2p, g2p_lang)
                    if valid:
                        word.attrib["effective-g2p-lang"] = g2p_lang
                        break
                else:
                    all_g2p_valid = False
                    LOGGER.warning(
                        f'No valid g2p conversion found for "{text_to_g2p}". '
                        f"Check its orthography and language code, "
                        f"or pick suitable g2p fallback languages."
                    )

            # Save the g2p_text from the last conversion attemps, even when
            # it's not valid, so it's in the g2p output if the user wants to
            # inspect it manually.
            word.attrib["ARPABET"] = g2p_text

        except ValueError as e:
            LOGGER.warning(
                f'Could not g2p "{text_to_g2p}" due to an incorrect '
                f'"xml:lang", "lang" or "fallback-langs" attribute in the XML: {e}'
            )
            all_g2p_valid = False

    return xml, all_g2p_valid


def convert_xml(
    xml, word_unit="w", output_orthography="eng-arpabet", verbose_warnings=False,
):
    """Convert all the words in XML though g2p, putting the results in attribute ARPABET

    Args:
        xml (etree): input XML
        word_unit (str): which XML element should be considered the unit to g2p
        output_orthography (str): target language for g2p mappings
        verbose_warnings (bool): whether (very!) verbose g2p errors should be produced

    Returns:
        xml (etree), valid (bool):
          - xml is a deepcopy of the input xml with the ARPABET attribute added
            to each word_unit element;
          - valid is a flag indicating whether all words were g2p'd successfully
    """
    xml_copy = copy.deepcopy(xml)
    xml_copy, valid = convert_words(
        xml_copy, word_unit, output_orthography, verbose_warnings
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
