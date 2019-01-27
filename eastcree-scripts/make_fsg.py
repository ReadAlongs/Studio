#!/usr/bin/env python

import sys
import os
import io

def make_fsg(path):
    """Make an FSG from a lab file."""
    words = []
    with io.open(path) as labfile:
        for spam in labfile:
            words.extend(spam.strip().split())
    base, ext = os.path.splitext(path)
    basename = os.path.basename(base)
    with io.open(base + '.fsg', 'w') as fsgfile:
        fsgfile.write("""FSG_BEGIN %s
NUM_STATES %d
START_STATE %d
FINAL_STATE %d

""" % (basename, len(words) + 1, 0, len(words)))
        for i, word in enumerate(words):
            fsgfile.write("TRANSITION %d %d 1.0 %s\n" % (i, i + 1, word))
        fsgfile.write("FSG_END\n")

def main():
    for path in sys.argv[1:]:
        make_fsg(path)

if __name__ == '__main__':
    main()
