#!/usr/bin/env python3

"""Test suite for inserting silences into a readalong"""

import os
from unittest import main

from basic_test_case import BasicTestCase
from lxml import etree
from pydub import AudioSegment

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


if __name__ == "__main__":
    main()
