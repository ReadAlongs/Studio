#!/usr/bin/env python

"""Test suite for inserting silences into a readalong"""

import os
from unittest import main

from basic_test_case import BasicTestCase
from pydub import AudioSegment

from readalongs.cli import align
from readalongs.text.util import load_xml


class TestSilence(BasicTestCase):
    """Test suite for inserting silences into a readalong"""

    def test_basic_silence_insertion(self):
        """Basic usage of the silence feature in a readalong"""
        output = self.tempdir / "silence"
        # Run align from xml
        results = self.runner.invoke(
            align,
            [
                "-s",
                "-o",
                "srt",
                "-o",
                "vtt",
                "-o",
                "TextGrid",
                "-o",
                "eaf",
                "-l",
                "fra",
                os.path.join(self.data_dir, "ej-fra-silence.readalong"),
                os.path.join(self.data_dir, "ej-fra.m4a"),
                str(output),
            ],
        )
        self.assertEqual(results.exit_code, 0)
        self.assertTrue((output / "www/silence.m4a").exists())
        # test silence spans in output xml
        root = load_xml(output / "www/silence.readalong")
        silence_spans = root.xpath("//silence")
        self.assertEqual(len(silence_spans), 3)
        # test audio has correct amount of silence added
        original_audio = AudioSegment.from_file(
            os.path.join(self.data_dir, "ej-fra.m4a")
        )
        new_audio = AudioSegment.from_file(output / "www/silence.m4a", format="m4a")
        self.assertAlmostEqual(
            len(new_audio) - len(original_audio),
            2882,
            msg="silence-added audio file is more than 50ms shorter or longer",
            delta=50,
        )

    def test_bad_silence(self):
        output = self.tempdir / "bad_silence"
        # Run align from bad xml
        results = self.runner.invoke(
            align,
            [
                "-s",
                "-o",
                "srt",
                "-o",
                "vtt",
                "-o",
                "TextGrid",
                "-o",
                "eaf",
                "-l",
                "fra",
                os.path.join(self.data_dir, "ej-fra-silence-bad.readalong"),
                os.path.join(self.data_dir, "ej-fra.m4a"),
                str(output),
            ],
        )
        self.assertNotEqual(results.exit_code, 0)
        self.assertIn("Could not parse all duration attributes", results.output)


if __name__ == "__main__":
    main()
