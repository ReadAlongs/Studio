#!/usr/bin/env python
# -*- coding: utf-8 -*-

###################################################
#
# pitch2svg.py
#
# Make an SVG of a pitch trace.
#
# Based loosely off code from Martijn Millecamp
# (martijn.millecamp@student.kuleuven.be) and
# Miroslav Masat (miro.masat@gmail.com):
#  https://github.com/miromasat/pitch-detection-librosa-python
#
###################################################

from __future__ import absolute_import, division, print_function, unicode_literals

import os
from io import open

import librosa  # type: ignore
import numpy as np

from readalongs.text.util import load_xml, xpath_default

SAMPLE_RATE = 16000


def smooth(x, window_size=5):
    """Smooth the waveform to look... well, smooth"""
    if window_size < 3:
        return x
    s = np.r_[2 * x[0] - x[window_size - 1 :: -1], x, 2 * x[-1] - x[-1:-window_size:-1]]
    w = np.hanning(window_size)
    y = np.convolve(w / w.sum(), s, mode="same")
    return y[window_size : -window_size + 1]


def load_smil(input_path):
    """Get the bucketed max and min value from a sequence of WAV files as
    expressed in a SMIL document"""
    xml = load_xml(input_path)
    dirname = os.path.dirname(input_path)
    data = None
    most_recent_audio_src = None
    for audio_node in xpath_default(xml, ".//i:audio"):
        audio_src = audio_node.attrib["src"]
        if audio_src == most_recent_audio_src:
            continue
        most_recent_audio_src = audio_src
        audio_path = os.path.join(dirname, audio_src)
        waveform = load_wav(audio_path)
        data = np.hstack((data, waveform)) if data is not None else waveform
    return data


def load_wav(input_path):
    waveform, _ = librosa.load(input_path, sr=SAMPLE_RATE)
    return waveform


def load_wav_or_smil(input_path):
    if os.path.splitext(input_path)[1].lower() == ".smil":
        waveform = load_smil(input_path)
    else:
        waveform = load_wav(input_path)
    return waveform


def ensure_dirs(path):
    dirname = os.path.dirname(path)
    if dirname and not os.path.exists(dirname):
        os.makedirs(dirname)


def save_txt(output_path, txt):
    ensure_dirs(output_path)
    with open(output_path, "w", encoding="utf-8") as fout:
        fout.write(txt)
