""" dna_utils.py: Utilities to manipulate and use lists of do-no-align segments

Do-not-align segment lists are in the format imported from our config.json file:
    List[{"begin": begin-time-in-ms (int), "end": end-time-in-ms (int)}]
The items in the list represent time-ranges in the audio that should not be aligned to
any units in the text.
"""

import copy
from typing import List, Tuple


def sort_and_join_dna_segments(do_not_align_segments: List[dict]) -> List[dict]:
    """Give a list of DNA segments, sort them and join any overlapping ones"""
    results: List[dict] = []
    for seg in sorted(do_not_align_segments, key=lambda x: x["begin"]):
        if results and results[-1]["end"] >= seg["begin"]:
            results[-1]["end"] = max(results[-1]["end"], seg["end"])
        else:
            results.append(copy.deepcopy(seg))
    return results


def correct_adjustments(
    start: int, end: int, do_not_align_segments: List[dict]
) -> Tuple[int, int]:
    """Given the start and end of a segment (in ms) and a list of do-not-align segments,
    If one of the do-not-align segments occurs inside one of the start-end range,
    align the start or end with the do-not-align segment, whichever requires minimal change
    """
    for seg in do_not_align_segments:
        if start < seg["begin"] and end > seg["end"]:
            if seg["begin"] - start > end - seg["end"]:
                return start, seg["begin"]
            else:
                return seg["end"], end
    return start, end


def calculate_adjustment(timestamp: int, do_not_align_segments: List[dict]) -> int:
    """Given a time (in ms) and a list of do-not-align segments,
        return the sum (ms) of the lengths of the do-not-align segments
        that start before the timestamp

    Preconditions:
        do_not_align_segments are sorted in ascending order of their "begin" and do not overlap
    """
    results = 0
    prev_end = -1
    for seg in do_not_align_segments:
        assert prev_end < seg["begin"]
        prev_end = seg["end"]
        if seg["begin"] <= timestamp:
            delta = seg["end"] - seg["begin"]
            results += delta
            timestamp += delta
    return results


def segment_intersection(segments1: List[dict], segments2: List[dict]) -> List[dict]:
    """Return the intersection of two lists of segments

    Precondition:
        segments1 and segments2 contain sorted, non-overlapping ranges
    """
    i1 = 0  # current index in segments1
    i2 = 0  # current index in segments2
    len1 = len(segments1)
    len2 = len(segments2)

    results = []
    while i1 < len1 and i2 < len2:
        if segments1[i1]["end"] < segments2[i2]["begin"]:
            i1 += 1
        elif segments1[i1]["begin"] > segments2[i2]["end"]:
            i2 += 1
        else:
            results.append(
                {
                    "begin": max(segments1[i1]["begin"], segments2[i2]["begin"]),
                    "end": min(segments1[i1]["end"], segments2[i2]["end"]),
                }
            )
            if segments1[i1]["end"] < segments2[i2]["end"]:
                i1 += 1
            else:
                i2 += 1
    return results


def dna_union(
    start, end, audio_length: int, do_not_align_segments: List[dict]
) -> List[dict]:
    """Return the DNA list to include [start,end] and exclude do_not_align_segments

    Given time range [start, end] to keep, and a list of do-not-align-segments to
    exclude, calculate the equivalent do-not-align-segment list to keeping only
    what's in [start, end], and removing both what's outside [start, end] and
    do_not_align_segments.

    Args:
        start (Optional[int]): the start time of the range to keep, None meaning 0,
            i.e., the beginning of the audio file
        end (Optional[int]): the end of the range to keep, None meaning the end of the audio file
        audio_length (int): the full length of the audio file
        do_not_align_segments (List[dict]): the original list of DNA segments

    Returns:
        List[dict]:
            the union of DNA lists [[0, start], [end, audio_length]] and do_not_align_segments
    """
    current_list = do_not_align_segments
    if start:
        new_list = []
        new_list.append({"begin": 0, "end": start})
        for seg in current_list:
            if seg["end"] <= start:
                pass  # dna segments that end before start are subsumed by [0,start)
            elif seg["begin"] <= start:
                start = seg["end"]
                new_list[0]["end"] = start
            else:
                new_list.append(seg)
        current_list = new_list
    if end:
        new_list = []
        for seg in current_list:
            if seg["begin"] >= end:
                pass  # dna segments after end are subsumed by [end, audio_length)
            elif seg["end"] >= end:
                end = seg["begin"]
            else:
                new_list.append(seg)
        new_list.append({"begin": end, "end": audio_length})
        current_list = new_list
    return current_list
