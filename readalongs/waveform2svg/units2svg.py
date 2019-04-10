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
import pystache
from lxml import etree
import librosa
from collections import OrderedDict

def ensure_dirs(path):
    dirname = os.path.dirname(path)
    if dirname and not os.path.exists(dirname):
        os.makedirs(dirname)

FMIN = 80
FMAX = 1000
THRESHOLD = 0.75

SVG_TEMPLATE = '''<svg id='units' preserveAspectRatio='none' viewBox="0 0 {{total_width}} {{total_height}}" xmlns="http://www.w3.org/2000/svg" height="{{height}}" width="{{width}}">
  {{#rects}}
    <rect x="{{x}}" y="0" rx="{{radius}}" ry="{{radius}}" width="{{width}}" height="{{total_height}}"></rect>
  {{/rects}}
</svg>
'''

def render_svg(data, width=512, height=100):
    result = { "total_width": width,
               "total_height": height,
               "radius": height / 25,
               "rects": [] }
    total_duration = data["duration"]
    for src, audio in data["audio_files"].items():
        for unit in audio["sub_units"]:
            x = (unit["start"] / total_duration) * width - 0.5
            x = "%.2f" % x
            w = max((unit["duration"] / total_duration) * width - 1.0, 1.0)
            w = "%.2f" % w
            result["rects"].append({"x":x, "width":w})
    return pystache.render(SVG_TEMPLATE, result)

def load_xml(input_path):
    with open(input_path, "r", encoding="utf-8") as fin:
        return etree.fromstring(fin.read())

def xpath_default(xml, query, default_namespace_prefix="i"):
    nsmap = dict(((x,y) if x else (default_namespace_prefix,y))
                        for (x,y) in xml.nsmap.items())
    for e in xml.xpath(query, namespaces=nsmap):
        yield e

def parse_smil(input_path):
    ''' Figure out the overall start and end of every unit, even if the whole
        sequence plays out over multiple audio files '''
    xml = load_xml(input_path)
    data = { "audio_files": OrderedDict() }
    dirname = os.path.dirname(input_path)
    current_time = 0.0
    for audio_node in xpath_default(xml, ".//i:audio"):
        src = audio_node.attrib["src"]
        if src not in data["audio_files"]:
            # get some basic info on the audio
            audio_path = os.path.join(dirname, src)
            y, sr = librosa.load(audio_path)
            duration = y.shape[0] / sr
            data["audio_files"][src] = ({
                "src": src,
                "start": current_time,
                "duration": duration,
                "end": current_time + duration,
                "sub_units": []
            })
            current_time += duration
        current_audio_file = data["audio_files"][src]
        start = float(audio_node.attrib["clipBegin"]) + current_audio_file["start"] \
            if "clipBegin" in audio_node.attrib else current_audio_file["start"]
        end = float(audio_node.attrib["clipEnd"]) + current_audio_file["start"] \
            if "clipEnd" in audio_node.attrib else current_audio_file["end"]
        current_audio_file["sub_units"].append({
            "start": start,
            "duration": end - start
        })
    if not data["audio_files"]:
        data["duration"] = 0.0
    else:
        last_audio = next(reversed(data["audio_files"]))
        data["duration"] = data["audio_files"][last_audio]["end"]
    return data

def make_svg(input_path, width=512, height=100):
    data = parse_smil(input_path)
    return render_svg(data, width, height)

def main(input_path, output_path):
    svg = make_svg(input_path)
    ensure_dirs(input_path)
    with open(output_path, "w", encoding="utf-8") as fout:
        fout.write(svg)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Convert a SMIL file to a SVG file indicating sub-unit durations')
    parser.add_argument('input', type=str, help='Input SMIL file')
    parser.add_argument('output', type=str, help='Output SVG file')
    args = parser.parse_args()
    main(args.input, args.output)
