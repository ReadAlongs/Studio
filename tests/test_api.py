#!/usr/bin/env python

"""
Test suite for the API way to call align
"""

import re
import sys
from contextlib import redirect_stderr
from io import StringIO

import click
from pytest import main

from readalongs import api
from readalongs.log import LOGGER
from tests.basic_test_case import BasicTestCase
from tests.sound_swallower_stub import SoundSwallowerStub


class TestAlignApi(BasicTestCase):
    """Test suite for the API way to call align()"""

    def test_call_align(self):
        # We deliberately pass pathlib.Path objects as input, to make sure the
        # API accepts them too.
        langs = ("fra",)  # make sure language can be an iterable, not just a list.
        with SoundSwallowerStub("t0b0d0p0s0w0:920:1520", "t0b0d0p0s1w0:1620:1690"):
            with redirect_stderr(StringIO()):
                (status, exception, log) = api.align(
                    self.data_dir / "ej-fra.txt",
                    self.data_dir / "ej-fra.m4a",
                    self.tempdir / "output",
                    langs,
                    output_formats=["html", "TextGrid", "srt"],
                )
        assert status == 0
        assert exception is None
        assert "Words (<w>) not present; tokenizing" in log
        expected_output_files = (
            "www/output.readalong",
            "www/output.m4a",
            "output.TextGrid",
            "output_sentences.srt",
            "output_words.srt",
            "www/index.html",
            "Offline-HTML/output.html",
        )
        for f in expected_output_files:
            assert (self.tempdir / "output" / f).exists(), (
                f"successful alignment should have created {f}",
            )
        assert list(langs) == ["fra"], (
            "Make sure the API call doesn't not modify my variables",
        )

        with redirect_stderr(StringIO()):
            (status, exception, log) = api.align("", "", self.tempdir / "errors")
        assert status != 0
        assert exception is not None

    def test_call_make_xml(self):
        with redirect_stderr(StringIO()):
            (status, exception, log) = api.make_xml(
                self.data_dir / "ej-fra.txt",
                self.tempdir / "prepared.readalong",
                ("fra", "eng"),
            )
        assert status == 0
        assert exception is None
        assert "Wrote " in log
        with open(self.tempdir / "prepared.readalong") as f:
            xml_text = f.read()
            assert 'xml:lang="fra" fallback-langs="eng,und"' in xml_text

        (status, exception, log) = api.make_xml(
            self.data_dir / "ej-fra.txt",
            self.tempdir / "bad.readalong",
            ("fra", "not-a-lang"),
        )
        assert status != 0
        assert isinstance(exception, click.BadParameter)

        (status, exception, log) = api.make_xml(
            self.data_dir / "file-not-found.txt",
            self.tempdir / "none.readalong",
            ("fra",),
        )
        assert status != 0
        assert isinstance(exception, click.UsageError)

    def test_deprecated_prepare(self, caplog):
        caplog.set_level("WARNING", logger=LOGGER.name)
        api.prepare(self.data_dir / "ej-fra.txt", self.tempdir / "foo", ("fra",))
        assert "deprecated" in caplog.text

    sentences_to_convert = [
        [
            api.Token("Bonjöûr,", 0.2, 1.0),
            api.Token(" "),
            api.Token("hello", 1.0, 0.2),
            api.Token("!"),
        ],
        [api.Token("Sentence2", 4.2, 0.2), api.Token("!")],
        [],
        [api.Token("Paragraph2", 4.2, 0.2), api.Token(".")],
        [],
        [],
        [
            api.Token("("),
            api.Token('"'),
            api.Token("Page2", 5.2, 0.2),
            api.Token("."),
            api.Token('"'),
            api.Token(")"),
        ],
    ]

    def test_convert_to_readalong(self):

        readalong = api.convert_prealigned_text_to_readalong(self.sentences_to_convert)
        # print(readalong)

        # Make the reference by calling align with the same text and adjusting
        # things we expect to be different.
        sentences_as_text = "\n".join(
            "".join(token.text for token in sentence)
            for sentence in self.sentences_to_convert
        )
        with open(self.tempdir / "sentences.txt", "w", encoding="utf8") as f:
            f.write(sentences_as_text)
        with redirect_stderr(StringIO()):
            result = api.align(
                self.tempdir / "sentences.txt",
                self.data_dir / "noise.mp3",
                self.tempdir / "output",
                ("und",),
            )
        if result[0] != 0:
            print("align error:", result)
        with open(self.tempdir / "output/www/output.readalong", encoding="utf8") as f:
            align_result = f.read()

        align_result = re.sub(r" ARPABET=\".*?\"", "", align_result)
        align_result = re.sub(
            r'<w (id=".*?") time=".*?" dur=".*?"',
            r'<w time="ttt" dur="ddd" \1',
            align_result,
        )
        readalong = re.sub(r"time=\".*?\"", 'time="ttt"', readalong)
        readalong = re.sub(r"dur=\".*?\"", 'dur="ddd"', readalong)
        assert readalong == align_result

    def test_convert_to_offline_html(self):
        import readalongs.text.make_package as make_package

        # We want to exercise caching of the bundles, but first we need to uncache
        # them in case some other test case already cached them.
        make_package.fonts_bundle_contents = None
        make_package.js_bundle_contents = None

        html, _ = api.convert_prealigned_text_to_offline_html(
            self.sentences_to_convert,
            str(self.data_dir / "noise.mp3"),
            subheader="by Jove!",
        )
        # with open("test.html", "w", encoding="utf8") as f:
        #     f.write(html)
        # print(html)
        assert "<html" in html
        assert "<body" in html
        assert '<meta name="generator" content="@readalongs/studio (cli)' in html
        assert 'href="data:application/readalong+xml;base64' in html
        assert 'audio="data:audio/' in html
        assert "<span slot='read-along-header'>" in html
        assert "<span slot='read-along-subheader'>by Jove!</span>" in html

        # Make sure the bundles got cached
        assert make_package.fonts_bundle_contents is not None
        assert make_package.js_bundle_contents is not None

        # And convert again, this time it's going to use the cached bundles.
        html2, _ = api.convert_prealigned_text_to_offline_html(
            self.sentences_to_convert,
            str(self.data_dir / "noise.mp3"),
            subheader="by Jove!",
        )
        assert html == html2

        # Once more, this time pretend we could not fetch the first bundle
        make_package.fonts_bundle_contents = None
        make_package.js_bundle_contents = None
        make_package._prev_js_status_code = "TIMEOUT"
        make_package._prev_fonts_status_code = None
        _, _ = api.convert_prealigned_text_to_offline_html(
            self.sentences_to_convert,
            str(self.data_dir / "noise.mp3"),
            subheader="by Jove!",
        )
        assert make_package._prev_fonts_status_code == "TIMEOUT"
        assert make_package.fonts_bundle_contents is not None
        assert make_package.js_bundle_contents is not None

    def test_extract_version_from_url(self):
        from readalongs.text.make_package import extract_version_from_url

        # Test that the version is extracted correctly from the URL
        url = "https://unpkg.com/@readalongs/web-component@1.2.3/dist/bundle.js"
        version = extract_version_from_url(url)
        assert version == "1.2.3"

        # Test with a URL that doesn't contain a version
        url = "https://unpkg.com/@readalongs/web-component/dist/bundle.js"
        version = extract_version_from_url(url)
        assert version == "unknown"


if __name__ == "__main__":
    main(sys.argv)
