#!/usr/bin/env python

import sys
import os
import io

def write_textgrid(words, path):
    with io.open(path, 'w') as tg:
        xmin = words[0][1]
        xmax = words[-1][2]
        tg.write("""File type = "ooTextFile"
Object class = "TextGrid"

xmin = %f
xmax = %f
tiers? <exists>
size = 1
item []:
	item [1]:
		class = "IntervalTier"
		name = "words"
		xmin = %f
		xmax = %f
		intervals: size = %d
""" % (xmin, xmax, xmin, xmax, len(words)))
        for word, start, end in words:
            tg.write("""			intervals [1]:
				xmin = %f
				xmax = %f
				text = "%s"
""" % (start, end, word))

def make_textgrids(path):
    """Make textgrids from a hypseg file."""
    with io.open(path) as hypseg:
        for spam in hypseg:
            words = []
            spam = spam.strip().split()
            base = spam[0]
            # Skip the scores and go to the words
            i = 10
            start = float(spam[9]) * 0.01
            while i < len(spam):
                _, _, word, ef = spam[i:i+4]
                end = float(ef) * 0.01
                words.append((word, start, end))
                start = end
                i += 4
            write_textgrid(words, os.path.join(os.path.dirname(path), base + '.TextGrid'))

def main():
    make_textgrids(sys.argv[1])

if __name__ == '__main__':
    main()
