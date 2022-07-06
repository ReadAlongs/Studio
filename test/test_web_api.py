#!/usr/bin/env python3

import os
from copy import deepcopy
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
        self.assertEqual(response.status_code, 400)

    def test_langs(self):
        # Test the langs endpoint
        response = API_CLIENT.get("/api/v1/langs")
        self.assertEqual(response.json(), get_langs()[1])
        self.assertEqual(set(response.json().keys()), set(get_langs()[0]))

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


if __name__ == "__main__":
    main()
