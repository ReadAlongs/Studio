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

from __future__ import print_function, unicode_literals, division
from io import open
import argparse, json, itertools, logging
from create_inv_from_map import create_inventory_from_mapping
import panphon.distance

dst = panphon.distance.Distance()

#################################
#
# Preprocessing:
#
# Panphon can only match a single segment to another segment,
# rather than (say) try to combine two segments to better match the features.
# For example, you might want "kʷ" to match to "kw", but Panphon will only
# match the "kʷ" to "k" and consider the "w" to be a dropped character.  In
# order to get around this, we preprocess strings so that common IPA segments
# that you might expect map to two characters in another language, like affricates
# or rounded consonants, are treated as two characters rather than one.
#
#################################

def split_character(p):
    return p.replace("ʷ","w").replace("ʲ","j").replace("͡","")

def split_characters(inv):
    return [ split_character(p) for p in inv ]

##################################
#
# Creating the mapping
#
#
#
###################################


def create_mapping(inv_l1, inv_l2):
    if inv_l1["type"] == "mapping":
        inv_l1 = create_inventory_from_mapping(inv_l1, "out")
    if inv_l2["type"] == "mapping":
        inv_l2 = create_inventory_from_mapping(inv_l2, "in")
    if inv_l1["metadata"]["orth"] != "ipa":
        logging.warning("Orthography of inventory 1 is not 'ipa'.")
    if inv_l2["metadata"]["orth"] != "ipa":
        logging.warning("Orthography of inventory 2 is not 'ipa'.")
    mapping = align_inventories(inv_l1["inventory"], inv_l2["inventory"])
    output_mapping = {
        "type": "mapping",
        "in_metadata": inv_l1["metadata"],
        "out_metadata": inv_l2["metadata"],
        "map": mapping
    }
    return output_mapping

def align_inventories(inventory_l1, inventory_l2):
    mapping = []
    inventory_l2_expanded = itertools.product(inventory_l2, inventory_l2)
    inventory_l2_expanded = list(x + y for x,y in inventory_l2_expanded)
    inventory_l2_expanded = inventory_l2 + inventory_l2_expanded
    for i1, p1 in enumerate(split_characters(inventory_l1)):
        # we enumerate the strings because we want to save the original string
        # (e.g., 'kʷ') to the mapping, not the processed one (e.g. 'kw')
        best_match = None
        best_match_distance = 1000000000
        for i2, p2 in enumerate(split_characters(inventory_l2_expanded)):
            distance = dst.weighted_feature_edit_distance(p1, p2)
            if distance < best_match_distance:
                best_match = inventory_l2_expanded[i2]
                best_match_distance = distance
        mapping.append({"in": inventory_l1[i1], "out": best_match})
    return mapping


def go(inv_l1_filename, inv_l2_filename, intermediate_mapping_filename):
    with open(inv_l1_filename, "r", encoding="utf-8") as fin_l1:
        inv_l1 = json.load(fin_l1)
    with open(inv_l2_filename, "r", encoding="utf-8") as fin_l2:
        inv_l2 = json.load(fin_l2)
    intermediate_mapping = create_mapping(inv_l1, inv_l2)
    with open(intermediate_mapping_filename, "w", encoding="utf-8") as fout:
        fout.write(json.dumps(intermediate_mapping, ensure_ascii=False, indent=4))


if __name__ == '__main__':
   parser = argparse.ArgumentParser(description='Create a mapping between IPA symbols of two languages')
   parser.add_argument('mapping_l1', type=str, help='First mapping filename')
   parser.add_argument('mapping_l2', type=str, help='Second mapping filename')
   parser.add_argument('output', type=str, help='Output mapping filename')
   args = parser.parse_args()
   go(args.mapping_l1, args.mapping_l2, args.output)
