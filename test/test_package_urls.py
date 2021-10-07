import requests
from basic_test_case import BasicTestCase

from readalongs.text.make_package import FONTS_BUNDLE_URL, JS_BUNDLE_URL


class TestPackageURLs(BasicTestCase):
    def test_urls(self):
        for endpoint in [FONTS_BUNDLE_URL, JS_BUNDLE_URL]:
            res = requests.get(endpoint)
            self.assertEqual(res.status_code, 200)
