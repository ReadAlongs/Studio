#!/usr/bin/env python

"""
Test suite for the API way to call align
"""

import os
import re
from contextlib import redirect_stderr
from io import StringIO
from unittest import main

import click
from basic_test_case import BasicTestCase
from sound_swallower_stub import SoundSwallowerStub

from readalongs import api
from readalongs.log import LOGGER


class TestAlignApi(BasicTestCase):
    """Test suite for the API way to call align()"""

    def test_call_align(self):
        # We deliberately pass pathlib.Path objects as input, to make sure the
        # API accepts them too.
        langs = ("fra",)  # make sure language can be an iterable, not just a list.
        with SoundSwallowerStub("t0b0d0p0s0w0:920:1520", "t0b0d0p0s1w0:1620:1690"):
            with redirect_stderr(StringIO()):
                (status, exception, log) = api.align(
                    self.data_dir / "ej-fra.txt",
                    self.data_dir / "ej-fra.m4a",
                    self.tempdir / "output",
                    langs,
                    output_formats=["html", "TextGrid", "srt"],
                )
        self.assertEqual(status, 0)
        self.assertTrue(exception is None)
        self.assertIn("Words (<w>) not present; tokenizing", log)
        expected_output_files = (
            "www/output.readalong",
            "www/output.m4a",
            "output.TextGrid",
            "output_sentences.srt",
            "output_words.srt",
            "www/index.html",
            "Offline-HTML/output.html",
        )
        for f in expected_output_files:
            self.assertTrue(
                (self.tempdir / "output" / f).exists(),
                f"successful alignment should have created {f}",
            )
        self.assertEqual(
            list(langs),
            ["fra"],
            "Make sure the API call doesn't not modify my variables",
        )

        with redirect_stderr(StringIO()):
            (status, exception, log) = api.align("", "", self.tempdir / "errors")
        self.assertNotEqual(status, 0)
        self.assertFalse(exception is None)

    def test_call_make_xml(self):
        with redirect_stderr(StringIO()):
            (status, exception, log) = api.make_xml(
                self.data_dir / "ej-fra.txt",
                self.tempdir / "prepared.readalong",
                ("fra", "eng"),
            )
        self.assertEqual(status, 0)
        self.assertTrue(exception is None)
        self.assertIn("Wrote ", log)
        with open(self.tempdir / "prepared.readalong") as f:
            xml_text = f.read()
            self.assertIn('xml:lang="fra" fallback-langs="eng,und"', xml_text)

        (status, exception, log) = api.make_xml(
            self.data_dir / "ej-fra.txt",
            self.tempdir / "bad.readalong",
            ("fra", "not-a-lang"),
        )
        self.assertNotEqual(status, 0)
        self.assertTrue(isinstance(exception, click.BadParameter))

        (status, exception, log) = api.make_xml(
            self.data_dir / "file-not-found.txt",
            self.tempdir / "none.readalong",
            ("fra",),
        )
        self.assertNotEqual(status, 0)
        self.assertTrue(isinstance(exception, click.UsageError))

    def test_deprecated_prepare(self):
        with self.assertLogs(LOGGER, level="WARNING") as cm:
            api.prepare(self.data_dir / "ej-fra.txt", os.devnull, ("fra",))
        self.assertIn("deprecated", "\n".join(cm.output))

    sentences_to_convert = [
        [
            api.Token("Bonjöûr,", 0.2, 1.0),
            api.Token(" "),
            api.Token("hello", 1.0, 0.2),
            api.Token("!"),
        ],
        [api.Token("Sentence2", 4.2, 0.2), api.Token("!")],
        [],
        [api.Token("Paragraph2", 4.2, 0.2), api.Token(".")],
        [],
        [],
        [
            api.Token("("),
            api.Token('"'),
            api.Token("Page2", 5.2, 0.2),
            api.Token("."),
            api.Token('"'),
            api.Token(")"),
        ],
    ]

    def test_convert_to_readalong(self):

        readalong = api.convert_prealigned_text_to_readalong(self.sentences_to_convert)
        # print(readalong)

        # Make the reference by calling align with the same text and adjusting
        # things we expect to be different.
        sentences_as_text = "\n".join(
            "".join(token.text for token in sentence)
            for sentence in self.sentences_to_convert
        )
        with open(self.tempdir / "sentences.txt", "w", encoding="utf8") as f:
            f.write(sentences_as_text)
        with redirect_stderr(StringIO()):
            result = api.align(
                self.tempdir / "sentences.txt",
                self.data_dir / "noise.mp3",
                self.tempdir / "output",
                ("und",),
            )
        if result[0] != 0:
            print("align error:", result)
        with open(self.tempdir / "output/www/output.readalong", encoding="utf8") as f:
            align_result = f.read()

        align_result = re.sub(r" ARPABET=\".*?\"", "", align_result)
        align_result = re.sub(
            r'<w (id=".*?") time=".*?" dur=".*?"',
            r'<w time="ttt" dur="ddd" \1',
            align_result,
        )
        readalong = re.sub(r"time=\".*?\"", 'time="ttt"', readalong)
        readalong = re.sub(r"dur=\".*?\"", 'dur="ddd"', readalong)
        self.assertEqual(readalong, align_result)

    def test_convert_to_offline_html(self):
        html, _ = api.convert_prealigned_text_to_offline_html(
            self.sentences_to_convert,
            str(self.data_dir / "noise.mp3"),
            subheader="by Jove!",
        )
        # with open("test.html", "w", encoding="utf8") as f:
        #     f.write(html)
        # print(html)
        self.assertIn("<html", html)
        self.assertIn("<body", html)
        self.assertIn('<meta name="generator" content="@readalongs/studio (cli)', html)
        self.assertIn('<read-along href="data:application/readalong+xml;base64', html)
        self.assertIn('audio="data:audio/', html)
        self.assertIn("<span slot='read-along-header'>", html)
        self.assertIn("<span slot='read-along-subheader'>by Jove!</span>", html)


if __name__ == "__main__":
    main()
