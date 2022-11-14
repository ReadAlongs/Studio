#!/usr/bin/env python
# -*- coding: utf-8 -*-

###################################################
#
# waveform2svg.py
#
# Make an SVG of a waveform, using roughly the same
# procedure as Audacity uses: chop up the samples into
# n buckets, plot only the maximum and minimum values.
#
###################################################

from __future__ import absolute_import, division, print_function, unicode_literals

import argparse
from math import ceil, floor

import chevron
import numpy as np

from readalongs.waveform2svg.audio_util import load_wav_or_smil, save_txt, smooth

SVG_TEMPLATE = """<svg id='wave' preserveAspectRatio='none' viewBox="0 0 {{width}} {{height}}" xmlns="http://www.w3.org/2000/svg" height="{{height}}" width="{{width}}">
  <defs>
      <linearGradient id="Gradient" x1="0" x2="1" y1="0" y2="0">
        <stop id='progress-base' offset="0%"/>
        <stop id='progress-fill' class='' offset="0%"/>
        <stop id='progress-trail' offset='0%' stop-color='transparent'/>
      </linearGradient>
  </defs>
    <polygon id="polygon" stroked-width=".65" stroke="black" fill="url(#Gradient)" points="{{#points}}{{x}},{{y}} {{/points}}"></polygon>
</svg>
"""

SAMPLE_RATE = 16000


def get_max_and_min(data, nbuckets):
    data /= np.abs(data).max(axis=0)  # normalize
    num_samples = data.shape[0]
    samples_per_bucket = int(ceil(num_samples / nbuckets))
    max_amps, min_amps = [], []
    for i in range(0, num_samples, samples_per_bucket):
        max_amps.append(data[i : i + 256].max())
        min_amps.append(data[i : i + 256].min())
    max_amps = list(smooth(max_amps, window_size=int(floor(nbuckets / 100))))
    min_amps = list(smooth(min_amps, window_size=int(floor(nbuckets / 100))))
    return max_amps, min_amps


def render_svg(
    max_amps,
    min_amps,
    num_buckets,
    include_negative=True,
    width=512,
    height=100,
    zero_height=5,
):
    data = {"height": height, "width": width, "points": []}
    data["points"].append({"x": 0.0, "y": height / 2})
    data["points"].append({"x": 0.0, "y": (height - zero_height) / 2})
    for i, max_amp in enumerate(max_amps):
        y = (1.0 - max_amp) * ((height - zero_height) / 2)
        y = "%.2f" % y
        x = i / num_buckets * width + 0.5
        data["points"].append({"x": x, "y": y})
    data["points"].append({"x": float(width), "y": (height - zero_height) / 2})
    data["points"].append({"x": float(width), "y": height / 2})
    if include_negative:
        data["points"].append({"x": float(width), "y": (height + zero_height) / 2})
        min_amps.reverse()
        for i, min_amp in enumerate(min_amps):
            y = (1.0 - min_amp) * ((height + zero_height) / 2)
            y = "%.2f" % y
            x = width - (i / num_buckets * width + 0.5)
            data["points"].append({"x": x, "y": y})
        data["points"].append({"x": 0.0, "y": (height + zero_height) / 2})
    return chevron.render(SVG_TEMPLATE, data)


def make_waveform_svg(
    input_path, num_buckets=512, include_neg=True, width=512, height=100, zero_height=5
):
    waveform = load_wav_or_smil(input_path)
    max_amps, min_amps = get_max_and_min(waveform, num_buckets)
    return render_svg(
        max_amps, min_amps, num_buckets, include_neg, width, height, zero_height
    )


def main(
    input_path,
    output_path,
    num_buckets=512,
    include_neg=True,
    width=512,
    height=100,
    zero_height=5,
):
    svg = make_waveform_svg(
        input_path, num_buckets, include_neg, width, height, zero_height
    )
    save_txt(output_path, svg)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert a WAV file to a SVG file of its waveform"
    )
    parser.add_argument("input", type=str, help="Input WAV file")
    parser.add_argument("output", type=str, help="Output SVG file")
    parser.add_argument(
        "--nbuckets",
        type=int,
        default=512,
        help="Number of sample buckets (default: 256)",
    )
    parser.add_argument(
        "--include_neg",
        type=bool,
        default=True,
        help="Include negative values? (default: True",
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
        args.include_neg,
        args.width,
        args.height,
        args.zero_height,
    )
