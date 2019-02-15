#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals, division
from io import open
import argparse, json, itertools, logging

def create_inventory_from_mapping(mapping, in_or_out):
   if in_or_out not in ["in", "out"]:
      logging.error("Parameter in_or_out must be 'in' or 'out'")
      return {}
   inventory = [ x[in_or_out] for x in mapping["map"] ]
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