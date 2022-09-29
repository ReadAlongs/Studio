"""Functions to concatenate multiple readalongs together"""

from copy import deepcopy
from typing import List, Tuple

from lxml import etree

from readalongs.text.util import get_attrib_recursive, get_lang_attrib


def add_prefix_to_all_ids(prefix: str, tree: etree.ElementTree) -> None:
    """Add prefix in front of each id attributed in and under tree.

    Modifies tree in place.
    """
    if "id" in tree.attrib:
        tree.attrib["id"] = prefix + tree.attrib["id"]
    for child in tree:
        add_prefix_to_all_ids(prefix, child)


def concat_ras(inputs: List[dict]) -> Tuple[etree.ElementTree, List[dict], float]:
    """Accept a list of readalongs and return a merged readalong

    Args:
        ras (List[dict]) is a non-empty list of dicts with these keys:
            - "xml" (etree.ElementTree): the parse XML for the readalong
            - "words" (List[dict]): same as make_smil's words arg
            - "audio_duration" (float): audio duration in seconds

    Returns:
        A tuple of "xml", "words" and "audio_duration" values representing a
        readalong that is the concation of the input readalongs.
    """
    if not inputs:
        raise ValueError("empty input list for concat_ras")

    result_xml = deepcopy(inputs[0]["xml"])
    body = result_xml.find(".//body")
    body_lang = get_lang_attrib(body)
    body_fb_lang = get_attrib_recursive(body, "fallback-langs")
    # if body_lang:
    #    body.attrib["lang"] = body_lang
    # if body_fb_lang:
    #    body.attrib["fallback-langs"] = body_fb_lang
    for page in body:
        add_prefix_to_all_ids("r0", page)

    for i, xml in enumerate(ra["xml"] for ra in inputs[1:]):
        xml_copy = deepcopy(xml)
        for page in xml_copy.xpath(".//div[@type='page']"):
            add_prefix_to_all_ids(f"r{i+1}", page)
            page_lang = get_lang_attrib(page)
            if page_lang and page_lang != body_lang:
                page.attrib["lang"] = page_lang
            page_fb_lang = get_attrib_recursive(page, "fallback-langs")
            if page_fb_lang and page_fb_lang != body_fb_lang:
                page.attrib["fallback-langs"] = page_fb_lang
            body.append(page)

    result_words = []
    total_duration = 0.0
    for i, ra in enumerate(inputs):
        # deepcopy, add prefix to ids and extend into cat_words
        words = ra["words"]
        duration = ra["audio_duration"]
        prefix = f"r{i}"
        for word in words:
            result_words.append(
                {
                    "id": prefix + word["id"],
                    "start": word["start"] + total_duration,
                    "end": word["end"] + total_duration,
                }
            )
        total_duration += duration

    return (result_xml, result_words, total_duration)
