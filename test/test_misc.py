#!/usr/bin/env python

"""Test suite for misc stuff that don't need their own stand-alone suite"""

import itertools
import os
import zipfile
from unittest import main

import click
from basic_test_case import BasicTestCase
from lxml import etree
from pep440 import is_canonical
from test_dna_utils import segments_from_pairs

from readalongs._version import READALONG_FILE_FORMAT_VERSION, VERSION
from readalongs.align import split_silences
from readalongs.log import LOGGER, capture_logs
from readalongs.text.util import (
    get_attrib_recursive,
    get_lang_attrib,
    get_word_text,
    load_xml,
    load_xml_zip,
    parse_time,
    parse_xml,
    save_txt,
    save_xml,
)
from readalongs.util import JoinerCallbackForClick


class TestMisc(BasicTestCase):
    """Testing miscellaneous stuff"""

    def test_parse_time(self):
        """Test readalongs.text.util.parse_time() with valid inputs"""
        for time_str, time_in_ms in (
            ("1234", 1234000),
            ("12s", 12000),
            ("0.1s", 100),
            (".12s", 120),
            ("123.s", 123000),
            ("123.", 123000),
            (".543", 543),
            ("1234ms", 1234),
            ("  1234  ms  ", 1234),
            ("3.213s", 3213),
            ("1h10m43.123s", 4243123),
            ("2h", 7200000),
            ("2h3", 7203000),
            ("2h3ms", 7200003),
        ):
            self.assertEqual(
                parse_time(time_str), time_in_ms, f'error parsing "{time_str}"'
            )

    def test_parse_time_errors(self):
        """Test readalongs.text.util.parse_time() with invalid inputs"""
        for err_time_str in ("3.4.5 ms", ".", "", "asdf", " 0 h z ", "nm"):
            with self.assertRaises(
                ValueError,
                msg=f'parsing "{err_time_str}" should have raised ValueError',
            ):
                _ = parse_time(err_time_str)

    def test_split_silences(self):
        """Test readalongs.align.split_silences()"""
        dna = segments_from_pairs((1000, 2000), (5000, 5000))
        words = [
            {"id": i, "start": s, "end": e}
            for i, s, e in (
                ("1", 0.100, 0.200),
                ("2", 0.300, 0.900),
                ("3", 2.002, 2.100),
                ("4", 2.200, 4.900),
                ("5", 5.004, 6.000),
            )
        ]
        split_silences(words, 6.100, dna)
        ref = [
            {"id": i, "start": s, "end": e}
            for i, s, e in (
                ("1", 0.050, 0.250),
                ("2", 0.250, 1.000),
                ("3", 2.000, 2.150),
                ("4", 2.150, 4.952),
                ("5", 5.000, 6.050),
            )
        ]
        self.assertEqual(words, ref)

    def test_get_attrib_recursive(self):
        raw_xml = """<read-along version="%s">
    <meta name="generator" content="@readalongs/studio (cli) %s"/>
            <text lang="text">
            <p lang="p1"><s>stuff</s><s lang="p1s2">nonsense</s></p>
            <p><s lang="p2s1">stuff</s><s>nonsense</s></p>
            </text>
            <text>
            <p xml:lang="p3"><s lang="p3s1">stuff</s><s>nonsense<s lang="p3p2c">!</s></s></p>
            </text>
            <text>
            <p><s xml:lang="p4s1" lang="not:xml:lang">stuff</s><s>nonsense<s xml:lang="p4p2c">!</s></s></p>
            </text>
            </read-along>
        """ % (
            READALONG_FILE_FORMAT_VERSION,
            VERSION,
        )
        xml = parse_xml(raw_xml)

        for i, s, lang in zip(
            itertools.count(),
            xml.xpath(".//s"),
            (
                "p1",
                "p1s2",
                "p2s1",
                "text",
                "p3s1",
                None,
                "p3p2c",
                "not:xml:lang",
                None,
                None,
            ),
        ):
            self.assertEqual(
                get_attrib_recursive(s, "lang"),
                lang,
                f"expected lang={lang} for {etree.tostring(s)} (i={i})",
            )

        for i, s, get_lang in zip(
            itertools.count(),
            xml.xpath(".//s"),
            (
                "p1",
                "p1s2",
                "p2s1",
                "text",
                "p3s1",
                "p3",
                "p3p2c",
                "p4s1",
                None,
                "p4p2c",
            ),
        ):
            self.assertEqual(
                get_lang_attrib(s),
                get_lang,
                f"expected get_lang={get_lang} for {etree.tostring(s)} (i={i})",
            )

        for i, s, xml_lang in zip(
            itertools.count(),
            xml.xpath(".//s"),
            (None, None, None, None, "p3", "p3", "p3", "p4s1", None, "p4p2c"),
        ):
            self.assertEqual(
                get_attrib_recursive(s, "xml:lang"),
                xml_lang,
                f"expected xml:lang={xml_lang} for {etree.tostring(s)} (i={i})",
            )

        # Show what xml:lang actually looks like in element.attrib:
        # for p in xml.xpath(".//p"):
        #     print(f"{etree.tostring(p)} has attribs {p.attrib}")
        # Answer: p.attrib={'{http://www.w3.org/XML/1998/namespace}lang': 'p3'}
        # This code is no longer relevant here, but I'm keeping it as
        # documentation, as it's what helped me figure out why I needed
        # element.xpath("./@"+attrib) instead of element.attrib[attrib]
        # get_attrib_recursive() --EJJ Nov 2021

    def test_joiner_callback(self):
        cb = JoinerCallbackForClick(iter("qwer"))  # iterable over four characters
        self.assertEqual(cb(None, None, ["e:r"]), ["e", "r"])
        self.assertEqual(cb(None, None, ["q,w"]), ["q", "w"])
        with self.assertRaises(click.BadParameter):
            cb(None, None, ["q:e", "a,w"])
        self.assertEqual(cb(None, None, ["r:q", "w"]), ["r", "q", "w"])

    def test_get_word_text(self):
        self.assertEqual(
            get_word_text(parse_xml("<w>basicword</w>")),
            "basicword",
        )
        self.assertEqual(
            get_word_text(parse_xml("<w><subw>subwcase</subw></w>")),
            "subwcase",
        )
        self.assertEqual(
            get_word_text(parse_xml("<w><syl>syl1</syl><syl>syl2</syl></w>")),
            "syl1syl2",
        )
        self.assertEqual(
            get_word_text(parse_xml("<w>text<subw>sub</subw>tail</w>")),
            "textsubtail",
        )
        self.assertEqual(
            get_word_text(parse_xml("<w><a>a<b>b</b>c</a>d</w>")),
            "abcd",
        )

    def test_load_xml(self):
        xml_text = '<foo attrib="value">text</foo>'
        foo_file = self.tempdir / "foo.readalong"
        with open(foo_file, "w") as f:
            print(xml_text, file=f)
        self.assertEqual(
            xml_text.encode(encoding="ascii"),
            etree.tostring(load_xml(foo_file)),
        )

    def test_load_xml_errors(self):
        # non-existent file
        with self.assertRaises(OSError):
            load_xml("file-does-not-exist.readalong")

        # invalid XML file
        bad_file = self.tempdir / "bad.readalong"
        with open(bad_file, "w") as f:
            print("This is not XML", file=f)
        with self.assertRaises(etree.ParseError):
            load_xml(bad_file)

        # empty file is also invalid
        with self.assertRaises(etree.ParseError):
            load_xml(os.devnull)

        # make sure we're not vulnerable to XML bombs
        xml_bomb = """<?xml version="1.0"?>
            <!DOCTYPE explode [
                <!ENTITY a "AA">
                <!ENTITY b "&a;&a;">
                <!ENTITY c "&b;&b;">
            ]>
            <explode>&c;&c;</explode>
        """
        explode_file = self.tempdir / "explode.readalong"
        with open(explode_file, "w") as f:
            f.write(xml_bomb)
        self.assertEqual(
            etree.tostring(load_xml(explode_file)),
            b"<explode>&c;&c;</explode>",
        )
        # Would be this if we allowed entity expansion:
        # b'<explode>AAAAAAAAAAAAAAAA</explode>'
        # See https://en.wikipedia.org/wiki/Billion_laughs_attack

    def test_parse_xml(self):
        xml_text = '<foo attrib="value">text</foo>'
        xml = parse_xml(xml_text)
        xml2 = parse_xml(bytes(xml_text, encoding="latin1"))
        self.assertEqual(etree.tostring(xml), etree.tostring(xml2))

        malformed_xml_text = "<foo attrib="
        with self.assertRaises(etree.ParseError):
            xml = parse_xml(malformed_xml_text)

    def test_save_xml(self):
        xml_text = '<foo attrib="value">text</foo>'
        xml = parse_xml(xml_text)
        filename = self.tempdir / "foo.readalong"
        save_xml(filename, xml)
        loaded_xml = load_xml(filename)
        self.assertEqual(etree.tostring(loaded_xml), xml_text.encode(encoding="ascii"))

    def test_save_txt(self):
        xml_text = '<foo attrib="value">text</foo>'
        filename = self.tempdir / "foo.txt"
        save_txt(filename, xml_text)
        loaded_xml = load_xml(filename)
        self.assertEqual(etree.tostring(loaded_xml), xml_text.encode(encoding="ascii"))

    def test_load_xml_zip(self):
        xml_text = '<foo attrib="value">text</foo>'
        with zipfile.ZipFile(self.tempdir / "file.zip", "w") as myzip:
            myzip.writestr("file.readalong", xml_text)
        self.assertEqual(
            etree.tostring(load_xml_zip(self.tempdir / "file.zip", "file.readalong")),
            xml_text.encode(encoding="ascii"),
        )

    def test_capture_logs(self):
        with capture_logs() as captured_logs:
            LOGGER.info("foo bar baz")
        self.assertIn("foo bar baz", captured_logs.getvalue())

    def test_capture_logs_some_more(self):
        with capture_logs() as captured_logs:
            LOGGER.info("this will be captured")
        self.assertIn("this will be captured", captured_logs.getvalue())
        with self.assertLogs():
            LOGGER.info("blah")
        with self.assertLogs() as cm:
            with capture_logs() as captured_logs:
                LOGGER.info("This text does not propagate to root")
            LOGGER.info("This text is included in root")
            self.assertIn("propagate", captured_logs.getvalue())
        self.assertIn("included", "".join(cm.output))
        self.assertNotIn("propagate", "".join(cm.output))

    def test_version_is_pep440_compliant(self):
        self.assertTrue(is_canonical(VERSION))


if __name__ == "__main__":
    main()
