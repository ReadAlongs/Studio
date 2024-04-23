#!/usr/bin/env python

"""Test suite for loading the config.json configuration file for readalongs align"""

import io
import os
from contextlib import redirect_stderr
from unittest import TestCase, main

from lxml import etree

from readalongs.text.add_elements_to_xml import add_images, add_supplementary_xml
from readalongs.text.util import load_xml


class TestConfig(TestCase):
    """Test suite for loading the config.json configuration file for readalongs align"""

    @classmethod
    def setUpClass(cls):
        data_dir = os.path.join(os.path.dirname(__file__), "data")
        cls.readalong = load_xml(os.path.join(data_dir, "ej-fra.readalong"))

    def test_image(self):
        """Test images are added correctly"""
        with self.assertRaises(KeyError):
            new_xml = add_images(self.readalong, {})
        new_xml = add_images(self.readalong, {"images": {"0": "test.jpg"}})
        self.assertTrue(len(new_xml.xpath("//graphic")) == 1)
        with self.assertRaises(TypeError):
            new_xml = add_images(self.readalong, {"images": [{"0": "test.jpg"}]})
        with self.assertRaises(ValueError):
            new_xml = add_images(self.readalong, {"images": {"a": "test.jpg"}})
        with self.assertRaises(IndexError):
            new_xml = add_images(
                self.readalong, {"images": {"0": "test.jpg", "999": "out_of_range.jpg"}}
            )

    def test_arbitrary_xml(self):
        """Test arbitrary xml is added correctly"""
        with self.assertRaises(KeyError):
            new_xml = add_supplementary_xml(self.readalong, {})
        new_xml = add_supplementary_xml(
            self.readalong,
            {
                "xml": [
                    {
                        "xpath": "//div[1]",
                        "value": "<test>here is some test text</test>",
                    }
                ]
            },
        )
        self.assertTrue(len(new_xml.xpath("//test")) == 1)

        # bad xml raises lxml.etree.XMLSyntaxError
        with self.assertRaises(etree.XMLSyntaxError):
            new_xml = add_supplementary_xml(
                self.readalong, {"xml": [{"xpath": "//div[1]", "value": "bloop"}]}
            )

        # if xpath isn't valid, log warning
        with redirect_stderr(io.StringIO()) as log_output:
            new_xml = add_supplementary_xml(
                self.readalong,
                {
                    "xml": [
                        {
                            "xpath": "//bloop",
                            "value": "<shmoop>here is some test text</shmoop>",
                        }
                    ]
                },
            )
        self.assertIn("No elements found at //bloop", log_output.getvalue())
        self.assertTrue(len(new_xml.xpath("//shmoop")) == 0)


if __name__ == "__main__":
    main()
