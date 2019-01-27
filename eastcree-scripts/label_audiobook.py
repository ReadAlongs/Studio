#!/usr/bin/env python3

"""Align text to audio in eastcree.org read-along lessons and add code to
highlight words as they are spoken.

Currently uses SoX and Montreal Forced Aligner.  Also requires a few
Python modules from PyPI:

BeautifulSoup
textgrid

Written by David Huggins Daines <dhdaines@gmail.com>
Some parts from NLTK and Prosodylab-Align, also under MIT license.

"""

# Copyright (c) 2018 David Huggins Daines

# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:

# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


from bs4 import BeautifulSoup
from collections import defaultdict

import base64
import textgrid
import fileinput
import argparse
import subprocess
import itertools
import os
import io

def load_table(stream):
    """Load syllabic to phone mapping from file."""
    table = {}
    for line in stream:
        line = line.strip()
        if len(line) == 0 or line[0] == '#':
            pass
        else:
            code, phones = line.split('\t')
            code = chr(int(code, 16))
            table[code] = phones.strip().split()
    return table

def load_mapping(stream):
    """Load phone to phone mapping from file."""
    table = {}
    for line in stream:
        line = line.strip()
        if len(line) == 0 or line[0] == '#':
            pass
        else:
            phones = line.split()
            table[phones[0]] = phones[1:]
    return table

def make_argparse():
    """Make the argparse."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-m', '--mfa',
                        help='Path to Montreal Forced Aligner (default to $MFADIR)',
                        default=os.getenv('MFADIR',
                                          os.path.join(os.getenv('HOME'),
                                                       'montreal-forced-aligner')))
    parser.add_argument('html', help='Self-contained HTML file with audio book')
    args = parser.parse_args()
    if not os.path.exists(os.path.join(args.mfa, 'bin', 'mfa_align')):
        parser.error('Could not find Montreal Forced Aligner, please set $MFADIR '
                     'or use --mfa option')
    return parser

def make_dict(dict_file, label_files):
    """Make a "fake" pronunciation dictionary by mapping Cree syllabics to
    close-ish English phonemes.
    """
    unicode_table = load_table(io.StringIO(UNICODE_TABLE))
    arpabet_mappings = load_mapping(io.StringIO(ARPABET_MAPPINGS))
    dictionary = defaultdict(int)
    for line in fileinput.input(label_files):
        words = line.strip().split()
        for word in words:
            dictionary[word] += 1
    with open(dict_file, 'w') as dictfh:
        for word in sorted(dictionary.keys()):
            phones = []
            for syllabic in word:
                worldbet = unicode_table[syllabic]
                for phone in worldbet:
                    phones.extend(arpabet_mappings[phone])
            dictfh.write("%s\t%s\n" % (word, ' '.join(phones)))

def label_audiobook(mfa_path, html_path):
    """Label an audiobook."""
    with open(html_path) as fp:
        soup = BeautifulSoup(fp)
    base_path, _ = os.path.splitext(html_path)
    out_dir = '%s_data' % (base_path)
    title = os.path.basename(base_path)
    try:
        os.mkdir(out_dir)
    except OSError:
        pass
    # mapping to remove (some) punctuation
    delpunc = dict((ord(c), None) for c in '᙮,!?.()')
    # Dump out the text and audio
    label_files = []
    for i, page in enumerate(soup.find_all('div', 'item')):
        fileid = "%s_page%d" % (title, i + 1)
        cree = page.find_all('span', 'cree')
        if cree:
            cree_text = ' '.join(itertools.chain(*(tag.stripped_strings
                                                   for tag in cree)))
            cree_text = cree_text.translate(delpunc)
            label_file = os.path.join(out_dir, "%s.lab" % (fileid))
            with open(label_file, 'w') as labels:
                labels.write(cree_text)
                labels.write('\n')
            label_files.append(label_file)
        else:
            print("No text on page %d" % (i + 1))
            continue
        print("%s %s" % (fileid, cree_text))
        
        if page.audio:
            audio_base64 = page.audio.source['src'] # I think BS4 always decodes this :(
            audio_data = base64.decodestring(audio_base64.encode('ascii')) # we want bytes
            # use sox to convert it to 16khz mono wav
            out_file = os.path.join(out_dir, "%s.wav" % (fileid))
            with subprocess.Popen(['sox', '-t', 'mp3', '-', out_file,
                                   'rate', '16k', 'channels', '1'],
                                  stdin=subprocess.PIPE) as sox:
                sox.stdin.write(audio_data)
        else:
            print("No audio on page %d (%s)" % (i + 1, cree_text))
    # Fake up a dictionary
    dict_file = os.path.join(out_dir, "arpabet.dict")
    make_dict(dict_file, label_files)
    # Now run alignment!
    subprocess.run([os.path.join(mfa_path, 'bin', 'mfa_align'),
                    out_dir, dict_file, 'english', out_dir], check=True)
    align_dir = os.path.join(out_dir, os.path.basename(out_dir))
    if not os.path.exists(align_dir): # MFA 1.1 and 1.0 are different
        align_dir = out_dir
    # Now splice the alignments back into the file!
    for i, page in enumerate(soup.find_all('div', 'item')):
        fileid = "%s_page%d" % (title, i + 1)
        alignfile = os.path.join(align_dir, "%s.TextGrid" % fileid)
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
        var clickedSegment = null;
        $("audio").on('timeupdate', function(){
            var timestamp = this.currentTime;
            var audio = this;
            if (clickedSegment != null
                && timestamp >= clickedSegment.getAttribute('data-end')) {
                audio.pause(); // clickedSegment gets cleared later
                return;
            }
            $("div.active span.segment").each(function(index, element) {
                var segStart = element.getAttribute('data-start');
                var segEnd = element.getAttribute('data-end');
                if (segStart <= timestamp && segEnd > timestamp) {
                    $(element).addClass('active');
                }
                else {
                    $(element).removeClass('active');
                }
            });
        });
        $("audio").on("pause", function() {
            clickedSegment = null;
            $("span.segment").removeClass('active');
        });
        $("span.segment").on('click', function() {
            var audio = $("div.active audio")[0]
            audio.currentTime = this.getAttribute('data-start');
            audio.play();
            clickedSegment = this;
        });
    });
    """)

    with open("%s_aligned.html" % (base_path), 'w') as fp:
        fp.write(soup.prettify())
        
