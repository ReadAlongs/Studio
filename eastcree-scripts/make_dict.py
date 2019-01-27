#!/usr/bin/env python3

"""Make a dictionary of words using worldbet phones from table and
phone mapping."""

from collections import defaultdict
import fileinput
import argparse

def load_table(path):
    """Load syllabic to phone mapping from path."""
    table = {}
    with open(path) as infile:
        for line in infile:
            line = line.strip()
            if len(line) == 0 or line[0] == '#':
                pass
            else:
                code, phones = line.split('\t')
                code = chr(int(code, 16))
                table[code] = phones.strip().split()
    return table

def load_mapping(path):
    """Load phone to phone mapping from path."""
    table = {}
    with open(path) as infile:
        for line in infile:
            line = line.strip()
            if len(line) == 0 or line[0] == '#':
                pass
            else:
                phones = line.split()
                table[phones[0]] = phones[1:]
    return table

def make_argparse():
    """Make the argument parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mapping',
                        help='Mapping from WorldBet table to model phoneset (English/French/whatever')
    parser.add_argument('transcripts',
                        nargs='+',
                        help='Transcript files containing only text in syllabics')
    return parser

def main():
    parser = make_argparse()
    args = parser.parse_args()
    dictionary = defaultdict(int)
    table = load_table("UnifiedCanadianAboriginalSyllabics_unicode.txt")
    mapping = load_mapping(args.mapping)
    
    for line in fileinput.input(args.transcripts):
        words = line.strip().split()
        for word in words:
            dictionary[word] += 1

    for word in sorted(dictionary.keys()):
        phones = []
        for syllabic in word:
            worldbet = table[syllabic]
            for phone in worldbet:
                phones.extend(mapping[phone])
        print("%s\t%s" % (word, ' '.join(phones)))

if __name__ == '__main__':
    main()
