#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#######################################################################
#
# audio_utils.py
#
#   Various utility functions for manipulating audio
#
#   And also utility functions for manipulating and apply do-not-align segments
#
#######################################################################

import copy
from typing import List, Tuple, Union

from pydub import AudioSegment

from readalongs.log import LOGGER


def join_section(audio: AudioSegment, audio_to_insert: AudioSegment, start: int):
    """ Given two AudioSegments, insert the second into the first at start (ms)
    """
    try:
        return audio[:start] + audio_to_insert + audio[start:]
    except IndexError:
        LOGGER.error(
            f"Tried to insert audio at {start}, but audio is only {len(audio)}ms long. \
                     Returning unchanged audio instead."
        )
        return audio


def remove_section(audio: AudioSegment, start: int, end: int) -> AudioSegment:
    """ Given an AudioSement, remove the section between start (ms) and end (ms)
    """
    try:
        return audio[:start] + audio[end:]
    except IndexError:
        LOGGER.error(
            f"Tried to remove audio between {start} and {end}, but audio is only {len(audio)}ms long. \
                     Returning unchanged audio instead."
        )
        return audio


def mute_section(audio: AudioSegment, start: int, end: int) -> AudioSegment:
    """ Given an AudioSegment, reduce the gain between a given interval by 120db.
        Effectively, make it silent.

    Args:
        audio (AudioSegment): audio segment to mute
        start (int): start timestamp of audio (ms)
        end (int): end timestamp of audio (ms)

    Returns:
        AudioSegment: A muted audio segment
    """
    try:
        return audio[:start] + audio[start:end].apply_gain(-120) + audio[end:]
    except IndexError:
        LOGGER.error(
            f"Tried to mute audio between {start} and {end}, but audio is only {len(audio)}ms long. \
                     Returning unmuted audio instead."
        )
        return audio


def extract_section(
    audio: AudioSegment, start: Union[None, int], end: Union[None, int]
) -> AudioSegment:
    """ Given an AudioSegment, extract and keep only the [start, end) interval

    Args:
        audio (AudioSegment): audio segment to extract a section from
        start (Union[None,int]): start timestamp of audio to extract (ms)
            (None means begining of audio)
        end (Union[None,int]): end timestamp of audio to extract (ms)
            (None means end of audio)

    Returns:
        AudioSegment: the extracted audio segment
    """
    # Optimization: don't copy the data if we're extracting from None to None
    if start is None and end is None:
        return audio

    try:
        return audio[start:end]
    except IndexError:
        LOGGER.error(
            f"Tried to extract audio between {start} and {end}, but audio is only {len(audio)}ms long. "
            "Returning whole audio instead."
        )
        return audio


def write_audio_to_file(audio: AudioSegment, path: str) -> None:
    """ Write AudioSegment to file

    Args:
        audio (AudioSegment): audio segment to write
        path (str): path where to write the audio file

    TODO: Add exception handling
    """
    # open path in a context manager to make sure the file handle gets closed before
    # this function exists.
    # audio.export(filename) does not close its file handle, so we can't count on that.
    with open(path, "wb") as f:
        audio.export(f)


def read_audio_from_file(path: str) -> AudioSegment:
    """ Read in AudioSegment from file

    Args:
        path (str): Path to audiofile

    Returns:
        AudioSegment: An AudioSegment object of the audiofile

    Raises:
        RuntimeError: catches empty audio files and other problems with them.
    """
    try:
        return AudioSegment.from_file(path)
    except Exception as e:
        # need repr(e) here instead of e since these exceptions don't all have messages
        raise RuntimeError("Error reading audio file %s: %s" % (path, repr(e)))


#######################################################################
#
# The following functions manipulate not actual audio files, but lists of
# do-not-align segment lists about audio files
#
#######################################################################


def sort_and_join_dna_segments(do_not_align_segments: List[dict]) -> List[dict]:
    """ Give a list of DNA segments, sort them and join any overlapping ones """
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
    """ Given the start and end of a segment (in ms) and a list of do-not-align segments,
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
    """ Given a time (in ms) and a list of do-not-align segments,
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
    """ Return the intersection of two lists of segments

    Precondition:
        segments1 and segments2 contain sorted, non-overlapping ranges
    """
    i1 = 0
    i2 = 0
    l1 = len(segments1)
    l2 = len(segments2)

    results = []
    while i1 < l1 and i2 < l2:
        if segments1[i1]["end"] <= segments2[i2]["begin"]:
            i1 += 1
        elif segments1[i1]["begin"] >= segments2[i2]["end"]:
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
    """ Given time range [start, end) to keep, and a list of do-not-align-segments, calculate
        the equivalent do-not-align-segment list to keeping only what's in
        [start, end) and removing what's outside it.
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
