#!/usr/bin/env python

from unittest import main

import requests
from basic_test_case import BasicTestCase

from readalongs.text.make_package import FONTS_BUNDLE_URL, JS_BUNDLE_URL


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


if __name__ == "__main__":
    main()
