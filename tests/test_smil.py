#!/usr/bin/env python

"""
Unit test suite for the smil writing and parsing utilities
"""

from textwrap import dedent
from unittest import main

from basic_test_case import BasicTestCase

from readalongs.text.make_smil import make_smil, parse_smil


class TestSmilUtilities(BasicTestCase):
    """Unit test suite for the smil writing and parsing utilities"""

    def setUp(self):
        super().setUp()
        self.words = [
            {"id": "w1", "start": 0.01, "end": 0.75},
            {"id": "w2", "start": 0.8, "end": 1.04},
            # Make one of the ID's a utf-8 character, to test for handling that correctly.
            {"id": "wé3", "start": 1.2, "end": 1.33},
        ]
        self.smil = dedent(
            """\
            <smil xmlns="http://www.w3.org/ns/SMIL" version="3.0">
                <body>
                    <par id="par-w1">
                        <text src="my_text_path#w1"/>
                        <audio src="my_audio_path" clipBegin="0.01" clipEnd="0.75"/>
                    </par>
                    <par id="par-w2">
                        <text src="my_text_path#w2"/>
                        <audio src="my_audio_path" clipBegin="0.8" clipEnd="1.04"/>
                    </par>
                    <par id="par-wé3">
                        <text src="my_text_path#wé3"/>
                        <audio src="my_audio_path" clipBegin="1.2" clipEnd="1.33"/>
                    </par>
                </body>
            </smil>
            """
        )

    def test_make_smil(self):
        text_path = "my_text_path"
        audio_path = "my_audio_path"
        smil = make_smil(text_path, audio_path, self.words)
        self.assertEqual(smil, self.smil)

    def test_parse_smil(self):
        words = parse_smil(self.smil)
        self.assertEqual(words, self.words)

    def test_parse_bad_smil(self):
        with self.assertRaises(ValueError):
            _ = parse_smil("this is not XML")

        missing_id = dedent(
            """\
            <smil xmlns="http://www.w3.org/ns/SMIL" version="3.0">
                <body>
                    <par id="par-w1">
                        <text src="my_text_path"/>
                        <audio src="my_audio_path" clipBegin="0.01" clipEnd="0.75"/>
                    </par>
                </body>
            </smil>
            """
        )
        with self.assertRaises(ValueError):
            _ = parse_smil(missing_id)

        missing_clip_end = dedent(
            """\
            <smil xmlns="http://www.w3.org/ns/SMIL" version="3.0">
                <body>
                    <par id="par-w1">
                        <text src="my_text_path#w1"/>
                        <audio src="my_audio_path" clipBegin="0.01"/>
                    </par>
                </body>
            </smil>
            """
        )
        with self.assertRaises(ValueError):
            _ = parse_smil(missing_clip_end)

        bad_float = dedent(
            """\
            <smil xmlns="http://www.w3.org/ns/SMIL" version="3.0">
                <body>
                    <par id="par-w1">
                        <text src="my_text_path#w1"/>
                        <audio src="my_audio_path" clipBegin="a.bc" clipEnd="2.34"/>
                    </par>
                </body>
            </smil>
            """
        )
        with self.assertRaises(ValueError):
            _ = parse_smil(bad_float)


if __name__ == "__main__":
    main()
