#!/usr/bin/env python

"""
Test suite for the API way to call align
"""

import os
from unittest import main

import click
from basic_test_case import BasicTestCase
from sound_swallower_stub import SoundSwallowerStub

import readalongs.api as api
from readalongs.log import LOGGER


class TestAlignApi(BasicTestCase):
    """Test suite for the API way to call align()"""

    def test_call_align(self):
        # We deliberately pass pathlib.Path objects as input, to make sure the
        # API accepts them too.
        langs = ("fra",)  # make sure language can be an iterable, not just a list.
        with SoundSwallowerStub("t0b0d0p0s0w0:920:1520", "t0b0d0p0s1w0:1620:1690"):
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

        (status, exception, log) = api.align("", "", self.tempdir / "errors")
        self.assertNotEqual(status, 0)
        self.assertFalse(exception is None)

    def test_call_make_xml(self):
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


if __name__ == "__main__":
    main()
