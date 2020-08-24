#!/usr/bin/env python3
# -*- coding: utf-8 -*-

###########################################
#
# util.py
#
# Just some shared functions
#
# TODO: Add numpy standard format docstrings
############################################

from __future__ import division, print_function, unicode_literals

import json
import os
import zipfile
from collections import OrderedDict
from copy import deepcopy
from io import TextIOWrapper, open
from unicodedata import category, normalize

from lxml import etree

from readalongs.log import LOGGER

# removed "try: unicode() except" block (was for Python 2), but this file uses unicode()
# too many times, so define it anyway.
unicode = str


def ensure_dirs(path):
    dirname = os.path.dirname(path)
    if dirname and not os.path.exists(dirname):
        os.makedirs(dirname)


def xpath_default(xml, query, default_namespace_prefix="i"):
    nsmap = xml.nsmap if hasattr(xml, "nsmap") else xml.getroot().nsmap
    nsmap = dict(
        ((x, y) if x else (default_namespace_prefix, y)) for (x, y) in nsmap.items()
    )
    for e in xml.xpath(query, namespaces=nsmap):
        yield e


def iterate_over_text(element):
    lang = get_lang_attrib(element)
    if element.text:
        yield (lang, unicode(element.text))
    for child in element:
        for subchild in iterate_over_text(child):
            yield subchild
        if child.tail:
            yield (lang, unicode(child.tail))


def get_lang_attrib(element):
    lang_path = element.xpath("./@xml:lang")
    if not lang_path and "lang" in element.attrib:
        lang_path = element.attrib["lang"]
    if not lang_path and element.getparent() is not None:
        return get_lang_attrib(element.getparent())
    if not lang_path:
        return None
    return lang_path[0]


def is_do_not_align(element):
    dna = element.attrib.get("do-not-align", "")
    return dna == "true" or dna == "True" or dna == "TRUE" or dna == "1"


def is_do_not_align_recursive(element):
    if "do-not-align" in element.attrib:
        dna = element.attrib["do-not-align"]
        return dna == "true" or dna == "True" or dna == "TRUE" or dna == "1"
    elif element.getparent() is not None:
        return is_do_not_align_recursive(element.getparent())
    else:
        return False


def set_lang_attrib(element, lang):
    nsmap = element.nsmap if hasattr(element, "nsmap") else element.getroot().nsmap
    xml_ns = nsmap.get("xml", "http://www.w3.org/XML/1998/namespace")
    key = "{%s}lang" % xml_ns
    element.attrib[key] = lang


def merge_if_same_label(lst_of_dicts, text_key, label_key):
    results = []
    current_item = None
    for dct in lst_of_dicts:
        if label_key not in dct:
            dct[label_key] = None
        if not current_item:
            current_item = deepcopy(dct)
            continue
        if dct[label_key] == current_item[label_key]:
            current_item[text_key] += dct[text_key]
        else:
            results.append(current_item)
            current_item = deepcopy(dct)
    if current_item:
        results.append(current_item)
    return results


def load_xml(input_path):
    with open(input_path, "rb") as fin:
        return etree.fromstring(fin.read())


def load_xml_zip(zip_path, input_path):
    with zipfile.ZipFile(zip_path, "r") as fin_zip:
        with fin_zip.open(input_path, "r") as fin:
            return etree.fromstring(fin)


def load_xml_with_encoding(input_path):
    """ etree.fromstring messes up on declared encodings """
    return etree.parse(input_path)


def save_xml(output_path, xml):
    ensure_dirs(output_path)
    with open(output_path, "wb") as fout:
        fout.write(etree.tostring(xml, encoding="utf-8", xml_declaration=True))
        fout.write("\n".encode("utf-8"))


def save_xml_zip(zip_path, output_path, xml):
    ensure_dirs(zip_path)
    with zipfile.ZipFile(zip_path, "a", compression=zipfile.ZIP_DEFLATED) as fout_zip:
        fout_zip.writestr(
            output_path,
            etree.tostring(xml, encoding="utf-8", xml_declaration=True) + "\n",
        )


def load_txt(input_path):
    with open(input_path, "r", encoding="utf-8") as fin:
        return fin.read()


def load_txt_zip(zip_path, input_path):
    with zipfile.ZipFile(zip_path, "r") as fin_zip:
        with fin_zip.open(input_path, "r") as fin:
            fin_utf8 = TextIOWrapper(fin, encoding="utf-8")
            return fin_utf8.read()


def save_txt(output_path, txt):
    ensure_dirs(output_path)
    with open(output_path, "w", encoding="utf-8") as fout:
        fout.write(txt)


def save_txt_zip(zip_path, output_path, txt):
    ensure_dirs(zip_path)
    with zipfile.ZipFile(zip_path, "a", compression=zipfile.ZIP_DEFLATED) as fout_zip:
        fout_zip.writestr(output_path, txt.encode("utf-8"))


def load_json(input_path):
    with open(input_path, "r", encoding="utf-8") as fin:
        return json.load(fin, object_pairs_hook=OrderedDict)


def load_json_zip(zip_path, input_path):
    with zipfile.ZipFile(zip_path, "r") as fin_zip:
        with fin_zip.open(input_path, "r") as fin:
            fin_utf8 = TextIOWrapper(fin, encoding="utf-8")
            return json.loads(fin_utf8.read(), object_pairs_hook=OrderedDict)


