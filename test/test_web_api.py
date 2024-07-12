#!/usr/bin/env python

import os
import re
from textwrap import dedent
from unittest import main

from basic_test_case import BasicTestCase

from readalongs._version import READALONG_FILE_FORMAT_VERSION, VERSION
from readalongs.log import LOGGER
from readalongs.text.add_ids_to_xml import add_ids
from readalongs.text.convert_xml import convert_xml
from readalongs.text.tokenize_xml import tokenize_xml
from readalongs.text.util import parse_xml
from readalongs.util import get_langs


class TestWebApi(BasicTestCase):
    _API_CLIENT = None

    @property
    def API_CLIENT(self):
        from fastapi.testclient import TestClient

        from readalongs.web_api import web_api_app

        if TestWebApi._API_CLIENT is None:
            TestWebApi._API_CLIENT = TestClient(web_api_app)
        return TestWebApi._API_CLIENT

    def slurp_data_file(self, filename: str) -> str:
        """Convenience function to slurp a whole file in self.data_dir"""
        with open(os.path.join(self.data_dir, filename), encoding="utf8") as f:
            return (
                f.read()
                .strip()
                .replace("{{format_version}}", READALONG_FILE_FORMAT_VERSION)
                .replace("{{studio_version}}", VERSION)
            )

    def test_assemble_from_plain_text(self):
        # Test the assemble endpoint with plain text
        request = {
            "input": self.slurp_data_file("ej-fra.txt"),
            "type": "text/plain",
            "text_languages": ["fra"],
        }
        response = self.API_CLIENT.post("/api/v1/assemble", json=request)
        self.assertEqual(response.status_code, 200)

    def test_bad_path(self):
        # Test a request to a path that doesn't exist
        response = self.API_CLIENT.get("/pathdoesntexist")
        self.assertEqual(response.status_code, 404)

    def test_bad_method(self):
        # Test a request to a valid path with a bad method
        response = self.API_CLIENT.get("/api/v1/assemble")
        self.assertEqual(response.status_code, 405)

    def test_assemble_from_xml(self):
        # Test the assemble endpoint with XML
        request = {
            "encoding": "utf-8",  # for bwd compat, make sure the encoding is allowed but ignored
            "input": self.slurp_data_file("ej-fra.readalong"),
            "type": "application/readalong+xml",
            "text_languages": ["fra"],
        }
        response = self.API_CLIENT.post("/api/v1/assemble", json=request)
        self.assertEqual(response.status_code, 200)

    def test_illformed_xml(self):
        # Test the assemble endpoint with ill-formed XML
        request = {
            "input": "this is not xml",
            "type": "application/readalong+xml",
            "text_languages": ["fra"],
        }
        response = self.API_CLIENT.post("/api/v1/assemble", json=request)
        self.assertEqual(response.status_code, 422)

    def test_invalid_ras(self):
        # Test the assemble endpoint with invalid RAS XML
        request = {
            "input": self.slurp_data_file("ej-fra-invalid.readalong"),
            "type": "application/readalong+xml",
            "text_languages": ["fra"],
        }
        response = self.API_CLIENT.post("/api/v1/assemble", json=request)
        self.assertEqual(response.status_code, 422)

    def test_create_grammar(self):
        # Test the create grammar function
        parsed = parse_xml(self.slurp_data_file("ej-fra.readalong"))
        tokenized = tokenize_xml(parsed)
        ids_added = add_ids(tokenized)
        g2ped, valid = convert_xml(ids_added)
        from readalongs.web_api import create_grammar

        word_dict, text = create_grammar(g2ped)
        self.assertTrue(valid)
        self.assertEqual(len(word_dict), len(text.split()))
        self.assertEqual(len(word_dict), 99)

    def test_bad_g2p(self):
        # Test the assemble endpoint with invalid g2p languages
        request = {
            "input": "blah blah",
            "type": "text/plain",
            "text_languages": ["test"],
        }
        response = self.API_CLIENT.post("/api/v1/assemble", json=request)
        self.assertIn("No language called", response.json()["detail"])
        self.assertEqual(response.status_code, 422)

    def test_g2p_faiture(self):
        # Test the assemble endpoint where g2p actually fails
        request = {
            "input": "ceci ña",
            "type": "text/plain",
            "text_languages": ["fra"],
        }
        response = self.API_CLIENT.post("/api/v1/assemble", json=request)
        self.assertEqual(response.status_code, 422)
        content = response.json()
        self.assertIn("No valid g2p conversion", content["detail"])

    def test_no_words(self):
        # Test the assemble endpoint with no actual words in the text
        request = {
            "input": ".!",
            "type": "text/plain",
            "text_languages": ["eng"],
        }
        response = self.API_CLIENT.post("/api/v1/assemble", json=request)
        self.assertEqual(response.status_code, 422)
        content = response.json()
        self.assertIn("Could not find any words", content["detail"])

    def test_empty_g2p(self):
        # When the input has numbers of non-g2p-able stuff, let's give the user
        # a 422 with a list of words we can't process
        request = {
            "input": "this 24 is 23:99 a no g2p 1234 test.",
            "type": "text/plain",
            "text_languages": ["eng", "und"],
        }
        response = self.API_CLIENT.post("/api/v1/assemble", json=request)
        self.assertEqual(response.status_code, 422)
        content_log = response.json()["detail"]
        for message_part in ["The output of the g2p process", "24", "23", "is empty"]:
            self.assertIn(message_part, content_log)

    def test_langs(self):
        # Test the langs endpoint
        response = self.API_CLIENT.get("/api/v1/langs")
        codes = [x["code"] for x in response.json()]
        self.assertEqual(set(codes), set(get_langs()[0]))
        self.assertEqual(codes, list(sorted(codes)))
        self.assertEqual(
            dict((x["code"], x["names"]["_"]) for x in response.json()), get_langs()[1]
        )

    def test_logs(self):
        # Test that we see the g2p warnings
        request = {
            "input": "Ceci mais pas ña",
            "type": "text/plain",
            "debug": True,
            "text_languages": ["fra", "und"],
        }
        response = self.API_CLIENT.post("/api/v1/assemble", json=request)
        content = response.json()
        # print("Content", content)
        self.assertIn('Could not g2p "ña" as French', content["log"])

    def test_debug(self):
        # Test the assemble endpoint with debug mode on
        request = {
            "input": self.slurp_data_file("ej-fra.txt"),
            "type": "text/plain",
            "debug": True,
            "text_languages": ["fra"],
        }
        response = self.API_CLIENT.post("/api/v1/assemble", json=request)
        content = response.json()
        self.assertEqual(content["input"], request)
        self.assertGreater(len(content["tokenized"]), 10)
        self.assertGreater(len(content["parsed"]), 10)
        self.assertGreater(len(content["g2ped"]), 10)

        # Test that debug mode is off by default
        request = {
            "input": "Ceci est un test.",
            "type": "text/plain",
            "text_languages": ["fra"],
        }
        response = self.API_CLIENT.post("/api/v1/assemble", json=request)
        content = response.json()
        self.assertIsNone(content["input"])
        self.assertIsNone(content["tokenized"])
        self.assertIsNone(content["parsed"])
        self.assertIsNone(content["g2ped"])

    hej_verden_xml = dedent(
        """<?xml version='1.0' encoding='utf-8'?>
        <read-along version="%s">
    <meta name="generator" content="@readalongs/studio (cli) %s"/>
            <text xml:lang="dan" fallback-langs="und" id="t0">
                <body id="t0b0">
                    <div type="page" id="t0b0d0">
                        <p id="t0b0d0p0">
                            <s id="t0b0d0p0s0">
                                <w id="wé0" time="17.745" dur="40.855" ARPABET="HH EH Y">hej é</w>
                                <w id="wé1" time="58.6" dur="23.59" ARPABET="V Y D EH N">verden à</w>
                            </s>
                        </p>
                    </div>
                </body>
            </text>
        </read-along>
        """
        % (READALONG_FILE_FORMAT_VERSION, VERSION)
    )

    def test_convert_to_TextGrid(self):
        request = {
            "dur": 83.1,
            "ras": self.hej_verden_xml,
        }
        response = self.API_CLIENT.post(
            "/api/v1/convert_alignment/textgrid", json=request
        )
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
        # Test default duration
        request = {
            "ras": self.hej_verden_xml,
        }
        response = self.API_CLIENT.post(
            "/api/v1/convert_alignment/textgrid", json=request
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("aligned.TextGrid", response.headers["content-disposition"])
        self.assertNotIn("xmax = 83.100000", response.text)

    def test_convert_to_eaf(self):
        request = {
            "dur": 83.1,
            "ras": self.hej_verden_xml,
        }
        response = self.API_CLIENT.post("/api/v1/convert_alignment/eaf", json=request)
        self.assertEqual(response.status_code, 200)
        self.assertIn("<ANNOTATION_DOCUMENT", response.text)
        self.assertIn("aligned.eaf", response.headers["content-disposition"])

    def test_convert_to_srt(self):
        request = {
            "dur": 83.1,
            "ras": self.hej_verden_xml,
        }
        response = self.API_CLIENT.post("/api/v1/convert_alignment/srt", json=request)
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

        response = self.API_CLIENT.post(
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
            "dur": 83.1,
            "ras": self.hej_verden_xml,
        }
        response = self.API_CLIENT.post(
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

        response = self.API_CLIENT.post(
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
            "dur": 83.1,
            "ras": "this is not XML",
        }
        response = self.API_CLIENT.post(
            "/api/v1/convert_alignment/textgrid", json=request
        )
        self.assertEqual(response.status_code, 422, "Invalid XML should fail.")

        request = {
            "dur": -10.0,
            "ras": self.hej_verden_xml,
        }
        response = self.API_CLIENT.post(
            "/api/v1/convert_alignment/textgrid", json=request
        )
        self.assertEqual(response.status_code, 422, "Negative duration should fail.")

    def test_cleanup_temp_dir(self):
        """Make sure convert's temporary directory actually gets deleted."""
        request = {
            "dur": 83.1,
            "ras": self.hej_verden_xml,
        }
        with self.assertLogs(LOGGER, "INFO") as log_cm:
            response = self.API_CLIENT.post(
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
        # This is seriously white-box testing... overlapping words
        # will cause an exception deeper in the code after the
        # temporary directory is created. We exercise here catching
        # that exception in a sane way, with a 422 status code, while
        # also making sure the temporary directory gets deleted.
        overlap_xml = dedent(
            """<?xml version='1.0' encoding='utf-8'?>
        <read-along version="%s">
    <meta name="generator" content="@readalongs/studio (cli) %s"/>
            <text xml:lang="dan" fallback-langs="und" id="t0">
                <body id="t0b0">
                    <div type="page" id="t0b0d0">
                        <p id="t0b0d0p0">
                            <s id="t0b0d0p0s0">
                                <w id="wé0" time="17.745" dur="999.999" ARPABET="HH EH Y">hej é</w>
                                <w id="wé1" time="58.6" dur="23.59" ARPABET="V Y D EH N">verden à</w>
                            </s>
                        </p>
                    </div>
                </body>
            </text>
        </read-along>
            """
            % (READALONG_FILE_FORMAT_VERSION, VERSION)
        )
        request = {
            "dur": 83.1,
            "ras": overlap_xml,
        }
        from readalongs.web_api import OutputFormat

        for format_name in OutputFormat:
            with self.assertLogs(LOGGER, "INFO") as log_cm:
                response = self.API_CLIENT.post(
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
            "dur": 83.1,
            "ras": self.hej_verden_xml,
        }
        response = self.API_CLIENT.post(
            "/api/v1/convert_alignment/badformat", json=request
        )
        self.assertEqual(response.status_code, 422)

        request = {
            "dur": 83.1,
            "ras": self.hej_verden_xml,
        }
        response = self.API_CLIENT.post("/api/v1/convert_alignment", json=request)
        self.assertEqual(response.status_code, 404)

        response = self.API_CLIENT.post(
            "/api/v1/convert_alignment/vtt?tier=badtier", json=request
        )
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    main()
