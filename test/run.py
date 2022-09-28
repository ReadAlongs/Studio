#!/usr/bin/env python3

"""
Top-level runner for out test suites

Invoke as
   ./run.py [suite]
where [suite] can be one of:
   all: run everything, by searching the directory for all test suite files
   prod: synonym for all
   dev: run the standard development test suite - this is what we do in CI
   e2e: run the end-to-end tests
   other: run the other tests
"""

import os
import sys
from unittest import TestLoader, TestSuite, TextTestRunner

from test_align_cli import TestAlignCli
from test_anchors import TestAnchors
from test_api import TestAlignApi
from test_audio import TestAudio
from test_concat_ras import TestConcatRas
from test_config import TestConfig
from test_dna_text import TestDNAText
from test_dna_utils import TestDNAUtils
from test_force_align import TestForceAlignment, TestXHTML
from test_g2p_cli import TestG2pCli
from test_make_xml_cli import TestMakeXMLCli
from test_misc import TestMisc
from test_package_urls import TestPackageURLs
from test_silence import TestSilence
from test_temp_file import TestTempFile
from test_tokenize_cli import TestTokenizeCli
from test_tokenize_xml import TestTokenizer
from test_web_api import TestWebApi
from test_smil import TestSmilUtilities

from readalongs.log import LOGGER

loader = TestLoader()

e2e_tests = [
    loader.loadTestsFromTestCase(test) for test in (TestForceAlignment, TestXHTML)
]

api_tests = [
    loader.loadTestsFromTestCase(test) for test in [TestWebApi]
]  # TODO: add some load testing with https://locust.io/

other_tests = [
    loader.loadTestsFromTestCase(test)
    for test in [
        TestAnchors,
        TestConcatRas,
        TestConfig,
        TestDNAText,
        TestDNAUtils,
        TestTokenizer,
        TestTokenizeCli,
        TestTempFile,
        TestMakeXMLCli,
        TestAudio,
        TestAlignCli,
        TestAlignApi,
        TestG2pCli,
        TestMisc,
        TestSilence,
        TestSmilUtilities,
        TestPackageURLs,
        TestWebApi,
    ]
]


def run_tests(suite):
    """Run the specified test suite"""

    if suite == "e2e":
        suite = TestSuite(e2e_tests)
    elif suite == "api":
        suite = TestSuite(api_tests)
    elif suite == "dev":
        suite = TestSuite(other_tests + e2e_tests)
    elif suite in ("prod", "all"):
        suite = loader.discover(os.path.dirname(__file__))
    elif suite == "other":
        suite = TestSuite(other_tests)
    else:
        LOGGER.error(
            "Sorry, you need to select a Test Suite to run, one of: "
            "dev, all (or prod), e2e, other"
        )
        sys.exit(1)

    runner = TextTestRunner(verbosity=3)
    return runner.run(suite)


if __name__ == "__main__":
    try:
        result = run_tests(sys.argv[1])
        if not result.wasSuccessful():
            raise Exception("Some tests failed. Please see log above.")
    except IndexError:
        print("Please specify a test suite to run: i.e. 'dev' or 'all'")
