import os
from copy import deepcopy
from unittest import main

from basic_test_case import BasicTestCase
from fastapi.testclient import TestClient
from lxml import etree

from readalongs.text.add_ids_to_xml import add_ids
from readalongs.text.convert_xml import convert_xml
from readalongs.text.tokenize_xml import tokenize_xml
from readalongs.web_api import XMLRequest, create_grammar, process_xml, web_api_app

API_CLIENT = TestClient(web_api_app)


class TestWebApi(BasicTestCase):
    def setUp(self):
        super().setUp()
        self.basicRequest = {"encoding": "utf-8", "debug": False}

    def test_prepare_from_plain_text(self):
        with open(os.path.join(self.data_dir, "ej-fra.txt")) as f:
            data = f.read().strip()
        request = deepcopy(self.basicRequest)
        request["text"] = data
        request["text_languages"] = ["fra"]
        response = API_CLIENT.post("/api/v1/prepare", json=request)
        self.assertEqual(response.status_code, 200)

    def test_bad_path(self):
        response = API_CLIENT.get("/pathdoesntexist")
        self.assertEqual(response.status_code, 404)

    def test_bad_method(self):
        response = API_CLIENT.get("/api/v1/prepare")
        self.assertEqual(response.status_code, 405)

    def test_prepare_from_xml(self):
        with open(os.path.join(self.data_dir, "ej-fra.xml")) as f:
            data = f.read().strip()
        request = deepcopy(self.basicRequest)
        request["xml"] = data
        request["text_languages"] = ["fra"]
        response = API_CLIENT.post("/api/v1/prepare", json=request)
        self.assertEqual(response.status_code, 200)

    def test_wrapper(self):
        with open(os.path.join(self.data_dir, "ej-fra.xml")) as f:
            data = f.read().strip()
        xml_request = XMLRequest(xml=data, text_languages=["test"])
        self.assertAlmostEqual(
            data, process_xml(lambda x: x)(xml_request).decode("utf-8")
        )

    def test_bad_xml(self):
        data = "this is not xml"
        request = deepcopy(self.basicRequest)
        request["xml"] = data
        request["text_languages"] = ["fra"]
        response = API_CLIENT.post("/api/v1/prepare", json=request)
        self.assertEqual(response.status_code, 422)

    def test_create_grammar(self):
        with open(os.path.join(self.data_dir, "ej-fra.xml")) as f:
            data = f.read().strip()
        parsed = etree.fromstring(bytes(data, encoding="utf8"))
        tokenized = tokenize_xml(parsed)
        ids_added = add_ids(tokenized)
        g2ped, valid = convert_xml(ids_added)
        dict, fsg, text = create_grammar(g2ped)
        self.assertTrue(valid)
        self.assertIn("Auto-generated JSGF grammar", fsg)
        self.assertEqual(len(dict), len(text.split()))
        self.assertEqual(len(dict), 99)

    def test_bad_g2p(self):
        with open(os.path.join(self.data_dir, "ej-fra.txt")) as f:
            data = f.read().strip()
        request = deepcopy(self.basicRequest)
        request["text"] = data
        request["text_languages"] = ["test"]
        response = API_CLIENT.post("/api/v1/prepare", json=request)
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    main()
