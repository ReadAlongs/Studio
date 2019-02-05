#!/usr/bin/env python3

"""Prepare data for force alignment."""

import argparse
import errno
import re
import os
import io

def read_audiobook(inputdir):
    """Iterate over pages in the book."""
    page_re = re.compile(r'(\d+).*\.txt$')
    pages = []
    for name in os.listdir(inputdir):
        m = page_re.match(name)
        if m is None:
            continue
        pagenum = int(m.group(1))
        pages.append((pagenum, name))
    pages.sort()
    for pagenum, name in pages:
        with io.open(os.path.join(inputdir, name)) as fh:
            text = fh.read()
            yield pagenum, name, text

TOKEN_RE = re.compile(r'\w+')
def tokenize(text):
    """Tokenize/normalize text, retaining pointers to input."""
    for match in TOKEN_RE.finditer(text):
        token = match.group(0)
        yield token, token.lower(), match.start(0), match.end(0)

MAPPING = {
    'p' : 'B',
    't' : 'D',
    'k' : 'G',
    's' : 'Z',
    'c' : 'SH',
    'tc' : 'D Z',
    'm' : 'M',
    'n' : 'N',
    'r' : 'T',
    'h' : 'HH',
    'w' : 'W',
    'a' : 'AH',
    'e' : 'EY',
    'i' : 'IH',
    'o' : 'UW',
}
MAPPING_GREEDY = sorted(MAPPING.keys(), key=lambda x: len(x), reverse=True)

G2P_RE = re.compile('(' + '|'.join(MAPPING_GREEDY) + ')')
def atj_g2p(lemma):
    """Very approximate G2P!"""
    phones = []
    for match in G2P_RE.finditer(lemma):
        graph =  match.group(1)
        phones.extend(MAPPING[graph].split())
    return phones

def save_lexicon(lexicon, outfile):
    with open(outfile, 'w') as outfh:
        for word in sorted(lexicon):
            outfh.write('%s\t%s\n' % (word, ' '.join(lexicon[word])))

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

def process_audiobook(args):
    lexicon = {}
    with open(os.path.join(args.outputdir, 'fileids'), 'w') as fileids:
        for pagenum, name, text in read_audiobook(args.inputdir):
            fileid = '%03d_%s' % (int(pagenum), os.path.splitext(name)[0])
            outpath = os.path.join(args.outputdir, fileid + '.lab')
            with open(outpath, 'w') as outfh:
                for token, lemma, start, end in tokenize(text):
                    if lemma not in lexicon:
                        lexicon[lemma] = atj_g2p(lemma)
                    outfh.write(lemma)
                    outfh.write(' ')
                outfh.write('\n')
            make_fsg(outpath)
            outwav = os.path.join(args.outputdir, fileid + '.wav')
            inwav = os.path.join(os.path.abspath(args.inputdir), os.path.splitext(name)[0] + '.wav')
            if not os.path.exists(inwav):
                raise RuntimeError('Input .wav file %s does not exist' % inwav)
            os.symlink(inwav, outwav)
            fileids.write('%s\n' % fileid)
    save_lexicon(lexicon, os.path.join(args.outputdir, 'ps_arpabet.dict'))

def make_argparse():
    """Create argument parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('inputdir', help='Directory with input .txt files')
    parser.add_argument('outputdir', help='Directory to receive .lab and .dict files')
    return parser

def main(argv=None):
    """Hi, my name is `main`"""
    parser = make_argparse()
    args = parser.parse_args(argv)
    try:
        os.makedirs(args.outputdir)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise e
    process_audiobook(args)

if __name__ == '__main__':
    main()
