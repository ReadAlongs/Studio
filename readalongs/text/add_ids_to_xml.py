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
# already have ids, or if the markup uses different tags than a RAS document.
#
###################################################

from collections import defaultdict
from copy import deepcopy

from lxml import etree

from readalongs.text.util import is_do_not_align

TAG_TO_ID = {
    "text": "t",
    "body": "b",
    "div": "d",
    "page": "pp",
    "p": "p",
    "u": "u",
    "s": "s",
    "w": "w",
    "m": "m",
}

TAGS_TO_IGNORE = ["head", "teiHeader", "script"]


def add_ids_aux(element: etree, ids: defaultdict, parent_id: str = "") -> defaultdict:
    """Add ids to xml element

    Args:
        element (etree): Element to add ids to
        ids (defaultdict): counters for ids assigned so far by tag type
        parent_id (str): Optional; id of parent element, by default ''

    Returns:
        defaultdict: ids, with new counts added by tag type
    """
    if element.tag is etree.Comment:
        return ids
    tag = etree.QName(element.tag).localname
    if tag in TAGS_TO_IGNORE:
        return ids
    if is_do_not_align(element):
        if tag == "w":
            raise RuntimeError(
                'Found <w> element with do-not-align="true" attribute. '
                "This is not allowed, please verify you XML input."
            )
        if element.xpath(".//w"):
            raise RuntimeError(
                'Found <w> nested inside a do-not-align="true" element. '
                "This is not allowed, please verify you XML input."
            )
        return ids
    if "id" not in element.attrib:
        if tag in TAG_TO_ID:
            id = TAG_TO_ID[tag]
        elif tag == "seg" and "type" in element.attrib:
            if element.attrib["type"] == "syll":
                id = "y"
            elif element.attrib["type"] in [
                "morph",
                "morpheme",
                "base",
                "root",
                "prefix",
                "suffix",
            ]:
                id = "m"
        else:
            id = tag
        if id not in ids:
            ids[id] = 0
        element.attrib["id"] = parent_id + id + str(ids[id])
        ids[id] += 1
    full_id = element.attrib["id"]
    # This deep copy of ids means that the ids counters are shared recursively
    # between siblings, but not between grand-children. Thus, if processing a p
    # element, the next p element will see its counter incremented, but the s
    # elements of the next p elements will start again at 0. ids always has the
    # counters of all ancestors and their siblings, by tag, but not the
    # descendents of siblings of ancestors.
    new_ids = deepcopy(ids)
    for child in element:
        new_ids = add_ids_aux(child, new_ids, full_id)
    return ids


def add_ids(xml: etree) -> etree:
    """Add ids to xml

    Args:
        xml (etree): xml to add ids to

    Returns:
        etree: xml with ids added
    """
    xml = deepcopy(xml)
    ids: defaultdict = defaultdict(lambda: 0)
    for child in xml:  # don't bother with the root element
        if child.tag is etree.Comment:
            continue
        ids = add_ids_aux(child, ids)
    return xml
