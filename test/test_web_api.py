#!/usr/bin/env python3

import os
from copy import deepcopy
from textwrap import dedent
from unittest import main

from basic_test_case import BasicTestCase
from fastapi.testclient import TestClient
from lxml import etree

from readalongs.text.add_ids_to_xml import add_ids
from readalongs.text.convert_xml import convert_xml
from readalongs.text.tokenize_xml import tokenize_xml
from readalongs.util import get_langs
from readalongs.web_api import XMLRequest, create_grammar, process_xml, web_api_app

API_CLIENT = TestClient(web_api_app)


class TestWebApi(BasicTestCase):
    def setUp(self):
        super().setUp()
        self.basicRequest = {"encoding": "utf-8", "debug": False}

    def test_assemble_from_plain_text(self):
        # Test the assemble endpoint with plain text
        with open(os.path.join(self.data_dir, "ej-fra.txt"), encoding="utf8") as f:
            data = f.read().strip()
        request = deepcopy(self.basicRequest)
        request["text"] = data
        request["text_languages"] = ["fra"]
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
        with open(os.path.join(self.data_dir, "ej-fra.xml"), encoding="utf8") as f:
            data = f.read().strip()
        request = deepcopy(self.basicRequest)
        request["xml"] = data
        request["text_languages"] = ["fra"]
        response = API_CLIENT.post("/api/v1/assemble", json=request)
        self.assertEqual(response.status_code, 200)

    def test_wrapper(self):
        # Test the xml processing wrapper
        with open(os.path.join(self.data_dir, "ej-fra.xml"), encoding="utf8") as f:
            data = f.read().strip()
        xml_request = XMLRequest(xml=data, text_languages=["test"])
        self.assertAlmostEqual(
            data, process_xml(lambda x: x)(xml_request).decode("utf-8")
        )

    def test_bad_xml(self):
        # Test the assemble endpoint with invalid XML
        data = "this is not xml"
        request = deepcopy(self.basicRequest)
        request["xml"] = data
        request["text_languages"] = ["fra"]
        response = API_CLIENT.post("/api/v1/assemble", json=request)
        self.assertEqual(response.status_code, 422)

    def test_create_grammar(self):
        # Test the create grammar function
        with open(os.path.join(self.data_dir, "ej-fra.xml"), encoding="utf8") as f:
            data = f.read().strip()
        parsed = etree.fromstring(bytes(data, encoding="utf8"))
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
        with open(os.path.join(self.data_dir, "ej-fra.txt"), encoding="utf8") as f:
            data = f.read().strip()
        request = deepcopy(self.basicRequest)
        request["text"] = data
        request["text_languages"] = ["test"]
        response = API_CLIENT.post("/api/v1/assemble", json=request)
        self.assertEqual(response.status_code, 422)

    def test_langs(self):
        # Test the langs endpoint
        response = API_CLIENT.get("/api/v1/langs")
        self.assertEqual(response.json()["langs"], get_langs()[1])
        self.assertEqual(set(response.json()["langs"].keys()), set(get_langs()[0]))

    def test_debug(self):
        # Test the assemble endpoint with debug mode on
        with open(os.path.join(self.data_dir, "ej-fra.txt"), encoding="utf8") as f:
            data = f.read().strip()
        request = deepcopy(self.basicRequest)
        request["text"] = data
        request["debug"] = True
        request["text_languages"] = ["fra"]
        response = API_CLIENT.post("/api/v1/assemble", json=request)
        content = response.json()
        self.assertEqual(content["input"], request)
        self.assertGreater(len(content["tokenized"]), 10)
        self.assertGreater(len(content["parsed"]), 10)
        self.assertGreater(len(content["g2ped"]), 10)

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

    hej_verden_textgrid = dedent(
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
    )

    def test_convert_to_TextGrid(self):
        request = {
            "encoding": "utf-8",
            "audio_length": 83.1,
            "output_format": "TextGrid",
            "xml": self.hej_verden_xml,
            "smil": self.hej_verden_smil,
        }
        response = API_CLIENT.post("/api/v1/convert_alignment", json=request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["file_contents"], self.hej_verden_textgrid)

    def test_convert_to_TextGrid_errors(self):
        request = {
            "encoding": "utf-8",
            "audio_length": 83.1,
            "output_format": "TextGrid",
            "xml": "this is not XML",
            "smil": self.hej_verden_smil,
        }
        response = API_CLIENT.post("/api/v1/convert_alignment", json=request)
        self.assertEqual(response.status_code, 422, "Invalid XML should fail.")

        request = {
            "encoding": "utf-8",
            "audio_length": 83.1,
            "output_format": "TextGrid",
            "xml": self.hej_verden_xml,
            "smil": "This is not SMIL",
        }
        response = API_CLIENT.post("/api/v1/convert_alignment", json=request)
        self.assertEqual(response.status_code, 422, "Invalid SMIL should fail.")

        request = {
            "encoding": "utf-8",
            "audio_length": -10.0,
            "output_format": "TextGrid",
            "xml": self.hej_verden_xml,
            "smil": self.hej_verden_smil,
        }
        response = API_CLIENT.post("/api/v1/convert_alignment", json=request)
        self.assertEqual(response.status_code, 422, "Negative duration should fail.")

        request = {
            "encoding": "latin-1",
            "audio_length": 83.1,
            "output_format": "TextGrid",
            "xml": self.hej_verden_xml,
            "smil": self.hej_verden_smil,
        }
        response = API_CLIENT.post("/api/v1/convert_alignment", json=request)
        # Figure out how to exercise this case, but for now latin-1 is not even supported...
        # print(response.status_code, response.json())
        self.assertEqual(
            response.status_code, 422, "only utf-8 is allowed at the moment."
        )
        # Or, once we do support latin-1:
        # self.assertEqual(response.status_code, 400)

    def test_convert_to_eaf(self):
        request = {
            "encoding": "utf-8",
            "audio_length": 83.1,
            "output_format": "eaf",
            "xml": self.hej_verden_xml,
            "smil": self.hej_verden_smil,
        }
        response = API_CLIENT.post("/api/v1/convert_alignment", json=request)
        self.assertEqual(response.status_code, 200)
        self.assertIn("<ANNOTATION_DOCUMENT", response.json()["file_contents"])

    def test_convert_to_bad_format(self):
        request = {
            "encoding": "utf-8",
            "audio_length": 83.1,
            "output_format": "not_a_known_format",
            "xml": self.hej_verden_xml,
            "smil": self.hej_verden_smil,
        }
        response = API_CLIENT.post("/api/v1/convert_alignment", json=request)
        self.assertEqual(response.status_code, 422)

        request = {
            "encoding": "utf-8",
            "audio_length": 83.1,
            # "output_format" just missing
            "xml": self.hej_verden_xml,
            "smil": self.hej_verden_smil,
        }
        response = API_CLIENT.post("/api/v1/convert_alignment", json=request)
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    main()
