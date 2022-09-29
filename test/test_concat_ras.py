#!/usr/bin/env python3

from textwrap import dedent
from unittest import main

from basic_test_case import BasicTestCase
from lxml import etree

from readalongs.text.concat_ras import concat_ras


def same_text(s1, s2) -> bool:
    """Return whether s1 and s2 have the same text, consider None as empty str"""
    if s1 is None or s1 == "":
        return s2 is None or s2 == ""
    return s2 is not None and s1.strip() == s2.strip()


def cmp_ignore_whitespace(xml1: etree.ElementTree, xml2: etree.ElementTree) -> bool:
    """Returns true iff xml1 and xml2 are the same except for whitespace"""
    if (
        xml1.tag != xml2.tag
        or not same_text(xml1.text, xml2.text)
        or not same_text(xml1.tail, xml2.tail)
        or xml1.attrib != xml2.attrib
        or len(xml1) != len(xml2)
    ):
        return False
    for child1, child2 in zip(xml1, xml2):
        if not cmp_ignore_whitespace(child1, child2):
            return False
    return True


class TestConcatRas(BasicTestCase):
    xml_dan = dedent(
        """\
        <?xml version='1.0'?>
        <TEI>
            <text xml:lang="dan" fallback-langs="und" id="t0">
                <body id="t0b0">
                    <div type="page" id="t0b0d0">
                        <p id="t0b0d0p0">
                            <s id="t0b0d0p0s0">
                                <w id="w1" ARPABET="HH EH Y">hej</w>
                                <w id="w2" ARPABET="V Y D EH N">verden</w>
                            </s>
                        </p>
                    </div>
                </body>
            </text>
        </TEI>
        """
    )

    words_dan = [
        {"id": "w1", "start": 0.01, "end": 0.75},
        {"id": "w2", "start": 0.8, "end": 1.04},
    ]

    smil_dan = dedent(
        """\
        <smil xmlns="http://www.w3.org/ns/SMIL" version="3.0">
            <body>
                <par id="par-w1">
                    <text src="hej-verden.xml#w1"/>
                    <audio src="hej-verden.mp3" clipBegin="0.01" clipEnd="0.75"/>
                </par>
                <par id="par-w2">
                    <text src="hej-verden.xml#w2"/>
                    <audio src="hej-verden.mp3" clipBegin="0.80" clipEnd="1.04"/>
                </par>
            </body>
        </smil>
        """
    )

    xml_fra = dedent(
        """\
        <?xml version='1.0'?>
        <TEI>
            <text xml:lang="fra" fallback-langs="eng,und" id="t0">
                <body id="t0b0">
                    <div type="page" id="t0b0d0">
                        <p id="t0b0d0p0">
                            <s id="t0b0d0p0s0">
                                <w id="w1" ARPABET="B AO N ZH UW ZH">bonjour</w>
                                <w id="w2" ARPABET="L AH">le</w>
                            </s>
                        </p>
                    </div>
                    <div type="page" id="t0b0d1">
                        <p id="t0b0d1p0">
                            <s id="t0b0d1p0s0">
                                <w id="w3" ARPABET="M AO N D">monde</w>
                            </s>
                        </p>
                    </div>
                </body>
            </text>
        </TEI>
        """
    )

    words_fra = [
        {"id": "w1", "start": 0.01, "end": 0.75},
        {"id": "w2", "start": 0.8, "end": 1.04},
        {"id": "w3", "start": 1.11, "end": 2.34},
    ]

    smil_fra = dedent(
        """\
        <smil xmlns="http://www.w3.org/ns/SMIL" version="3.0">
            <body>
                <par id="par-w1">
                    <text src="yo-fra.xml#w1"/>
                    <audio src="yo-fra.mp3" clipBegin="0.01" clipEnd="0.75"/>
                </par>
                <par id="par-w2">
                    <text src="yo-fra.xml#w2"/>
                    <audio src="yo-fra.mp3" clipBegin="0.80" clipEnd="1.04"/>
                </par>
            </body>
        </smil>
        """
    )

    def test_basic_call(self):
        ra_dan = {
            "xml": etree.fromstring(self.xml_dan),
            "words": self.words_dan,
            "audio_duration": 2,
        }
        ra_fra = {
            "xml": etree.fromstring(self.xml_fra),
            "words": self.words_fra,
            "audio_duration": 3,
        }

        (cat_xml, cat_words, total_duration) = concat_ras([ra_dan, ra_fra, ra_dan])

        # save_xml(self.tempdir / "cat.xml", cat_xml)
        # os.system(f"cat {self.tempdir/'cat.xml'}")

        cat_xml_ref = dedent(
            """\
            <?xml version='1.0'?>
            <TEI>
                <text xml:lang="dan" fallback-langs="und" id="t0">
                    <body id="t0b0">
                        <div type="page" id="r0t0b0d0">
                            <p id="r0t0b0d0p0">
                                <s id="r0t0b0d0p0s0">
                                    <w id="r0w1" ARPABET="HH EH Y">hej</w>
                                    <w id="r0w2" ARPABET="V Y D EH N">verden</w>
                                </s>
                            </p>
                        </div>
                        <div type="page" lang="fra" fallback-langs="eng,und" id="r1t0b0d0">
                            <p id="r1t0b0d0p0">
                                <s id="r1t0b0d0p0s0">
                                    <w id="r1w1" ARPABET="B AO N ZH UW ZH">bonjour</w>
                                    <w id="r1w2" ARPABET="L AH">le</w>
                                </s>
                            </p>
                        </div>
                        <div type="page" lang="fra" fallback-langs="eng,und" id="r1t0b0d1">
                            <p id="r1t0b0d1p0">
                                <s id="r1t0b0d1p0s0">
                                    <w id="r1w3" ARPABET="M AO N D">monde</w>
                                </s>
                            </p>
                        </div>
                        <div type="page" id="r2t0b0d0">
                            <p id="r2t0b0d0p0">
                                <s id="r2t0b0d0p0s0">
                                    <w id="r2w1" ARPABET="HH EH Y">hej</w>
                                    <w id="r2w2" ARPABET="V Y D EH N">verden</w>
                                </s>
                            </p>
                        </div>
                    </body>
                </text>
            </TEI>
            """
        )

        self.assertTrue(cmp_ignore_whitespace(cat_xml, etree.fromstring(cat_xml_ref)))

        self.assertEqual(
            cat_words,
            [
                {"id": "r0w1", "start": 0.01, "end": 0.75},
                {"id": "r0w2", "start": 0.8, "end": 1.04},
                {"id": "r1w1", "start": 0.01 + 2, "end": 0.75 + 2},
                {"id": "r1w2", "start": 0.8 + 2, "end": 1.04 + 2},
                {"id": "r1w3", "start": 1.11 + 2, "end": 2.34 + 2},
                {"id": "r2w1", "start": 0.01 + 5, "end": 0.75 + 5},
                {"id": "r2w2", "start": 0.8 + 5, "end": 1.04 + 5},
            ],
        )

        self.assertEqual(total_duration, 7.0)

    def test_wrapped_call(self):
        pass


if __name__ == "__main__":
    main()
