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

import argparse, os
import logging
from unicodedata import normalize, category
from text_unidecode import unidecode

CATEGORIES = {
    "Cc": "other",	# Other, Control
    "Cf": "other",	# Other, Format
    "Cn": "other",	# Other, Not Assigned (no characters in the file have this property)
    "Co": "letter",	# Other, Private Use
    "Cs": "other",	# Other, Surrogate
    "LC": "letter",	# Letter, Cased
    "Ll": "letter",	# Letter, Lowercase
    "Lm": "letter",	# Letter, Modifier
    "Lo": "letter",	# Letter, Other
    "Lt": "letter",	# Letter, Titlecase
    "Lu": "letter",	# Letter, Uppercase
    "Mc": "diacritic",	# Mark, Spacing Combining
    "Me": "diacritic",	# Mark, Enclosing
    "Mn": "diacritic",	# Mark, Nonspacing
    "Nd": "number",	# Number, Decimal Digit
    "Nl": "number",	# Number, Letter
    "No": "number",	# Number, Other
    "Pc": "punctuation",	# Punctuation, Connector
    "Pd": "punctuation",	# Punctuation, Dash
    "Pe": "punctuation",	# Punctuation, Close
    "Pf": "punctuation",	# Punctuation, Final quote (may behave like Ps or Pe depending on usage)
    "Pi": "punctuation",	# Punctuation, Initial quote (may behave like Ps or Pe depending on usage)
    "Po": "punctuation",	# Punctuation, Other
    "Ps": "punctuation",	# Punctuation, Open
    "Sc": "symbol",	# Symbol, Currency
    "Sk": "symbol",	# Symbol, Modifier
    "Sm": "symbol",	# Symbol, Math
    "So": "symbol",	# Symbol, Other
    "Zl": "whitespace",	# Separator, Line
    "Zp": "whitespace",	# Separator, Paragraph
    "Zs": "whitespace",	# Separator, Space
}

def get_unicode_category(c):
    """ Maps a character to one of [ "letter", "number", "diacritic", "punctuation",
        "symbol", "whitespace", "other"] """
    cat = category(c)
    assert(cat in CATEGORIES)
    return CATEGORIES[cat]

for c in u"Yekaratónhkwa":
    cat = category(c)
    print([c,cat])
    print([unidecode(c)])
