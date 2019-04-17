#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#################################################################
#
# create_inv_from_map.py
#
# A convenience module for when you need an inventory JSON
# but only have a mapping one (as is usually the case so far).
#
# This is called by create_ipa_mapping.py when it needs an
# intermediate mapping between a grapheme2ipa mapping
# and an ipa2arpabet mapping, for example.  It needs two inventories,
# and so uses this to extract the output vocabulary of the first
# and the input vocabulary of the second.
#
# This is implemented as its own module so that you can also
# call it yourself on the command line, if you
# need that actual JSON file for something.
#
###################################################################

from __future__ import print_function, unicode_literals, division
from io import open
import argparse, json, itertools, logging
from unicodedata import normalize

def create_inventory_from_mapping(mapping, in_or_out):
   if in_or_out not in ["in", "out"]:
      logging.error("Parameter in_or_out must be 'in' or 'out'")
      return {}
   inventory = [ x[in_or_out] for x in mapping["map"] ]
   print("before: %s" % inventory)
   inventory = [ normalize("NFD", x) for x in inventory ]
   print("after: %s" % inventory)
   metadata = mapping["in_metadata"] if in_or_out == 'in' else mapping["out_metadata"]
   return {
      "type": "inventory",
      "metadata": metadata,
      "inventory": inventory
   }

def go(mapping_filename, in_or_out, output_filename):
   with open(mapping_filename, "r", encoding="utf-8") as fin:
      mapping = json.load(fin)
   inventory = create_inventory_from_mapping(mapping, in_or_out)
   with open(output_filename, "w", encoding="utf-8") as fout:
      fout.write(json.dumps(inventory, ensure_ascii=False, indent=4))

if __name__ == '__main__':
   parser = argparse.ArgumentParser(description='Create an inventory file from a mapping file')
   parser.add_argument('mapping', type=str, help='Mapping filename')
   parser.add_argument('in_or_out', type=str, help='Input ("in") or output ("out") inventory?')
   parser.add_argument('output', type=str, help='Output inventory filename')
   args = parser.parse_args()
   go(args.mapping, args.in_or_out, args.output)
