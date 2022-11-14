#!/usr/bin/env python
# -*- coding: utf-8 -*-

########################################################
#
# make_all_svgs.py
#
# Take a SMIL file and render all available SVGs for it
#
########################################################

from __future__ import absolute_import, division, print_function, unicode_literals

import argparse

from audio_util import save_txt
from pitch2svg import make_pitch_svg
from units2svg import make_units_svg
from waveform2svg import make_waveform_svg


def main(
    input_path,
    output_waveform_path,
    output_half_waveform_path,
    output_pitch_path,
    output_units_path,
):
    waveform_svg = make_waveform_svg(input_path)
    save_txt(output_waveform_path, waveform_svg)
    half_waveform_svg = make_waveform_svg(input_path, include_neg=False)
    save_txt(output_half_waveform_path, half_waveform_svg)
    pitch_svg = make_pitch_svg(input_path)
    save_txt(output_pitch_path, pitch_svg)
    units_svg = make_units_svg(input_path)
    save_txt(output_units_path, units_svg)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert a SMIL file to a SVG file of its waveform, pitch, and units"
    )
    parser.add_argument("input", type=str, help="Input SMIL file")
    parser.add_argument("output_waveform", type=str, help="Output SVG file")
    parser.add_argument("output_half_waveform", type=str, help="Output SVG file")
    parser.add_argument("output_pitch", type=str, help="Output SVG file")
    parser.add_argument("output_units", type=str, help="Output SVG file")
    args = parser.parse_args()
    main(
        args.input,
        args.output_waveform,
        args.output_half_waveform,
        args.output_pitch,
        args.output_units,
    )
