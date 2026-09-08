#!/usr/bin/env python

"""Test suite for loading the config.json configuration file for readalongs align"""

import io
import os
import sys
from contextlib import redirect_stderr

from lxml import etree
from pytest import fixture, main, raises

from readalongs.text.add_elements_to_xml import add_images, add_supplementary_xml
from readalongs.text.util import load_xml


class TestConfig:
    """Test suite for loading the config.json configuration file for readalongs align"""

    readalong: etree

    @fixture(autouse=True, scope="class")
    @classmethod
    def _pytest_setup(cls) -> None:
        data_dir = os.path.join(os.path.dirname(__file__), "data")
        cls.readalong = load_xml(os.path.join(data_dir, "ej-fra.readalong"))

    def test_image(self) -> None:
        """Test images are added correctly"""
        with raises(KeyError):
            new_xml = add_images(self.readalong, {})
        new_xml = add_images(self.readalong, {"images": {"0": "test.jpg"}})
        assert len(new_xml.xpath("//graphic")) == 1
        with raises(TypeError):
            new_xml = add_images(self.readalong, {"images": [{"0": "test.jpg"}]})
        with raises(ValueError):
            new_xml = add_images(self.readalong, {"images": {"a": "test.jpg"}})
        with raises(IndexError):
            new_xml = add_images(
                self.readalong, {"images": {"0": "test.jpg", "999": "out_of_range.jpg"}}
            )

    def test_arbitrary_xml(self):
        """Test arbitrary xml is added correctly"""
        with raises(KeyError):
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
        assert len(new_xml.xpath("//test")) == 1

        # bad xml raises lxml.etree.XMLSyntaxError
        with raises(etree.XMLSyntaxError):
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
        assert "No elements found at //bloop" in log_output.getvalue()
        assert len(new_xml.xpath("//shmoop")) == 0


if __name__ == "__main__":
    main(sys.argv)
