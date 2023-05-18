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


def convert_words(  # noqa: C901
    xml, word_unit="w", output_orthography="eng-arpabet", verbose_warnings=False
):
    """Helper for convert_xml(), with the same Args and Return values, except
    xml is modified in place returned itself, instead of making a copy.
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

    all_g2p_valid = True
    for word in xml.xpath(".//" + word_unit):
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
                g2p_text, valid = convert_word(text_to_g2p, g2p_lang)
                if not valid:
                    # This is where we apply the g2p cascade
                    for lang in (
                        re.split(r"[,:]", g2p_fallbacks) if g2p_fallbacks else []
                    ):
                        _, langs = get_langs()
                        if g2p_fallback_warning_count < 2 or verbose_warnings:
                            g2p_fallback_warning_count += 1
                            LOGGER.warning(
                                f'Could not g2p "{text_to_g2p}" as {langs.get(g2p_lang, "")} ({g2p_lang}). '
                                f"Trying fallback: {langs.get(lang, '')} ({lang})."
                            )
                        g2p_lang = lang.strip()
                        g2p_text, valid = convert_word(text_to_g2p, g2p_lang)
                        if valid:
                            word.attrib["effective-g2p-lang"] = g2p_lang
                            break
                    else:
                        all_g2p_valid = False
                        if g2p_fail_warning_count < 2 or verbose_warnings:
                            g2p_fail_warning_count += 1
                            LOGGER.warning(
                                f'No valid g2p conversion found for "{text_to_g2p}". '
                                f"Check its orthography and language code, "
                                f"or pick suitable g2p fallback languages."
                            )

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
    xml, word_unit="w", output_orthography="eng-arpabet", verbose_warnings=False
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
