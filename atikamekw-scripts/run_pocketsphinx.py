#!/usr/bin/env python3

import pocketsphinx
from sphinxbase import sphinxbase
import logging
import wave
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

def make_fsg(path, lmath):
    """Make an FSG from a lab file."""
    words = []
    with io.open(path) as labfile:
        for spam in labfile:
            words.extend(spam.strip().split())
    base, ext = os.path.splitext(path)
    basename = os.path.basename(base)
    nstates = len(words) + 1
    fsg = sphinxbase.FsgModel(basename, lmath, 1.0, nstates)
    for i, word in enumerate(words):
        wid = fsg.word_add(word)
        fsg.trans_add(i, i + 1, fsg.log(1.0), wid)
        final_state = i + 1
    fsg.set_final_state(final_state)
    return fsg

def main(argv=None):
    ps = pocketsphinx.Pocketsphinx(#verbose=True,
                                   remove_noise=False,
                                   remove_silence=False,
                                   dict='ps_arpabet.dict',
                                   lm=None)
    cfg = ps.get_config()
    lmath = ps.get_logmath()
    frame_size = 1.0 / cfg.get_int('-frate')
    logging.info("Model sample rate: %d, frame size: %f sec",
                 cfg.get_float('-samprate'), frame_size)
    def frames_to_time(frames):
        return frames * frame_size
    
    with io.open('fileids') as fileids:
        for fileid in fileids:
            fileid = fileid.strip()
            wavfile = fileid + '.wav'
            txtfile = fileid + '.lab'

            fsg = make_fsg(txtfile, lmath)
            ps.set_fsg('force_align', fsg)
            ps.set_search('force_align') # This is a silly API, I didn't design it
            with wave.open(wavfile) as wav:
                # FIXME: Obvs need to convert/downsample as needed
                logging.info("Read %s: %d frames (%f seconds) audio"
                             % (wavfile, wav.getnframes(), wav.getnframes() / wav.getframerate()))
                raw_data = wav.readframes(wav.getnframes())
                ps.start_utt()
                ps.process_raw(raw_data, no_search=False, full_utt=True)
                ps.end_utt()

            words = []
            for seg in ps.seg():
                if seg.word in ('<sil>', '[NOISE]'):
                    continue
                start = frames_to_time(seg.start_frame)
                end = frames_to_time(seg.end_frame + 1)
                words.append((seg.word, start, end))
                logging.info("Segment: %s (%.3f : %.3f)",
                             seg.word, start, end)
            write_textgrid(words, fileid + '.TextGrid')

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()
