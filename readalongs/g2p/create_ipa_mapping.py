#!/usr/bin/env python3
# -*- coding: utf-8 -*-

######################################################################
#
# create_ipa_mapping.py
#
# Given two IPA inventories in JSON (either as dedicated inventory
# files or the input/output sides of mapping files), map the first
# onto the second by use of panphon's phonetic distance calculators.
#
# The resulting mappings are used just like other mappings: to make
# converters and pipelines of converters in convert_orthography.py
#
######################################################################

from __future__ import print_function, unicode_literals
from __future__ import division, absolute_import

import argparse
import json
from readalongs.log import LOGGER
import io

import panphon.distance
from panphon.xsampa import XSampa
from tqdm import tqdm

from readalongs.g2p.create_inv_from_map import create_inventory_from_mapping

dst = panphon.distance.Distance()

#################################
#
# Preprocessing:
#
# Panphon can only match a single segment to another segment, rather
# than (say) try to combine two segments to better match the features.
# For example, you might want "kʷ" to match to "kw", but Panphon will
# only match the "kʷ" to "k" and consider the "w" to be a dropped
# character.  In order to get around this, we preprocess strings so
# that common IPA segments that you might expect map to two characters
# in another language, like affricates or rounded consonants, are
# treated as two characters rather than one.
#
#################################
xsampa_converter = XSampa()


def process_character(p, is_xsampa=False):
    if is_xsampa:
        p = xsampa_converter.convert(p)
    return p.replace("ʷ", "w").replace("ʲ", "j").replace("͡", "")


def process_characters(inv, is_xsampa=False):
    return [process_character(p, is_xsampa) for p in inv]

##################################
#
# Creating the mapping
#
#
#
###################################


def create_mapping(inv_l1, inv_l2):
    if inv_l1["type"].startswith("mapping"):
        inv_l1 = create_inventory_from_mapping(inv_l1, "out")
    if inv_l2["type"].startswith("mapping"):
        inv_l2 = create_inventory_from_mapping(inv_l2, "in")
    supported_formats = ('ipa', 'x-sampa', 'xsampa')
    if inv_l1["metadata"]["format"].lower() not in supported_formats:
        LOGGER.warning("Unsupported orthography of inventory 1: %s"
                        " (must be ipa or x-sampa)",
                        inv_l1["metadata"]["format"].lower())
    if inv_l2["metadata"]["format"].lower() not in supported_formats:
        LOGGER.warning("Unsupported orthography of inventory 2: %s"
                        " (must be ipa or x-sampa)",
                        inv_l2["metadata"]["format"].lower())
    l1_is_xsampa, l2_is_xsampa = False, False
    sampas = ("x-sampa", "xsampa")
    if inv_l1["metadata"]["format"].lower() in sampas:
        l1_is_xsampa = True
    if inv_l2["metadata"]["format"].lower() in sampas:
        l2_is_xsampa = True
    mapping = align_inventories(inv_l1["inventory"], inv_l2["inventory"],
                                l1_is_xsampa, l2_is_xsampa)
    output_mapping = {
        "type": "mapping",
        "in_metadata": inv_l1["metadata"],
        "out_metadata": inv_l2["metadata"],
        "map": mapping
    }
    return output_mapping


def find_good_match(p1, inventory_l2, l2_is_xsampa=False):
    """Find a good sequence in inventory_l2 matching p1."""
    # The proper way to do this would be with some kind of beam search
    # through a determinized/minimized FST, but in the absence of that
    # we can do a kind of heurstic greedy search.  (we don't want any
    # dependencies outside of PyPI otherwise we'd just use OpenFST)
    p1_pseq = dst.fm.ipa_segs(p1)
    p2_pseqs = [dst.fm.ipa_segs(p)
                for p in process_characters(inventory_l2, l2_is_xsampa)]
    i = 0
    good_match = []
    while i < len(p1_pseq):
        best_input = ""
        best_output = -1
        best_score = 0xdeadbeef
        for j, p2_pseq in enumerate(p2_pseqs):
            # FIXME: Should also consider the (weighted) possibility
            # of deleting input or inserting any segment (but that
            # can't be done with a greedy search)
            if len(p2_pseq) == 0:
                LOGGER.warning('No panphon mapping for %s - skipping',
                                inventory_l2[j])
                continue
            e = min(i + len(p2_pseq), len(p1_pseq))
            input_seg = p1_pseq[i:e]
            score = dst.weighted_feature_edit_distance(''.join(input_seg),
                                                       ''.join(p2_pseq))
            # Be very greedy and take the longest match
            if (score < best_score
                or score == best_score
                and len(input_seg) > len(best_input)):
                best_input = input_seg
                best_output = j
                best_score = score
        LOGGER.debug('Best match at position %d: %s => %s',
                      i, best_input, inventory_l2[best_output])
        good_match.append(inventory_l2[best_output])
        i += len(best_input)  # greedy!
    return ''.join(good_match)


def align_inventories(inventory_l1, inventory_l2,
                      l1_is_xsampa=False, l2_is_xsampa=False):
    mapping = []
    inventory_l1 = sorted(set(inventory_l1))
    inventory_l2 = list(set(inventory_l2))
    for i1, p1 in enumerate(tqdm(process_characters(inventory_l1,
                                                    l1_is_xsampa))):
        # we enumerate the strings because we want to save the original string
        # (e.g., 'kʷ') to the mapping, not the processed one (e.g. 'kw')
        good_match = find_good_match(p1, inventory_l2, l2_is_xsampa)
        mapping.append({"in": inventory_l1[i1], "out": good_match})
    return mapping


def go(inv_l1_filename, inv_l2_filename, intermediate_mapping_filename):
    with io.open(inv_l1_filename, "r", encoding="utf-8") as fin_l1:
        inv_l1 = json.load(fin_l1)
    with io.open(inv_l2_filename, "r", encoding="utf-8") as fin_l2:
        inv_l2 = json.load(fin_l2)
    intermediate_mapping = create_mapping(inv_l1, inv_l2)
    with io.open(intermediate_mapping_filename, "w", encoding="utf-8") as fout:
        fout.write(json.dumps(intermediate_mapping,
                              ensure_ascii=False, indent=4))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Create a mapping between IPA symbols of two languages')
    parser.add_argument('mapping_l1', type=str, help='First mapping filename')
    parser.add_argument('mapping_l2', type=str, help='Second mapping filename')
    parser.add_argument('output', type=str, help='Output mapping filename')
    args = parser.parse_args()
    go(args.mapping_l1, args.mapping_l2, args.output)
