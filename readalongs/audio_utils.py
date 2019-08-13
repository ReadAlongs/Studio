from pydub import AudioSegment
from typing import Dict, List

from readalongs.log import LOGGER


def mute_section(audio: AudioSegment, start: int, end: int) -> AudioSegment:
    ''' Given an AudioSegment, reduce the gain between a given interval by 120db.
        Effectively, make it silent.
    '''
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
    ''' Read in AudioSegment from file
    '''
    try:
        return AudioSegment.from_file(path)
    except Exception as e:
        # need repr(e) here instead of e since these exceptions don't all have messages
        # this except clause catches empty audio files and other problems with them.
        raise RuntimeError("Error reading audio file %s: %s" %
                           (path, repr(e)))
