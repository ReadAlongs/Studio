#!/usr/bin/env python3
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

from __future__ import print_function, unicode_literals, division, absolute_import
from io import open
import logging
import argparse
import os
import numpy as np
from math import floor
import pystache
import librosa
from audio_util import *

FMIN = 80
FMAX = 1000
THRESHOLD = 0.75

SVG_TEMPLATE = '''<svg id='pitch' preserveAspectRatio='none' viewBox="0 0 512 100" xmlns="http://www.w3.org/2000/svg" height="{{height}}" width="{{width}}">
    <polygon points="{{#points}}{{x}},{{y}} {{/points}}"></polygon>
</svg>
'''

def render_svg(pitches, width=512, height=100):
    data = { "height": height, "width": width, "points": [] }
    data["points"].append({"x":0.0, "y": float(height)})
    for i, pitch in enumerate(pitches):
        x = i + 0.5
        y = (1.0 - pitch) * height
        y = "%.2f" % y
        data["points"].append({"x": x, "y": y})
    data["points"].append({"x":float(width), "y": float(height)})
    return pystache.render(SVG_TEMPLATE, data)

def extract_pitches(waveform, nbuckets=512):
    nsamples = waveform.shape[0]
    hop_length = int(floor(nsamples / nbuckets))
    pitches, magnitudes = librosa.core.piptrack(y=waveform, sr=SAMPLE_RATE,
        fmin=FMIN, fmax=FMAX, hop_length=hop_length, threshold=THRESHOLD)
    pitches = pitches[:,:nbuckets]
    pitches = pitches.max(axis=0)
    pitches /= pitches.max()
    return smooth(pitches, window_size=int(floor(nbuckets/40)))

def make_svg(input_path, nbuckets=512, height=100, width=512):
    waveform = load_wav_or_smil(input_path)
    pitches = extract_pitches(waveform, nbuckets)
    return render_svg(pitches, width, height)

def main(input_path, output_path, nbuckets=512):
    svg = make_svg(input_path, nbuckets)
    ensure_dirs(input_path)
    with open(output_path, "w", encoding="utf-8") as fout:
        fout.write(svg)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Convert a WAV or SMIL file to a SVG file of its waveform')
    parser.add_argument('input', type=str, help='Input WAV or SMIL file')
    parser.add_argument('output', type=str, help='Output SVG file')
    parser.add_argument('--nbuckets', type=int, default=512,
                        help='Number of sample buckets (default: 256)')
    args = parser.parse_args()
    main(args.input, args.output, args.nbuckets)
