""" audio_utils.py: Various utility functions for manipulating audio

Audio segments and files are manipulated using pydub.AudioSegment, which indexes them
in millisecond slices and lets us manipulate them as if they were simple lists.
"""

import logging
from typing import Union

from pydub import AudioSegment

from readalongs.log import LOGGER

# quiet pydub's logging
logging.getLogger("pydub.converter").setLevel(logging.WARNING)


def join_section(audio: AudioSegment, audio_to_insert: AudioSegment, start: int):
    """Given two AudioSegments, insert the second into the first at start (ms)"""
    try:
        return audio[:start] + audio_to_insert + audio[start:]
    except IndexError:
        LOGGER.error(
            f"Tried to insert audio at {start}, but audio is only {len(audio)}ms long. "
            "Returning unchanged audio instead."
        )
        return audio


def remove_section(audio: AudioSegment, start: int, end: int) -> AudioSegment:
    """Given an AudioSement, remove the section between start (ms) and end (ms)"""
    try:
        return audio[:start] + audio[end:]
    except IndexError:
        LOGGER.error(
            f"Tried to remove audio between {start} and {end}, but audio is only "
            f"{len(audio)}ms long. Returning unchanged audio instead."
        )
        return audio


def mute_section(audio: AudioSegment, start: int, end: int) -> AudioSegment:
    """Given an AudioSegment, reduce the gain between a given interval by 120db.
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
    """Given an AudioSegment, extract and keep only the [start, end) interval

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
            f"Tried to extract audio between {start} and {end}, but audio is only "
            f"{len(audio)}ms long. Returning whole audio instead."
        )
        return audio


def write_audio_to_file(audio: AudioSegment, path: str) -> None:
    """Write AudioSegment to file

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
    """Read in AudioSegment from file

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
        raise RuntimeError(
            "Error reading audio file %s: %s. Please provide a valid audio file and "
            "make sure ffmpeg is installed." % (path, repr(e))
        ) from e
