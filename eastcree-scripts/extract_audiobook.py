#!/usr/bin/env python3

"""
Extract audio and transcripts from eastcree.org read-along books.
"""

from bs4 import BeautifulSoup
import base64
import argparse
import subprocess
import itertools
import os

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('html', help='Self-contained HTML file with audio book')
args = parser.parse_args()

with open(args.html) as fp:
    soup = BeautifulSoup(fp)
title, _ = os.path.splitext(args.html)
out_dir = '%s_data' % (title)
try:
    os.mkdir(out_dir)
except OSError:
    pass
# mapping to remove (some) punctuation
delpunc = dict((ord(c), None) for c in '᙮,!?.()')
for i, page in enumerate(soup.find_all('div', 'item')):
    fileid = "%s_page%d" % (title, i + 1)
    cree = page.find_all('span', 'cree')
    print("%s %s" % (fileid, cree))
    if cree:
        cree_text = ' '.join(itertools.chain(*(tag.stripped_strings for tag in cree)))
        cree_text = cree_text.translate(delpunc)
        with open(os.path.join(out_dir, "%s.lab" % (fileid)), 'w') as labels:
            labels.write(cree_text)
            labels.write('\n')
    else:
        cree_text = 'TRANSCRIBE_ME_PLEASE'
    if page.audio:
        audio_base64 = page.audio.source['src'] # I think BS4 always decodes this :(
        audio_data = base64.decodestring(audio_base64.encode('ascii')) # we want bytes
        # use sox to convert it to 16khz mono wav
        out_file = os.path.join(out_dir, "%s.wav" % (fileid))
        with subprocess.Popen(['sox', '-t', 'mp3', '-', out_file, 'rate', '16k', 'channels', '1'],
                              stdin=subprocess.PIPE) as sox:
            sox.stdin.write(audio_data)
    else:
        print("No audio on page %d (%s)" % (i + 1, cree_text))
