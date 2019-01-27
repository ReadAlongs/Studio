#!/usr/bin/env python3

"""
Extract audio and transcripts from eastcree.org read-along books.
"""

from bs4 import BeautifulSoup
import base64
import argparse
import subprocess
import itertools
import textgrid
import os

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('html', help='Self-contained HTML file with audio book')
parser.add_argument('aligndir', help='Directory with time alignment files')
args = parser.parse_args()

with open(args.html) as fp:
    soup = BeautifulSoup(fp)
title, _ = os.path.splitext(args.html)
# mapping to remove (some) punctuation (for sanity-checking only...)
delpunc = dict((ord(c), None) for c in '᙮,!?.()')
for i, page in enumerate(soup.find_all('div', 'item')):
    fileid = "%s_page%d" % (title, i + 1)
    alignfile = os.path.join(args.aligndir, "%s.TextGrid" % fileid)
    try:
        alignment = textgrid.TextGrid.fromFile(alignfile)
    except FileNotFoundError:
        print("No alignment for page %d, skipping" % (i + 1))
        continue
    for tier in alignment:
        if tier.name == 'words':
            break
    assert tier.name == 'words'

    print(fileid)
    # change all the Cree spans to contain time alignments
    cree = page.find_all('span', 'cree')
    for tag in cree:
        contents = []
        intervals = (i for i in tier if i.mark)
        for element in tag:
            if element.name == 'br':
                contents.append(soup.new_tag('br'))
            elif element.string is not None:
                for word in element.string.strip().split():
                    # make sure the alignment matches the text!
                    interval = next(intervals)
                    assert word.translate(delpunc) == interval.mark
                    span = soup.new_tag('span')
                    span['class'] = 'segment'
                    span['data-start'] = interval.minTime
                    span['data-end'] = interval.maxTime
                    span.string = word
                    contents.append(span)
                    contents.append(" ")
        tag.clear()
        for span in contents:
            tag.append(span)

# Now add some CSS and Javascript
soup.find_all('style')[-1].append("""
    span.active { color: #2222aa }
""")
soup.find_all('script')[-1].append("""
    $(document).ready(function () {
        $("audio").on('timeupdate', function(){
            timestamp = this.currentTime;                                    
            $("div.active span.segment").each(function(index, element) {
                if (element.getAttribute('data-start') <= timestamp
                    && element.getAttribute('data-end') > timestamp) {
                    $(element).addClass('active');
                }
                else {
                    $(element).removeClass('active');
                }
            });
        });
    });
""")

with open("%s_aligned.html" % (title), 'w') as fp:
    fp.write(soup.prettify())
