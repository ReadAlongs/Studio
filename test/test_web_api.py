#!/usr/bin/env python

import os
import re
from textwrap import dedent
from unittest import main

from basic_test_case import BasicTestCase
from fastapi.testclient import TestClient
from lxml import etree

from readalongs.log import LOGGER
from readalongs.text.add_ids_to_xml import add_ids
from readalongs.text.convert_xml import convert_xml
from readalongs.text.tokenize_xml import tokenize_xml
from readalongs.util import get_langs
from readalongs.web_api import FormatName, create_grammar, web_api_app

API_CLIENT = TestClient(web_api_app)


class TestWebApi(BasicTestCase):
    def slurp_data_file(self, filename: str) -> str:
        """Convenience function to slurp a whole file in self.data_dir"""
        with open(os.path.join(self.data_dir, filename), encoding="utf8") as f:
            return f.read().strip()

    def test_assemble_from_plain_text(self):
        # Test the assemble endpoint with plain text
        request = {
            "text": self.slurp_data_file("ej-fra.txt"),
            "text_languages": ["fra"],
        }
        response = API_CLIENT.post("/api/v1/assemble", json=request)
        self.assertEqual(response.status_code, 200)

    def test_bad_path(self):
        # Test a request to a path that doesn't exist
        response = API_CLIENT.get("/pathdoesntexist")
        self.assertEqual(response.status_code, 404)

    def test_bad_method(self):
        # Test a request to a valid path with a bad method
        response = API_CLIENT.get("/api/v1/assemble")
        self.assertEqual(response.status_code, 405)

    def test_assemble_from_xml(self):
        # Test the assemble endpoint with XML
        request = {
            "encoding": "utf-8",  # for bwd compat, make sure the encoding is allowed but ignored
            "xml": self.slurp_data_file("ej-fra.xml"),
            "text_languages": ["fra"],
        }
        response = API_CLIENT.post("/api/v1/assemble", json=request)
        self.assertEqual(response.status_code, 200)

    def test_bad_xml(self):
        # Test the assemble endpoint with invalid XML
        request = {
            "xml": "this is not xml",
            "text_languages": ["fra"],
        }
        response = API_CLIENT.post("/api/v1/assemble", json=request)
        self.assertEqual(response.status_code, 422)

    def test_create_grammar(self):
        # Test the create grammar function
        parsed = etree.fromstring(
            bytes(self.slurp_data_file("ej-fra.xml"), encoding="utf8")
        )
        tokenized = tokenize_xml(parsed)
        ids_added = add_ids(tokenized)
        g2ped, valid = convert_xml(ids_added)
        word_dict, fsg, text = create_grammar(g2ped)
        self.assertTrue(valid)
        self.assertIn("Auto-generated JSGF grammar", fsg)
        self.assertEqual(len(word_dict), len(text.split()))
        self.assertEqual(len(word_dict), 99)

    def test_bad_g2p(self):
        # Test the assemble endpoint with invalid g2p languages
        request = {
            "text": "blah blah",
            "text_languages": ["test"],
        }
        with self.assertLogs(LOGGER, "ERROR"):
            response = API_CLIENT.post("/api/v1/assemble", json=request)
        self.assertEqual(response.status_code, 422)

    def test_langs(self):
        # Test the langs endpoint
        response = API_CLIENT.get("/api/v1/langs")
        self.assertEqual(response.json(), get_langs()[1])
        self.assertEqual(set(response.json().keys()), set(get_langs()[0]))

    def test_debug(self):
        # Test the assemble endpoint with debug mode on
        request = {
            "text": self.slurp_data_file("ej-fra.txt"),
            "debug": True,
            "text_languages": ["fra"],
        }
        response = API_CLIENT.post("/api/v1/assemble", json=request)
        content = response.json()
        self.assertEqual(content["input"], request)
        self.assertGreater(len(content["tokenized"]), 10)
        self.assertGreater(len(content["parsed"]), 10)
        self.assertGreater(len(content["g2ped"]), 10)

        # Test that debug mode is off by default
        request = {
            "text": "Ceci est un test.",
            "text_languages": ["fra"],
        }
        response = API_CLIENT.post("/api/v1/assemble", json=request)
        content = response.json()
        self.assertIsNone(content["input"])
        self.assertIsNone(content["tokenized"])
        self.assertIsNone(content["parsed"])
        self.assertIsNone(content["g2ped"])

    hej_verden_xml = dedent(
        """\
        <?xml version='1.0' encoding='utf-8'?>
        <TEI>
            <text xml:lang="dan" fallback-langs="und" id="t0">
                <body id="t0b0">
                    <div type="page" id="t0b0d0">
                        <p id="t0b0d0p0">
                            <s id="t0b0d0p0s0"><w id="wé0" ARPABET="HH EH Y">hej é</w> <w id="wé1" ARPABET="V Y D EH N">verden à</w></s>
                        </p>
                    </div>
                </body>
            </text>
        </TEI>
        """
    )

    hej_verden_smil = dedent(
        """\
        <smil xmlns="http://www.w3.org/ns/SMIL" version="3.0">
            <body>
                <par id="par-wé0">
                    <text src="hej-verden.xml#wé0"/>
                    <audio src="hej-verden.mp3" clipBegin="17.745" clipEnd="58.6"/>
                </par>
                <par id="par-wé1">
                    <text src="hej-verden.xml#wé1"/>
                    <audio src="hej-verden.mp3" clipBegin="58.6" clipEnd="82.19"/>
                </par>
            </body>
        </smil>
        """
    )

    def test_convert_to_TextGrid(self):
        request = {
            "audio_duration": 83.1,
            "xml": self.hej_verden_xml,
            "smil": self.hej_verden_smil,
        }
        response = API_CLIENT.post("/api/v1/convert_alignment/textgrid", json=request)
        self.assertEqual(response.status_code, 200)
        self.assertIn("aligned.TextGrid", response.headers["content-disposition"])
        self.assertEqual(
            response.text,
            dedent(
                """\
                File type = "ooTextFile"
                Object class = "TextGrid"

                xmin = 0.000000
                xmax = 83.100000
                tiers? <exists>
                size = 2
                item []:
                    item [1]:
                        class = "IntervalTier"
                        name = "Sentence"
                        xmin = 0.000000
                        xmax = 83.100000
                        intervals: size = 3
                        intervals [1]:
                            xmin = 0.000000
                            xmax = 17.745000
                            text = ""
                        intervals [2]:
                            xmin = 17.745000
                            xmax = 82.190000
                            text = "hej é verden à"
                        intervals [3]:
                            xmin = 82.190000
                            xmax = 83.100000
                            text = ""
                    item [2]:
                        class = "IntervalTier"
                        name = "Word"
                        xmin = 0.000000
                        xmax = 83.100000
                        intervals: size = 4
                        intervals [1]:
                            xmin = 0.000000
                            xmax = 17.745000
                            text = ""
                        intervals [2]:
                            xmin = 17.745000
                            xmax = 58.600000
                            text = "hej é"
                        intervals [3]:
                            xmin = 58.600000
                            xmax = 82.190000
                            text = "verden à"
                        intervals [4]:
                            xmin = 82.190000
                            xmax = 83.100000
                            text = ""
                """
            ),
        )

    def test_convert_to_eaf(self):
        request = {
            "audio_duration": 83.1,
            "xml": self.hej_verden_xml,
            "smil": self.hej_verden_smil,
        }
        response = API_CLIENT.post("/api/v1/convert_alignment/eaf", json=request)
        self.assertEqual(response.status_code, 200)
        self.assertIn("<ANNOTATION_DOCUMENT", response.text)
        self.assertIn("aligned.eaf", response.headers["content-disposition"])

    def test_convert_to_srt(self):
        request = {
            "audio_duration": 83.1,
            "xml": self.hej_verden_xml,
            "smil": self.hej_verden_smil,
        }
        response = API_CLIENT.post("/api/v1/convert_alignment/srt", json=request)
        self.assertEqual(response.status_code, 200)
        self.assertIn("aligned_sentences.srt", response.headers["content-disposition"])
        self.assertEqual(
            response.text.replace("\r", ""),  # CRLF->LF, in case we're on Windows.
            dedent(
                """\
                1
                00:00:17,745 --> 00:01:22,190
                hej é verden à

                """
            ),
        )

        response = API_CLIENT.post(
            "/api/v1/convert_alignment/srt?tier=word", json=request
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("aligned_words.srt", response.headers["content-disposition"])
        self.assertEqual(
            response.text.replace("\r", ""),  # CRLF->LF, in case we're on Windows.
            dedent(
                """\
                1
                00:00:17,745 --> 00:00:58,600
                hej é

                2
                00:00:58,600 --> 00:01:22,190
                verden à

                """
            ),
        )

    def test_convert_to_vtt(self):
        request = {
            "encoding": "utf-8",  # for bwd compat, make sure the encoding is allowed but ignored
            "audio_duration": 83.1,
            "xml": self.hej_verden_xml,
            "smil": self.hej_verden_smil,
        }
        response = API_CLIENT.post(
            "/api/v1/convert_alignment/vtt?tier=sentence", json=request
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("aligned_sentences.vtt", response.headers["content-disposition"])
        self.assertEqual(
            response.text.replace("\r", ""),  # CRLF->LF, in case we're on Windows.
            dedent(
                """\
                WEBVTT

                00:00:17.745 --> 00:01:22.190
                hej é verden à
                """
            ),
        )

        response = API_CLIENT.post(
            "/api/v1/convert_alignment/vtt?tier=word", json=request
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("aligned_words.vtt", response.headers["content-disposition"])
        self.assertEqual(
            response.text.replace("\r", ""),  # CRLF->LF, in case we're on Windows.
            dedent(
                """\
                WEBVTT

                00:00:17.745 --> 00:00:58.600
                hej é

                00:00:58.600 --> 00:01:22.190
                verden à
                """
            ),
        )

    def test_convert_to_TextGrid_errors(self):
        request = {
            "audio_duration": 83.1,
            "xml": "this is not XML",
            "smil": self.hej_verden_smil,
        }
        response = API_CLIENT.post("/api/v1/convert_alignment/textgrid", json=request)
        self.assertEqual(response.status_code, 422, "Invalid XML should fail.")

        request = {
            "audio_duration": 83.1,
            "xml": self.hej_verden_xml,
            "smil": "This is not SMIL",
        }
        response = API_CLIENT.post("/api/v1/convert_alignment/textgrid", json=request)
        self.assertEqual(response.status_code, 422, "Invalid SMIL should fail.")

        request = {
            "audio_duration": -10.0,
            "xml": self.hej_verden_xml,
            "smil": self.hej_verden_smil,
        }
        response = API_CLIENT.post("/api/v1/convert_alignment/textgrid", json=request)
        self.assertEqual(response.status_code, 422, "Negative duration should fail.")

    def test_cleanup_temp_dir(self):
        """Make sure convert's temporary directory actually gets deleted."""
        request = {
            "audio_duration": 83.1,
            "xml": self.hej_verden_xml,
            "smil": self.hej_verden_smil,
        }
        with self.assertLogs(LOGGER, "INFO") as log_cm:
            response = API_CLIENT.post(
                "/api/v1/convert_alignment/textgrid", json=request
            )
        self.assertEqual(response.status_code, 200)
        # print(log_cm.output)
        match = re.search(
            "Temporary directory: (.*)($|\r|\n)", "\n".join(log_cm.output)
        )
        self.assertIsNotNone(match)
        self.assertFalse(os.path.isdir(match[1]))

    def test_cleanup_even_if_error(self):
        # This is seriously white-box testing... this XML has IDs that don't
        # match those in the SMIL file, which will cause an exception deeper in
        # the code after the temporary directory is created. We exercise here
        # catching that exception in a sane way, with a 422 status code, while
        # also making sure the temporary directory gets deleted.
        mismatch_xml = dedent(
            """\
            <?xml version='1.0' encoding='utf-8'?>
            <TEI>
                <text xml:lang="dan" fallback-langs="und" id="t0">
                    <body id="t0b0">
                        <div type="page" id="t0b0d0">
                            <p id="t0b0d0p0">
                                <s id="t0b0d0p0s0"><w id="mismatch0" ARPABET="HH EH Y">hej é</w> <w id="mismatch1" ARPABET="V Y D EH N">verden à</w></s>
                            </p>
                        </div>
                    </body>
                </text>
            </TEI>
            """
        )
        request = {
            "audio_duration": 83.1,
            "xml": mismatch_xml,
            "smil": self.hej_verden_smil,
        }
        for format_name in FormatName:
            with self.assertLogs(LOGGER, "INFO") as log_cm:
                response = API_CLIENT.post(
                    f"/api/v1/convert_alignment/{format_name.value}", json=request
                )
            self.assertEqual(response.status_code, 422)
            # print(log_cm.output)
            match = re.search(
                "Temporary directory: (.*)($|\r|\n)", "\n".join(log_cm.output)
            )
            self.assertIsNotNone(match)
            self.assertFalse(os.path.isdir(match[1]))

    def test_convert_to_bad_format(self):
        request = {
            "audio_duration": 83.1,
            "xml": self.hej_verden_xml,
            "smil": self.hej_verden_smil,
        }
        response = API_CLIENT.post("/api/v1/convert_alignment/badformat", json=request)
        self.assertEqual(response.status_code, 422)

        request = {
            "audio_duration": 83.1,
            "xml": self.hej_verden_xml,
            "smil": self.hej_verden_smil,
        }
        response = API_CLIENT.post("/api/v1/convert_alignment", json=request)
        self.assertEqual(response.status_code, 404)

        response = API_CLIENT.post(
            "/api/v1/convert_alignment/vtt?tier=badtier", json=request
        )
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    main()
