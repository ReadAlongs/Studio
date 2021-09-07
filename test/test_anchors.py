#!/usr/bin/env python3

import os
from unittest import TestCase, main

from readalongs.align import align_audio


class TestAnchors(TestCase):
    data_dir = os.path.join(os.path.dirname(__file__), "data")

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_anchors_inner_only(self):
        # ej-fra-anchors has anchors between words/sentences only
        results = align_audio(
            os.path.join(self.data_dir, "ej-fra-anchors.xml"),
            os.path.join(self.data_dir, "ej-fra.m4a"),
        )
        words = results["words"]
        self.assertEqual(len(words), 99)
        self.assertLessEqual(words[0]["end"], 1.62)
        self.assertGreaterEqual(words[1]["start"], 1.62)
        self.assertLessEqual(words[8]["end"], 3.81)
        self.assertGreaterEqual(words[9]["start"], 3.82)
        self.assertLessEqual(words[21]["end"], 6.74)
        self.assertGreaterEqual(words[22]["start"], 6.74)

    def test_anchors_outer_too(self):
        # ej-fra-anchors2 also has anchors before the first word and after the last word
        results = align_audio(
            os.path.join(self.data_dir, "ej-fra-anchors2.xml"),
            os.path.join(self.data_dir, "ej-fra.m4a"),
        )
        words = results["words"]
        self.assertEqual(len(words), 99)
        self.assertGreaterEqual(words[0]["start"], 0.5)
        self.assertLessEqual(words[0]["end"], 1.2)
        self.assertGreaterEqual(words[1]["start"], 1.2)
        self.assertLessEqual(words[8]["end"], 3.6)
        self.assertGreaterEqual(words[9]["start"], 3.9)
        self.assertLessEqual(words[21]["end"], 7.0)
        self.assertGreaterEqual(words[22]["start"], 7.0)
        self.assertLessEqual(words[-1]["end"], 33.2)


if __name__ == "__main__":
    main()
