"""Functions to concatenate multiple readalongs together"""

from lxml import etree
from typing import List, Tuple


def concat_ras(inputs: List[dict]) -> Tuple[etree.ElementTree, List[dict], float]:
    """Accept a list of readalongs and return a merged readalong

    Args:
        ras (List[dict]) has dict with these keys:
            - "xml" (etree.ElementTree): the parse XML for the readalong
            - "words" (List[dict]): same as make_smil's words arg
            - "audio_duration" (float): audio duration in seconds

    Returns:
        A tuple of "xml", "words" and "audio_duration" values representing a
        readalong that is the concation of the input readalongs.
    """

    pass
