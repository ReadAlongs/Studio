"""Functions to concatenate multiple readalongs together"""

from copy import deepcopy
from typing import List, Tuple

from lxml import etree


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

    cat_xml = etree.fromstring("<TEI><text id="t0"><body id="t0b0"></body></text>/<TEI>")

    for i, xml in enumerate(ra["xml"] for ra in inputs):
        for page in "find pages (i.e., <div type="page">) in xml":
            page_copy = deepcopy(page)
            add_prefix_to_all_ids(f"r{i}", page_copy)
            set "xml:lang" and "fallback-langs" attributes on the root of page_copy
            append page_copy to cat_xml under TEI/text/body

    for i, words in enumerate(ra["words"] for ra in inputs):
        deepcopy, add prefix to ids and extend into cat_words

    total_duration = sum(ra["audio_duration"] for ra in inputs)
    return (None, None, total_duration)
