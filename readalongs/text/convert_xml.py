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
# is that it has word tags (using <w>, the convention used by RAS and TEI formats.)
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

import copy
import re
from time import perf_counter
from typing import Optional

from readalongs.log import LOGGER
from readalongs.text.util import get_attrib_recursive, get_word_text, iterate_over_text
from readalongs.util import get_langs


def get_same_language_units(element):
    """Find all the text in element, grouped by units of the same language

    Returns: list of (lang, text) pairs
    """
    same_language_units = []
    current_sublang, current_subword = None, None
    for sublang, subword in iterate_over_text(element):
        sublang = sublang.strip() if sublang else ""
        if current_subword and sublang == current_sublang:
            current_subword += subword
        else:
            if current_subword:
                same_language_units.append((current_sublang, current_subword))
            current_sublang, current_subword = sublang, subword
    if current_subword:
        same_language_units.append((current_sublang, current_subword))
    return same_language_units


class TimeLimitException(Exception):
    pass


def convert_words(  # noqa: C901
    xml,
    word_unit: str = "w",
    output_orthography: str = "eng-arpabet",
    verbose_warnings: Optional[bool] = False,
    time_limit: Optional[int] = None,
):
    """Helper for convert_xml(), with the same Args and Return values, except
    xml is modified in place returned itself, instead of making a copy.

    Raises:
        TimeLimitException: if the time_limit is specified and exceeded
    """

    if output_orthography != "eng-arpabet":
        LOGGER.info(f"output_orthography={output_orthography}")

    # Defer expensive import of g2p to do them only if and when they are needed
    from g2p import InvalidLanguageCode, NoPath, make_g2p
    from g2p.mappings.langs.utils import is_arpabet

    # Warning counts so we don't flood the logs (unless verbose_warnings is set)
    g2p_fallback_warning_count = 0
    g2p_fail_warning_count = 0
    g2p_empty_warning_count = 0

    # Tuck this function inside convert_words(), to share common arguments and imports
    def convert_word(word: str, lang: str) -> Tuple[str, bool]:
        """Convert one individual word through the specified cascade of g2p mappings.

        Args:
            word: input word to map through g2p
            lang: the language code to use to attempt the g2p mapping

        Returns:
            g2p_text: the word mapping from lang to output_orthography
            valid: a flag indicating whether g2p conversion yielded valid
                output, which includes making sure IPA output was valid IPA and
                ARPABET output was valid ARPABET, at all intermediate steps as
                well as in the final output.
        """

        try:
            converter = make_g2p(lang, output_orthography, tokenize=False)
        except InvalidLanguageCode as e:
            raise ValueError(
                f'Could not g2p "{word}" from "{lang}" to "{output_orthography}": {e} '
                f'\nRun "readalongs langs" to list languages supported by ReadAlongs Studio.'
            ) from e
        except NoPath as e:
            raise ValueError(
                f'Could not g2p "{word}": no path from "{lang}" to "{output_orthography}".'
                f'\nRun "readalongs langs" to list languages supported by ReadAlongs Studio.'
            ) from e
        tg = converter(word)
        text = tg.output_string
        if not text:
            nonlocal g2p_empty_warning_count
            if g2p_empty_warning_count < 2 or verbose_warnings:
                g2p_empty_warning_count += 1
                LOGGER.warning(
                    f'The output of the g2p process for "{word}" with lang "{lang}" is empty.'
                )
        valid = converter.check(tg, shallow=True) and text
        if not valid and verbose_warnings:
            converter.check(tg, shallow=False, display_warnings=verbose_warnings)
        return text, valid

    def convert_word_with_cascade(
        text_to_g2p: str, g2p_lang: str, g2p_fallbacks: str
    ) -> Tuple[str, bool, Optional[str]]:
        """Convert one individual word through the specified cascade of g2p mappings.

        Args:
            text_to_g2p: input word to map through g2p
            g2p_lang: the language code to use to attempt the g2p mapping
            g2p_fallbacks: comma-separated list of language codes to try if lang fails

        Returns:
            g2p_text: the final g2p mapping of word
            valid: a flag indicating whether g2p conversion yielded valid
                output in the final fallback tried
            effective_language: indicates the language code that was used to convert the word:
                if g2p_lang was successfully used: None
                if a fallback lang was successfully used: that lang's code
                if no valid conversion was found: None (and valid==False)
        """
        g2p_text, valid = convert_word(text_to_g2p, g2p_lang)
        if valid:
            return g2p_text, True, None

        # This is where we apply the g2p cascade
        for lang in re.split(r"[,:]", g2p_fallbacks) if g2p_fallbacks else []:
            _, langs = get_langs()
            nonlocal g2p_fallback_warning_count
            if g2p_fallback_warning_count < 2 or verbose_warnings:
                g2p_fallback_warning_count += 1
                LOGGER.warning(
                    f'Could not g2p "{text_to_g2p}" as {langs.get(g2p_lang, "")} ({g2p_lang}). '
                    f"Trying fallback: {langs.get(lang, '')} ({lang})."
                )
            g2p_lang = lang.strip()
            g2p_text, valid = convert_word(text_to_g2p, g2p_lang)
            if valid:
                return g2p_text, True, g2p_lang
        else:
            nonlocal g2p_fail_warning_count
            if g2p_fail_warning_count < 2 or verbose_warnings:
                g2p_fail_warning_count += 1
                LOGGER.warning(
                    f'No valid g2p conversion found for "{text_to_g2p}". '
                    f"Check its orthography and language code, "
                    f"or pick suitable g2p fallback languages."
                )
            return g2p_text, False, None

    all_g2p_valid = True
    start_time = perf_counter()
    for i, word in enumerate(xml.xpath(".//" + word_unit)):
        if time_limit is not None and perf_counter() - start_time > time_limit:
            raise TimeLimitException(
                f"g2p conversion exceeded time limit of {time_limit} seconds. "
                f"Aborting after processing {i} tokens. Please use a shorter text."
            )
        # if the word was already g2p'd, skip and keep existing ARPABET representation
        if "ARPABET" in word.attrib:
            arpabet = word.attrib["ARPABET"]
            if not is_arpabet(arpabet):
                LOGGER.warning(
                    f'Pre-g2p\'d text "{get_word_text(word)}" has invalid ARPABET conversion "{arpabet}"'
                )
                all_g2p_valid = False
            continue
        # only convert text within words
        same_language_units = get_same_language_units(word)
        if not same_language_units:
            continue
        all_arpabet = ""
        for lang, text in same_language_units:
            g2p_lang = lang or "und"  # default: Undetermined
            g2p_fallbacks = get_attrib_recursive(word, "fallback-langs")
            text_to_g2p = text.strip()
            try:
                g2p_text, valid, effective_g2p_lang = convert_word_with_cascade(
                    text_to_g2p, g2p_lang, g2p_fallbacks
                )
                if not valid:
                    all_g2p_valid = False
                if effective_g2p_lang:
                    word.attrib["effective-g2p-lang"] = effective_g2p_lang

                # Save the g2p_text from the last conversion attemps, even when
                # it's not valid, so it's in the g2p output if the user wants to
                # inspect it manually.

                all_arpabet = all_arpabet + " " + g2p_text.strip()

            except ValueError as e:
                LOGGER.warning(
                    f'Could not g2p "{text_to_g2p}" due to an incorrect '
                    f'"xml:lang", "lang" or "fallback-langs" attribute in the XML: {e}'
                )
                all_g2p_valid = False

                if not verbose_warnings:
                    break

        word.attrib["ARPABET"] = all_arpabet.strip()

    return xml, all_g2p_valid


def convert_xml(
    xml,
    word_unit: str = "w",
    output_orthography: str = "eng-arpabet",
    verbose_warnings: Optional[bool] = False,
    time_limit: Optional[int] = None,
):
    """Convert all the words in XML though g2p, putting the results in attribute ARPABET

    Args:
        xml (etree): input XML
        word_unit: which XML element should be considered the unit to g2p
        output_orthography: target language for g2p mappings
        verbose_warnings: whether (very!) verbose g2p errors should be produced
        time_limit: if not None, maximum time in seconds to spend on g2p conversion

    Returns:
        xml (etree), valid (bool):
          - xml is a deepcopy of the input xml with the ARPABET attribute added
            to each word_unit element;
          - valid is a flag indicating whether all words were g2p'd successfully

    Raises:
        TimeLimitException: if the time_limit is specified and exceeded
    """
    xml_copy = copy.deepcopy(xml)
    xml_copy, valid = convert_words(
        xml_copy, word_unit, output_orthography, verbose_warnings, time_limit
    )
    return xml_copy, valid
