#!/usr/bin/env python3

from textwrap import dedent
from unittest import main

from basic_test_case import BasicTestCase
from lxml import etree

from readalongs.text.concat_ras import concat_ras


class TestConcatRas(BasicTestCase):
    def test_basic_call(self):
        words = [
            {"id": "w1", "start": 0.01, "end": 0.75},
            {"id": "w2", "start": 0.8, "end": 1.04},
        ]
        xml_text = dedent(
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
        my_readalong = {
            "xml": etree.fromstring(xml_text),
            "words": words,
            "audio_duration": 2,
        }

        (cat_xml, cat_words, total_duration) = concat_ras([my_readalong] * 3)

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
                        <div type="page" id="r2t0b0d0">
                            <p id="r2t0b0d0p0">
                                <s id="r2t0b0d0p0s0">
                                    <w id="r2w1" ARPABET="HH EH Y">hej</w>
                                    <w id="r2w2" ARPABET="V Y D EH N">verden</w>
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

        self.assertEqual(cat_xml, etree.fromstring(cat_xml_ref))

        self.assertEqual(
            cat_words,
            [
                {"id": "r0w1", "start": 0.01, "end": 0.75},
                {"id": "r0w2", "start": 0.8, "end": 1.04},
                {"id": "r1w1", "start": 0.01 + 2, "end": 0.75 + 2},
                {"id": "r1w2", "start": 0.8 + 2, "end": 1.04 + 2},
                {"id": "r2w1", "start": 0.01 + 4, "end": 0.75 + 4},
                {"id": "r2w2", "start": 0.8 + 4, "end": 1.04 + 4},
            ],
        )

        self.assertEqual(total_duration, 6.0)


if __name__ == "__main__":
    main()
