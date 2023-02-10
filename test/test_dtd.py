#!/usr/bin/env python

"""Test our XML DTD to make sure all valid examples validate and invalid ones don't"""

import os
from os.path import dirname
from unittest import TestCase, main

from lxml import etree

DTDPATH = os.path.join(
    dirname(__file__), "..", "readalongs", "static", "read-along-0.2.dtd"
)

VALID_RAS = """
ej-fra-anchors2.ras
ej-fra-anchors.ras
ej-fra-converted.ras
ej-fra-dna.ras
ej-fra-package.ras
ej-fra.ras
ej-fra-silence.ras
ej-fra-subword.ras
ej-fra-translated.ras
fra-prepared.ras
fra-tokenized.ras
mixed-langs.g2p.ras
mixed-langs.ras
mixed-langs.tokenized.ras
patrickxtlan.ras
""".strip().split()
INVALID_RAS = """
ej-fra-invalid.ras
""".strip().split()


class TestDTD(TestCase):
    """Test the XML DTD"""

    def setUp(self):
        with open(DTDPATH, "rt") as infh:
            self.dtd = etree.DTD(infh)

    def test_valid_inputs(self):
        for name in VALID_RAS:
            path = os.path.join(dirname(__file__), "data", name)
            # DTD is text, XML is binary... okay
            with open(path, "rb") as infh:
                parsed = etree.parse(infh)
                self.assertTrue(self.dtd.validate(parsed), f"{name} does not validate")

    def test_invalid_inputs(self):
        for name in INVALID_RAS:
            path = os.path.join(dirname(__file__), "data", name)
            with open(path, "rb") as infh:
                parsed = etree.parse(infh)
                self.assertFalse(
                    self.dtd.validate(parsed), f"{name} validates but shouldn't"
                )


if __name__ == "__main__":
    main()
