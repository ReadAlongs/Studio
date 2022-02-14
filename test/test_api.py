#!/usr/bin/env python3

"""
Test suite for the API way to call align
"""

from basic_test_case import BasicTestCase
from pathlib import Path
from sound_swallower_stub import SoundSwallowerStub
from unittest import main

import readalongs.api as api


class TestAlignApi(BasicTestCase):
    """Test suite for the API way to call align()"""

    def test_call_align(self):
        data_dir = Path(self.data_dir)
        temp_dir = Path(self.tempdir)
        langs = ("fra",)  # make sure language can be an iterable, not just a list.
        with SoundSwallowerStub("t0b0d0p0s0w0:920:1520", "t0b0d0p0s1w0:1620:1690"):
            api.align(
                str(data_dir / "ej-fra.txt"),
                str(data_dir / "ej-fra.m4a"),
                str(temp_dir / "output"),
                langs,
                output_formats=["html"],
            )
        expected_output_files = (
            "output.smil",
            "output.xml",
            "output.m4a",
            "index.html",
            "output.html",
        )
        for f in expected_output_files:
            self.assertTrue(
                (temp_dir / "output" / f).exists(),
                f"successful alignment should have created {f}",
            )
        self.assertEqual(list(langs), ["fra"], "Make sure the API call doesn't not modify my variables")


if __name__ == "__main__":
    main()
