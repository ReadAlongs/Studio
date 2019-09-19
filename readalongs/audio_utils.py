#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#######################################################################
#
# audio_utils.py
#
#   Various utility functions for manipulating audio
#
#######################################################################

from pydub import AudioSegment

from readalongs.log import LOGGER

def mute_section(audio: AudioSegment, start: int, end: int) -> AudioSegment:
    """ Given an AudioSegment, reduce the gain between a given interval by 120db.
        Effectively, make it silent.
    
    Parameters
    ----------
    audio : AudioSegment
        audio segment to mute
    start : int
        start timestamp of audio (ms)
    end : int
        end timestamp of audio (ms)
    
    Returns
    -------
    AudioSegment
        A muted audio segment
    """
    try:
        return audio[:start] + audio[start:end].apply_gain(-120) + audio[end:]
    except IndexError:
        LOGGER.error(f"Tried to mute audio between {start} and {end}, but audio is only {len(audio)}ms long. \
                     Returning unmuted audio instead.")
        return audio

def write_audio_to_file(audio: AudioSegment, path: str) -> None:
    ''' Write AudioSegment to file
        TODO: Add params/file type kwargs
        TODO: Add exception handling
    '''
    audio.export(path)

def read_audio_from_file(path: str) -> AudioSegment:
    """ Read in AudioSegment from file

    Parameters
    ----------
    str
        Path to audiofile
    
    Returns
    -------
    AudioSegment
        An AudioSegment object of the audiofile
    
    Raises
    ------
    RuntimeError
        catches empty audio files and other problems with them.
    """
    try:
        return AudioSegment.from_file(path)
    except Exception as e:
        # need repr(e) here instead of e since these exceptions don't all have messages
        raise RuntimeError("Error reading audio file %s: %s" %
                           (path, repr(e)))
