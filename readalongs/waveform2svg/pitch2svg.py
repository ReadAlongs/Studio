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

import argparse
from math import floor

import chevron
import librosa

from readalongs.waveform2svg.audio_util import (
    SAMPLE_RATE,
    load_wav_or_smil,
    save_txt,
    smooth,
)

FMIN = 80
FMAX = 1000
THRESHOLD = 0.75

SVG_TEMPLATE = """<svg id='pitch' preserveAspectRatio='none' viewBox="0 0 {{width}} {{height}}" xmlns="http://www.w3.org/2000/svg" height="{{height}}" width="{{width}}">
    <polygon points="{{#points}}{{x}},{{y}} {{/points}}"></polygon>
</svg>
"""


def render_svg(pitches, width=512, height=100, zero_height=5):
    data = {"height": height, "width": width, "points": []}
    data["points"].append({"x": 0.0, "y": float(height)})
    data["points"].append({"x": 0.0, "y": float(height - zero_height)})
    for i, pitch in enumerate(pitches):
        x = i + 0.5
        y = (1.0 - pitch) * (height - zero_height)
        y = "%.2f" % y
        data["points"].append({"x": x, "y": y})
    data["points"].append({"x": float(width), "y": float(height - zero_height)})
    data["points"].append({"x": float(width), "y": float(height)})
    return chevron.render(SVG_TEMPLATE, data)


def extract_pitches(waveform, nbuckets=512):
    nsamples = waveform.shape[0]
    hop_length = int(floor(nsamples / nbuckets))
    pitches, magnitudes = librosa.core.piptrack(
        y=waveform,
        sr=SAMPLE_RATE,
        fmin=FMIN,
        fmax=FMAX,
        hop_length=hop_length,
        threshold=THRESHOLD,
    )
    pitches = pitches[
        :, :nbuckets
    ]  # TODO: AP: I'm not sure what this is meant to be. Causing error. Maybe just :nbuckets?
    pitches = pitches.max(axis=0)
    pitches /= pitches.max()
    return smooth(pitches, window_size=int(floor(nbuckets / 40)))


def make_pitch_svg(input_path, nbuckets=512, height=100, width=512, zero_height=5):
    waveform = load_wav_or_smil(input_path)
    pitches = extract_pitches(waveform, nbuckets)
    return render_svg(pitches, width, height, zero_height)


def main(input_path, output_path, nbuckets=512, width=512, height=100, zero_height=5):
    svg = make_pitch_svg(input_path, nbuckets, width, height, zero_height)
    save_txt(output_path, svg)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert a WAV or SMIL file to a SVG file of its pitch trace"
    )
    parser.add_argument("input", type=str, help="Input WAV or SMIL file")
    parser.add_argument("output", type=str, help="Output SVG file")
    parser.add_argument(
        "--nbuckets",
        type=int,
        default=512,
        help="Number of sample buckets (default: 256)",
    )
    parser.add_argument(
        "--width", type=int, default=512, help="Width of output SVG (default: 512)"
    )
    parser.add_argument(
        "--height", type=int, default=100, help="Height of output SVG (default: 100)"
    )
    parser.add_argument(
        "--zero_height", type=int, default=5, help="Padding around zero (default: 5)"
    )
    args = parser.parse_args()
    main(
        args.input,
        args.output,
        args.nbuckets,
        args.width,
        args.height,
        args.zero_height,
    )
