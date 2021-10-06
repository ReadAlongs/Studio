#!/usr/bin/env python3

import os
import tempfile
from unittest import TestCase, main

from basic_test_case import BasicTestCase

from readalongs.align import align_audio


class TestAnchors(BasicTestCase):
    def test_anchors_inner_only(self):
        # ej-fra-anchors has anchors between words/sentences only
        results = align_audio(
            os.path.join(self.data_dir, "ej-fra-anchors.xml"),
            os.path.join(self.data_dir, "ej-fra.m4a"),
        )
        words = results["words"]
        # The input text file has 99 words, so should the aligned segments.
        self.assertEqual(len(words), 99)

        # Make sure the aligned segments stay on the right side of their anchors
        self.assertLessEqual(words[0]["end"], 1.62)
        self.assertGreaterEqual(words[1]["start"], 1.62)
        self.assertLessEqual(words[8]["end"], 3.81)
        self.assertGreaterEqual(words[9]["start"], 3.82)
        self.assertLessEqual(words[21]["end"], 6.74)
        self.assertGreaterEqual(words[22]["start"], 6.74)

    def test_anchors_outer_too(self):
        # ej-fra-anchors2 also has anchors before the first word and after the last word
        save_temps_prefix = os.path.join(self.tempdir, "anchors2-temps")
        results = align_audio(
            os.path.join(self.data_dir, "ej-fra-anchors2.xml"),
            os.path.join(self.data_dir, "ej-fra.m4a"),
            save_temps=save_temps_prefix,
        )
        words = results["words"]
        # The input text file has 99 words, so should the aligned segments.
        self.assertEqual(len(words), 99)

        # Make sure the aligned segments stay on the right side of their anchors,
        # including the initial and final ones inserted into anchors2.xml
        self.assertGreaterEqual(words[0]["start"], 0.5)
        self.assertLessEqual(words[0]["end"], 1.2)
        self.assertGreaterEqual(words[1]["start"], 1.2)
        self.assertLessEqual(words[8]["end"], 3.6)
        self.assertGreaterEqual(words[9]["start"], 3.9)
        self.assertLessEqual(words[21]["end"], 7.0)
        self.assertGreaterEqual(words[22]["start"], 7.0)
        self.assertLessEqual(words[-1]["end"], 33.2)

        # Make sure the audio segment temp files were written and are not empty
        for suff in ("", ".2", ".3", ".4"):
            partial_wav_file = save_temps_prefix + ".wav" + suff
            self.assertTrue(
                os.path.exists(partial_wav_file), f"{partial_wav_file} should exist"
            )
            self.assertGreater(
                os.path.getsize(partial_wav_file),
                0,
                f"{partial_wav_file} should not be empty",
            )


if __name__ == "__main__":
    main()