def main(argv=None):
    parser = make_argparse()
    args = parser.parse_args(argv)
    label_audiobook(args.mfa, args.html)

ARPABET_MAPPINGS = """
# Approximate phoneme mappings from NLTK Unicode-to-WorldBet table to
# ARPABET for force alignment of East Cree (note that the Unicode
# table has Inuktitut phonemes in it, we map those to Cree phonemes
# here too) Cree phones in "dictionary" order are at the top, others
# below
aI	    EH1
i	    IH0
i:	    IY1
u	    UH1
u:	    UW1
A	    AH1
A:	    AA1
p	    P
pw	    P W
t	    T
tw	    T W
k	    K
kw	    K W
G	    CH
Gw	    CH W
m	    M
mw	    M W
n	    N
nw	    N W
l	    L
lw	    L W
s	    S
sw	    S W
S	    SH
Sw	    SH W
j	    Y
jw	    Y W
h	    HH
w	    W
?	    HH
# Not Cree sounds but we might encounter them, perhaps
r	    R
rw	    R W
v	    V
vw	    V W
o:	    OW1
e:	    EY1
e	    EY2
o	    OW2
a	    AH0
d	    D
eh	    EH1 HH
ih	    IH1 HH
oh	    OW2 HH
ah	    AA2 HH
D	    DH
mh	    M HH
N	    NG
nh	    N HH
cw	    T S W
Dw	    DH W
tj	    T Y
q	    K
th	    T HH
hl	    HH L
b	    B
Gh	    CH HH
hw	    HH W
kh	    K HH
z	    Z
dz	    D Z
ts	    T S
"""

