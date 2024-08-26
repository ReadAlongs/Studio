#!/usr/bin/env python

"""Test our XML DTD to make sure all valid examples validate and invalid ones don't"""

import os
from os.path import dirname
from unittest import TestCase, main

from lxml import etree

from readalongs.text.util import load_xml

DTDPATH = os.path.join(
    dirname(__file__), "..", "readalongs", "static", "read-along-1.2.dtd"
)

VALID_RAS = """
ej-fra-anchors2.readalong
ej-fra-anchors.readalong
ej-fra-annotated.readalong
ej-fra-converted.readalong
ej-fra-dna.readalong
ej-fra-package.readalong
ej-fra.readalong
ej-fra-silence.readalong
ej-fra-subword.readalong
ej-fra-translated.readalong
fra-prepared.readalong
fra-tokenized.readalong
mixed-langs.g2p.readalong
mixed-langs.readalong
mixed-langs.tokenized.readalong
patrickxtlan.readalong
""".strip().split()
INVALID_RAS = """
ej-fra-invalid.readalong
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
                try:
                    parsed = load_xml(infh)
                    self.assertTrue(
                        self.dtd.validate(parsed), f"{name} does not validate"
                    )
                except etree.ParseError as e:
                    self.fail("Error parsing XML input file %s: %s." % (path, e))

    def test_invalid_inputs(self):
        for name in INVALID_RAS:
            path = os.path.join(dirname(__file__), "data", name)
            with open(path, "rb") as infh:
                try:
                    parsed = load_xml(infh)
                    self.assertFalse(
                        self.dtd.validate(parsed), f"{name} validates but shouldn't"
                    )
                except etree.ParseError as e:
                    self.fail("Error parsing XML input file %s: %s." % (path, e))

    def test_backwards_compatibility(self):
        # the DTD needs to be backwards compatible as long as the major version does not change
        versions = [
            "ras-dtd-1.0.readalong",
            "ras-dtd-1.1.readalong",
            "ras-dtd-1.2.readalong",
        ]
        for name in versions:
            path = os.path.join(dirname(__file__), "data", name.strip())
            # DTD is text, XML is binary... okay
            with open(path, "rb") as infh:
                try:
                    parsed = load_xml(infh)
                    self.assertTrue(
                        self.dtd.validate(parsed), f"{name} does not validate"
                    )
                except etree.ParseError as e:
                    self.fail("Error parsing XML input file %s: %s." % (path, e))

        # test that previous DTD fails current version
        # test DTD 1.0 with format 1.1
        with open(
            os.path.join(
                dirname(__file__), "..", "readalongs", "static", "read-along-1.0.dtd"
            ),
            "rt",
        ) as dtdFile:
            dtd = etree.DTD(dtdFile)
            with open(
                os.path.join(dirname(__file__), "data", versions[1]), "rb"
            ) as rasFile:
                try:
                    parsed = load_xml(rasFile)
                    self.assertFalse(
                        dtd.validate(parsed),
                        f"{versions[1]} validates with 1.0 but shouldn't",
                    )
                except etree.ParseError as e:
                    self.fail("Error parsing XML input file %s: %s." % (rasFile, e))


if __name__ == "__main__":
    main()
