#!/usr/bin/env python3

"""Test suite for inserting silences into a readalong"""

import os
from unittest import expectedFailure, main

from basic_test_case import BasicTestCase
from lxml import etree
from pydub import AudioSegment
from sound_swallower_stub import SoundSwallowerStub

from readalongs.cli import align


class TestSilence(BasicTestCase):
    """Test suite for inserting silences into a readalong"""

    def test_basic_silence_insertion(self):
        """Basic usage of the silence feature in a readalong"""
        output = os.path.join(self.tempdir, "silence")
        # Run align from xml
        results = self.runner.invoke(
            align,
            [
                "-s",
                "-C",
                "-t",
                "-l",
                "fra",
                os.path.join(self.data_dir, "ej-fra-silence.xml"),
                os.path.join(self.data_dir, "ej-fra.m4a"),
                output,
            ],
        )
        self.assertEqual(results.exit_code, 0)
        self.assertTrue(os.path.exists(os.path.join(output, "silence.m4a")))
        # test silence spans in output xml
        with open(os.path.join(output, "silence.xml"), "rb") as f:
            xml_bytes = f.read()
        root = etree.fromstring(xml_bytes)
        silence_spans = root.xpath("//silence")
        self.assertEqual(len(silence_spans), 3)
        # test audio has correct amount of silence added
        original_audio = AudioSegment.from_file(
            os.path.join(self.data_dir, "ej-fra.m4a")
        )
        new_audio = AudioSegment.from_file(
            os.path.join(output, "silence.m4a"), format="m4a"
        )
        self.assertAlmostEqual(
            len(new_audio) - len(original_audio),
            2882,
            msg="silence-added audio file is more than 50ms shorter or longer",
            delta=50,
        )

    @expectedFailure
    def test_silence_insertion_with_incomplete_align_output(self):
        """Test silence when not all words actually get aligned"""

        # Related to https://github.com/ReadAlongs/Studio/issues/89
        # delete the @expectedFailure line above once #89 is fixed.

        # This stub returns all the words before the last silence, but is missing
        # the words in the next paragraphs. This is similar to having a
        # do-not-align block, or using anchors where alignment fails in some
        # but not all anchor-defined segments.
        output = os.path.join(self.tempdir, "silence")
        # Run align from xml
        segment_list = [
            "t0b0d0p0s0w0:920:1610",
            "t0b0d0p0s1w0:1620:1680",
            "t0b0d0p0s1w1:1690:1770",
            "t0b0d0p0s1w2:1780:1990",
            "t0b0d0p0s1w3:2000:2340",
            "t0b0d0p0s1w4:2350:2570",
            "t0b0d0p0s2w0:2580:2620",
            "t0b0d0p0s2w1:2630:2860",
            "t0b0d0p0s2w2:3040:3810",
            "t0b0d0p0s2w3:3820:3920",
            "t0b0d0p0s2w4:3930:4140",
            "t0b0d0p0s2w5:4150:4230",
            "t0b0d0p0s2w6:4240:4260",
            "t0b0d0p0s2w7:4270:4560",
            "t0b0d0p0s2w8:4570:4680",
            "t0b0d0p0s2w9:4690:5230",
            "t0b0d0p0s2w10:5240:5560",
            "t0b0d0p0s2w11:5570:5590",
            "t0b0d0p0s2w12:5600:5850",
            "t0b0d0p0s2w13:5860:6310",
            "t0b0d0p0s2w14:6320:6350",
            "t0b0d0p0s2w15:6360:6580",
        ]
        with SoundSwallowerStub(*segment_list):
            results = self.runner.invoke(
                align,
                [
                    "-s",
                    "-C",
                    "-t",
                    "-l",
                    "fra",
                    os.path.join(self.data_dir, "ej-fra-silence.xml"),
                    os.path.join(self.data_dir, "ej-fra.m4a"),
                    output,
                ],
            )
        print(results.output)
        print(f"results.exception={results.exception!r}")
        self.assertEqual(results.exit_code, 0)
        self.assertTrue(os.path.exists(os.path.join(output, "silence.m4a")))
        # test silence spans in output xml
        with open(os.path.join(output, "silence.xml"), "rb") as f:
            xml_bytes = f.read()
        root = etree.fromstring(xml_bytes)
        silence_spans = root.xpath("//silence")
        self.assertEqual(len(silence_spans), 3)
        # test audio has correct amount of silence added
        original_audio = AudioSegment.from_file(
            os.path.join(self.data_dir, "ej-fra.m4a")
        )
        new_audio = AudioSegment.from_file(
            os.path.join(output, "silence.m4a"), format="m4a"
        )
        self.assertAlmostEqual(
            len(new_audio) - len(original_audio),
            2882,
            msg="silence-added audio file is more than 50ms shorter or longer",
            delta=50,
        )

    def test_bad_silence(self):
        output = os.path.join(self.tempdir, "bad_silence")
        # Run align from bad xml
        results = self.runner.invoke(
            align,
            [
                "-s",
                "-C",
                "-t",
                "-l",
                "fra",
                os.path.join(self.data_dir, "ej-fra-silence-bad.xml"),
                os.path.join(self.data_dir, "ej-fra.m4a"),
                output,
            ],
        )
        self.assertEqual(results.exit_code, 1)


if __name__ == "__main__":
    main()
