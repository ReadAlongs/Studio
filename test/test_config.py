#!/usr/bin/env python3
import os
from unittest import TestCase, main

from lxml import etree

from readalongs.text.add_elements_to_xml import add_images, add_supplementary_xml


class TestConfig(TestCase):
    @classmethod
    def setUpClass(cls):
        data_dir = os.path.join(os.path.dirname(__file__), "data")
        cls.xml = etree.parse(os.path.join(data_dir, "ej-fra.xml")).getroot()

    def test_image(self):
        """Test images are added correctly"""
        with self.assertRaises(KeyError):
            new_xml = add_images(self.xml, {})
        new_xml = add_images(self.xml, {"images": {"0": "test.jpg"}})
        self.assertTrue(len(new_xml.xpath("//graphic")) == 1)

    def test_arbitrary_xml(self):
        """Test arbitrary xml is added correctly"""
        with self.assertRaises(KeyError):
            new_xml = add_supplementary_xml(self.xml, {})
        new_xml = add_supplementary_xml(
            self.xml,
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


if __name__ == "__main__":
    main()
