#!/usr/bin/env python

from unittest import main

import requests
from basic_test_case import BasicTestCase, silence_logs

from readalongs.text.make_package import (
    FONTS_BUNDLE_URL,
    JS_BUNDLE_URL,
    fetch_bundle_file,
)


class TestPackageURLs(BasicTestCase):
    def test_urls(self):
        """Test the links that our package functionality depends on"""
        for endpoint in [FONTS_BUNDLE_URL, JS_BUNDLE_URL]:
            try:
                res = requests.get(endpoint, timeout=10)
                self.assertEqual(res.status_code, 200)
            except requests.exceptions.ReadTimeout:
                # Don't fail on a timeout, sometimes unpkg can be slow
                pass

    def test_fetch_bundles_fallback(self):
        """Test graceful exit when the URLs are not accessible."""
        # Pretend the previous attempt failed: we'll get the file from disk
        status, contents, js_bundle_version = fetch_bundle_file(
            JS_BUNDLE_URL, "bundle.js", "SomeError"
        )
        # print(status, len(contents))
        self.assertEqual(status, "SomeError")
        self.assertEqual(js_bundle_version, "unknown")
        ref_length = len(contents)

        # Try with a bad URL
        bad_url = JS_BUNDLE_URL.replace("unpkg.com", "not-a-server.zzz")
        # print(bad_url)
        with silence_logs():
            status, contents, _ = fetch_bundle_file(bad_url, "bundle.js", None)
        # print(status, len(contents))
        self.assertNotEqual(status, 200)
        self.assertIsInstance(status, str)
        self.assertEqual(ref_length, len(contents))


if __name__ == "__main__":
    main()