def save_json(output_path, obj):
    ensure_dirs(output_path)
    with open(output_path, "w", encoding="utf-8") as fout:
        fout.write(unicode(json.dumps(obj, ensure_ascii=False, indent=4)))


def save_json_zip(zip_path, output_path, obj):
    ensure_dirs(zip_path)
    txt = unicode(json.dumps(obj, ensure_ascii=False, indent=4))
    with zipfile.ZipFile(zip_path, "a") as fout_zip:
        fout_zip.writestr(output_path, txt.encode("utf-8"))


def copy_file_to_zip(zip_path, origin_path, destination_path):
    ensure_dirs(zip_path)
    with zipfile.ZipFile(zip_path, "a", compression=zipfile.ZIP_DEFLATED) as fout_zip:
        fout_zip.write(origin_path, destination_path)


def load_tsv(input_path, labels):
    results = []
    with open(input_path, "r", encoding="utf-8") as fin:
        for i, line in enumerate(fin, start=1):
            pieces = line.strip("\n").strip(" ").split("\t")
            if len(pieces) > len(labels):
                LOGGER.error("More columns than labels on line %s" % i)
                continue
            results.append(OrderedDict(zip(labels, pieces)))
    return results


def unicode_normalize_xml(element):
    if element.text:
        element.text = normalize("NFD", unicode(element.text))
    for child in element.getchildren():
        unicode_normalize_xml(child)
        if child.tail:
            child.tail = normalize("NFD", unicode(child.tail))


CATEGORIES = {
    "Cc": "other",  # Other, Control
    "Cf": "other",  # Other, Format
    "Cn": "other",  # Other, Not Assigned (no characters in the file have this property)
    "Co": "letter",  # Other, Private Use
    "Cs": "other",  # Other, Surrogate
    "LC": "letter",  # Letter, Cased
    "Ll": "letter",  # Letter, Lowercase
    "Lm": "letter",  # Letter, Modifier
    "Lo": "letter",  # Letter, Other
    "Lt": "letter",  # Letter, Titlecase
    "Lu": "letter",  # Letter, Uppercase
    "Mc": "diacritic",  # Mark, Spacing Combining
    "Me": "diacritic",  # Mark, Enclosing
    "Mn": "diacritic",  # Mark, Nonspacing
    "Nd": "number",  # Number, Decimal Digit
    "Nl": "number",  # Number, Letter
    "No": "number",  # Number, Other
    "Pc": "punctuation",  # Punctuation, Connector
    "Pd": "punctuation",  # Punctuation, Dash
    "Pe": "punctuation",  # Punctuation, Close
    "Pf": "punctuation",  # Punctuation, Final quote (may behave like Ps or Pe depending on usage)
    "Pi": "punctuation",  # Punctuation, Initial quote (may behave like Ps or Pe depending on usage)
    "Po": "punctuation",  # Punctuation, Other
    "Ps": "punctuation",  # Punctuation, Open
    "Sc": "symbol",  # Symbol, Currency
    "Sk": "symbol",  # Symbol, Modifier
    "Sm": "symbol",  # Symbol, Math
    "So": "symbol",  # Symbol, Other
    "Zl": "whitespace",  # Separator, Line
    "Zp": "whitespace",  # Separator, Paragraph
    "Zs": "whitespace",  # Separator, Space
}


def get_unicode_category(c):
    """ Maps a character to one of [ "letter", "number", "diacritic", "punctuation",
        "symbol", "whitespace", "other"] """
    cat = category(c)
    assert cat in CATEGORIES
    return CATEGORIES[cat]


def compose_indices(i1, i2):
    if not i1:
        return i2
    i2_dict = dict(i2)
    i2_idx = 0
    results = []
    for i1_in, i1_out in i1:
        highest_i2_found = 0 if not results else results[-1][1]
        if i1_out is None:
            results.append((i1_in, highest_i2_found))
            continue
        while i2_idx <= i1_out:
            if i2_idx in i2_dict and i2_dict[i2_idx] > highest_i2_found:
                highest_i2_found = i2_dict[i2_idx]
            i2_idx += 1
        if results:
            assert i1_in >= results[-1][0]
            assert highest_i2_found >= results[-1][1]
        results.append((i1_in, highest_i2_found))
    return results


def compose_tiers(tiers):
    counter = 2
    reduced_indices = compose_indices(tiers[0], tiers[1])
    while counter < len(tiers):
        reduced_indices = compose_indices(reduced_indices, tiers[counter])
        counter += 1
    return reduced_indices


def concat_indices(i1, i2):
    if not i1:
        return i2
    results = deepcopy(i1)
    offset1, offset2 = results[-1]
    for i1, i2 in i2[1:]:
        results.append((i1 + offset1, i2 + offset2))
    return results


def offset_indices(idxs, n1, n2):
    return [(i1 + n1, i2 + n2) for i1, i2 in idxs]


def increment_indices(indices):
    new_indices = []
    for i, index in enumerate(indices):
        inp = index[0]
        outp = index[1]
        if indices[i][0] is not None:
            inp += 1
        if indices[i][1] is not None:
            outp += 1
        new_indices.append((inp, outp))
    return new_indices


def increment_tiers(tiers):
    incremented = []
    for i, tier in enumerate(tiers):
        incremented.append(increment_indices(tier))
    return incremented


def trim_indices(idxs):
    result = []
    for i1, i2 in idxs:
        i1 = max(i1, 0)
        i2 = max(i2, 0)
        if (i1, i2) in result:
            continue
        result.append((i1, i2))
    return result