UNICODE_TABLE = """
#Unified Canadian Aboriginal Syllabics
#From nltk_contrib/scripttranscriber/Unitran

#Syllables
1401	aI
1402	A: i
1403	i
1404	i:
1405	u
1406	u:
1407	o:
1408	e:
1409	i
140A	A
140B	A:
140C	w e
140D	w e
140E	w i
140F	w i
1410	w i:
1411	w i:
1412	w o
1413	w o
1414	w o:
1415	w o:
1416	w o:
1417	w A
1418	w A
1419	w A:
141A	w A:
141B	w A:
141C	A:
141D	w
141E	?
141F	?
1420	k
1421	S	
1422	s
1423	n
1424	w
1425	t t
1426	h
1427	w
1428	G
1429	n
142A	l
142B	e n
142C	i n
142D	o n
142E	a n
142F	p aI
1430	p A: i
1431	p i	
1432	p i:
1433	p u
1434	p u:
1435	p o:	
1436	h e:
1437	h i
1438	p A
1439	p A:
143A	pw e
143B	pw e
143C	pw i
143D	pw i
143E	pw i:
143F	pw i:
1440	pw o
1441	pw o
1442	pw o:
1443	pw o:
1444	pw A
1445	pw A
1446	pw A:
1447	pw A:
1448	pw A:
1449	p	
144A	h
144B	t aI
144C	t A: i
144D	t i
144E	t i
144F	t i:
1450	t u
1451	t u:
1452	t o:	
1453	d e:
1454	d i
1455	t A
1456	t A:
1457	tw e
1458	tw i
1459	tw i
145A	tw i:
145B	tw i:
145C	tw i:
145D	tw o
145E	tw o
145F	tw o:
1460	tw o:
1461	tw A
1462	tw A
1463	tw A:
1464	tw A:
1465	tw A:
1466	t
1467	t t e	
1468	t t i
1469	t t o
146A	t t A
146B	k aI
146C	k A: i
146D	k i	
146E	k i:
146F	k u
1470	k u:
1471	k o:
1472	k A
1473	k A:
1474	kw e
1475	kw e
1476	kw i
1477	kw i
1478	kw i:
1479	kw i:
147A	kw o
147B	kw o
147C	kw o:
147D	kw o:
147E	kw A
147F	kw A
1480	kw A
1481	kw A:
1482	kw A:
1483	k
1484	kw
1485	k eh
1486	k ih
1487	k oh
1488	k ah
1489	G aI
148A	G A: i
148B	G i
148C	G i:
148D	G u
148E	G u:
148F	G o:
1490	G A
1491	G A:
1492	Gw e
1493	Gw e
1494	Gw i
1495	Gw i
1496	Gw i:
1497	Gw i:
1498	Gw o
1499	Gw o
149A	Gw o:
149B	Gw o:
149C	Gw A
149D	Gw A
149E	Gw A:
149F	Gw A:
14A0	Gw A:
14A1	G
14A2	D
14A3	m aI
14A4	m A: i
14A5	m i
14A6	m i:
14A7	m u
14A8	m u:
14A9	m o:
14AA	m A
14AB	m A:
14AC	mw e
14AD	mw e
14AE	mw i
14AF	mw i
14B0	mw i:
14B1	mw i:
14B2	mw o
14B3	mw o
14B4	mw o:
14B5	mw o:
14B6	mw A
14B7	mw A
14B8	mw A:
14B9	mw A:
14BA	mw A:
14BB	m
14BC	m
14BD	mh
14BE	m
14BF	m
14C0	n aI
14C1	n A: i
14C2	n i
14C3	n i:
14C4	n u
14C5	n u:
14C6	n o:
14C7	n A
14C8	n A:
14C9	nw e
14CA	nw e
14CB	nw A
14CC	nw A
14CD	nw A:
14CE	nw A:
14CF	nw A:
14D0	n
14D1	N
14D2	nh
14D3	l aI
14D4	l A: i
14D5	l i
14D6	l i:
14D7	l u
14D8	l u:
14D9	l o:
14DA	l A
14DB	l A:
14DC	lw e
14DD	lw e
14DE	lw i
14DF	lw i
14E0	lw i:
14E1	lw i:
14E2	lw o
14E3	lw o
14E4	lw o:
14E5	lw o:
14E6	lw A
14E7	lw A
14E8	lw A:
14E9	lw A:
14EA	l
14EB	l
14EC	l
14ED	s aI
14EE	s A: i
14EF	s i	
14F0	s i:
14F1	s u
14F2	s u:
14F3	s o:
14F4	s A
14F5	s A:
14F6	sw e
14F7	sw e
14F8	sw i
14F9	sw i
14FA	sw i:
14FB	sw i:
14FC	sw o
14FD	sw o
14FE	sw o:
14FF	sw o:
1500	sw A
1501	sw A
1502	sw A:
1503	sw A:
1504	sw A:
1505	s
1506	s
1507	sw
1508	s
1509	s k
150A	s kw
150B	s w
150C	s pw A
150D	s tw A
150E	s kw A
150F	s cw A
1510	S e
1511	S i
1512	S i:
1513	S o
1514	S o:
1515	S A
1516	S A:
1517	Sw e
1518	Sw e
1519	Sw i
151A	Sw i
151B	Sw i:
151C	Sw i:
151D	Sw o
151E	Sw o
151F	Sw o:
1520	Sw o:
1521	Sw A
1522	Sw A
1523	Sw A:
1524	Sw A:
1525	S
1526	j aI
1527	j A: i
1528	j i
1529	j i:
152A	j u
152B	j u:
152C	j o:
152D	j A
152E	j A:
152F	jw e
1530	jw e
1531	jw i
1532	jw i
1533	jw i:
1534	jw i:
1535	jw o
1536	jw o
1537	jw o:
1538	jw o:
1539	jw A
153A	jw A
153B	jw A:
153C	jw A:
153D	jw A:
153E	j
153F	j
1540	j
1541	j i
1542	r aI
1543	r e
1544	l e
1545	r A: i
1546	r i
1547	r i:
1548	r u
1549	r u:
154A	l o
154B	r A
154C	r A:
154D	l a 
154E	rw A:
154F	rw A:
1550	r
1551	r
1552	r
1553	v aI
1554	v A: i
1555	v i
1556	v i:
1557	v o
1558	v o:
1559	v A
155A	v A:
155B	vw A:
155C	vw A:
155D	v
155E	D e
155F	D e
1560	D i
1561	D i
1562	D i:
1563	D i:
1564	D o
1565	D o:
1566	D A
1567	D A:
1568	Dw A:
1569	Dw A:
156A	D
156B	D e	
156C	D i
156D	D o
156E	D A
156F	D
1570	tj e
1571	tj i
1572	tj o
1573	tj A
1574	h e
1575	h i
1576	h i:
1577	h o
1578	h o:
1579	h A
157A	h A:
157B	h
157C	h
157D	h k
157E	q A: i
157F	q i	
1580	q i:
1581	q u
1582	q u:
1583	q A
1584	q A:
1585	q
1586	th l e
1587	th l i
1588	th l o
1589	th l A
158A	r e
158B	r i
158C	r o
158D	r A
158E	N aI
158F	N i
1590	N i:
1591	N u
1592	N u:
1593	N A
1594	N A:
1595	N
1596	N
1597	S e
1598	S i
1599	S o
159A	S A
159B	D e
159C	D i
159D	D o
159E	D A
159F	D
15A0	hl i
15A1	hl i:
15A2	hl u
15A3	hl u:
15A4	hl A
15A5	hl A:
15A6	hl
15A7	D e
15A8	D i
15A9	D i:
15AA	D o
15AB	D o:
15AC	D A
15AD	D A:
15AE	D
15AF	b
15B0	e
15B1	i
15B2	o
15B3	A
15B4	w e 
15B5	w i
15B6	w o
15B7	w A
15B8	n e
15B9	n i
15BA	n o
15BB	n A
15BC	k e
15BD	k i
15BE	k o
15BF	k A
15C0	h e
15C1	h i
15C2	h o
15C3	h A
15C4	Gh u
15C5	Gh o
15C6	Gh e
15C7	Gh e:
15C8	Gh i
15C9	Gh A
15CA	r u
15CB	r o
15CC	r e
15CD	r e:
15CE	r i
15CF	r A
15D0	w u
15D1	w o
15D2	w e
15D3	w e:
15D4	w i
15D5	w A
15D6	hw u
15D7	hw o
15D8	hw e
15D9	hw e:
15DA	hw i
15DB	hw A
15DC	D u
15DD	D o
15DE	D e
15DF	D e:
15E0	D i
15E1	D A
15E2	t t u
15E3	t t o
15E4	t t e
15E5	t t e:
15E6	t t i
15E7	t t A
15E8	p u
15E9	p o
15EA	p e
15EB	p e:
15EC	p i
15ED	p A
15EE	p
15EF	G u
15F0	G o
15F1	G e
15F2	G e:
15F3	G i
15F4	G A
15F5	kh u
15F6	kh o
15F7	kh e
15F8	kh e:
15F9	kh i
15FA	kh A
15FB	k k u
15FC	k k o
15FD	k k e
15FE	k k e:
15FF	k k i
1600	k k A
1601	k k
1602	n u
1603	n o
1604	n e
1605	n e:
1606	n i
1607	n A
1608	m u
1609	m o
160A	m e
160B	m e:
160C	m i
160D	m A
160E	j u
160F	j o
1610	j e
1611	j e:
1612	j i
1613	j A
1614	z u
1615	z u
1616	z o
1617	z e
1618	z e:
1619	z i
161A	z i
161B	z A
161C	z z u	
161D	z z o
161E	z z e
161F	z z e:
1620	z z i
1621	z z A
1622	l u
1623	l o
1624	l e
1625	l e:
1626	l i
1627	l A
1628	d l u
1629	d l o
162A	d l e
162B	d l e:
162C	d l i
162D	d l A
162E	hl u
162F	hl o
1630	hl e
1631	hl e:
1632	hl i
1633	hl A
1634	th l u
1635	th l o
1636	th l e
1637	th l e:
1638	th l i
1639	th l A
163A	t l u
163B	t l o
163C	t l e
163D	t l e:
163E	t l i
163F	t l A
1640	z u
1641	z o
1642	z e
1643	z e:
1644	z i
1645	z A
1646	z
1647	z
1648	dz u
1649	dz o
164A	dz e
164B	dz e:
164C	dz i
164D	dz A
164E	s u
164F	s o
1650	s e
1651	s e:
1652	s i
1653	s A
1654	S u
1655	S o
1656	S e
1657	S e:
1658	S i
1659	S A 
165A	S
165B	ts u
165C	ts o
165D	ts e
165E	ts e:
165F	ts i
1660	ts A
1661	Gh u
1662	Gh o
1663	Gh e
1664	Gh e:
1665	Gh i	
1666	Gh A
1667	ts u
1668	ts o
1669	ts e
166A	ts e:
166B	ts i
166C	ts A
#Symbol
166D	(SYMBOL TO DENOTE CHRIST)
#Punctuation
166E	(FULL STOP)
#Syllables
166F	q aI
1670	N aI
1671	N i
1672	N i:
1673	N o
1674	N o:
1675	N A
1676	N A:
"""

if __name__ == '__main__':
    main()
