"""
This SoundSwallower stub exists to speed up unit tests that don't actually
verify that forced alignment works, but rather that other parts of the software
works correctly.

To use this stub, create a context using a with statement where you provide the
output you want to pretend the SoundSwallower decoder produced.

Usage:

    with SoundSwallowerStub(
        "[NOISE]:0:100", "p0s0w0:100:1000", "<sil>:1000:1100", "p0s0w1:1100:2000"
    ):
        invoke align

will get align() to receive one noise segment, word p0s0w0 from 100 to 1000 ms,
a silence segment, and word p0s0w1 from 1100 to 2000 ms, regardless if the
input it provides to the decoder.
"""

from contextlib import contextmanager

import soundswallower


@contextmanager
def SoundSwallowerStub(*segments):
    """Stub SoundSwallower and make it pretend to produce the segments given

    Args:
        *segments: a list of segments to produce, in "wordid:start:end" format, where
            - wordid is like p0s0w0, or any string you want, it usually doesn't matter
            - start is the segment's start_frame time in ms
            - end is the segment's end_frame time is ms
    """
    try:
        saved_soundswallower_decoder = soundswallower.Decoder
        soundswallower.Decoder = SoundSwallowerDecoderStub(*segments)
        yield
    finally:
        soundswallower.Decoder = saved_soundswallower_decoder


class SoundSwallowerDecoderStub:
    """Stub class so we don't really call the SoundSwallower decoder"""

    class Segment:
        def __init__(self, segment_desc):
            """Init self from "word_id:start:end" description, e.g. "p0s0w0:0:1"."""
            self.word, s, e = segment_desc.split(":")
            self.start_frame = int(s)
            self.end_frame = int(e)

        def __repr__(self):
            return f'Segment(word="{self.word}", start_frame={self.start_frame}, end_frame={self.end_frame})'

    class Config:
        def __init__(self, *args):
            pass

        def set_boolean(self, *args):
            pass

        def set_string(self, *args):
            pass

        def set_float(self, *args):
            pass

        def set_int(self, *args):
            pass

        def get_float(self, *args):
            return 1.0

        def get_int(self, name):
            if name == "-frate":
                # Pretend the framerate is always 1000, so the stub times are all in ms
                return 1000
            else:
                return 1

    def __init__(self, *outputs):
        self._segments = [
            SoundSwallowerDecoderStub.Segment(segment) for segment in outputs
        ]

    def __call__(self, *args):
        return self

    def start_utt(self):
        pass

    def process_raw(self, *args, **kwargs):
        pass

    def end_utt(self):
        pass

    def seg(self):
        return self._segments

    def default_config(self):
        return SoundSwallowerDecoderStub.Config()
