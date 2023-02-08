##################################################
#
# make_dict.py
#
# This module takes a text file, marked up with
# units (e.g. w for word, m for morpheme) and ids
# and converted to IPA, and produces a
# .dict file for processing by PocketSphinx.
#
##################################################

from typing import List, Tuple

import chevron

from readalongs.log import LOGGER

DICT_TEMPLATE = """{{#items}}
{{id}}\t{{pronunciation}}
{{/items}}
"""


def generate_dict_entries(word_elements, input_filename, unit):
    nwords = 0
    for e in word_elements:
        if "id" not in e.attrib:
            LOGGER.error(
                "%s-type element without id in file %s" % (unit, input_filename)
            )
        text = e.attrib.get("ARPABET", "").strip()
        if not text:
            continue
        nwords += 1
        yield e.attrib["id"], text
    if nwords == 0:
        raise RuntimeError("No words in dictionary!")


def make_dict_list(
    word_elements, input_filename="'in-memory'", unit="m"
) -> List[Tuple[str, str]]:
    return list(generate_dict_entries(word_elements, input_filename, unit))


def make_dict(word_elements, input_filename="'in-memory'", unit="m"):
    data = {
        "items": [
            {"id": word_id, "pronunciation": text}
            for word_id, text in generate_dict_entries(
                word_elements, input_filename, unit
            )
        ]
    }
    return chevron.render(DICT_TEMPLATE, data)
