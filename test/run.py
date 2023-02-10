#!/usr/bin/env python

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
import re
import sys
from unittest import TestLoader, TestSuite, TextTestRunner

from test_align_cli import TestAlignCli
from test_anchors import TestAnchors
from test_api import TestAlignApi
from test_audio import TestAudio
from test_config import TestConfig
from test_dna_text import TestDNAText
from test_dna_utils import TestDNAUtils
from test_dtd import TestDTD
from test_force_align import TestForceAlignment, TestXHTML
from test_g2p_cli import TestG2pCli
from test_make_xml_cli import TestMakeXMLCli
from test_misc import TestMisc
from test_package_urls import TestPackageURLs
from test_silence import TestSilence
from test_smil import TestSmilUtilities
from test_temp_file import TestTempFile
from test_tokenize_cli import TestTokenizeCli
from test_tokenize_xml import TestTokenizer
from test_web_api import TestWebApi

from readalongs.log import LOGGER

LOADER = TestLoader()

e2e_tests = [
    LOADER.loadTestsFromTestCase(test) for test in (TestForceAlignment, TestXHTML)
]

api_tests = [
    LOADER.loadTestsFromTestCase(test) for test in [TestWebApi]
]  # TODO: add some load testing with https://locust.io/

other_tests = [
    LOADER.loadTestsFromTestCase(test)
    for test in [
        TestAnchors,
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
        TestDTD,
    ]
]


def list_tests(suite: TestSuite):
    for subsuite in suite:
        for match in re.finditer(r"tests=\[([^][]+)\]>", str(subsuite)):
            yield from match[1].split(", ")


def describe_suite(suite: TestSuite):
    full_suite = LOADER.discover(os.path.dirname(__file__))
    full_list = list(list_tests(full_suite))
    requested_list = list(list_tests(suite))
    requested_set = set(requested_list)
    print("Test suite includes:", *sorted(requested_list), sep="\n"),
    print(
        "\nTest suite excludes:",
        *sorted(test for test in full_list if test not in requested_set),
        sep="\n"
    )


def run_tests(suite: str, describe: bool = False) -> bool:
    """Run the specified test suite.

    Args:
        suite: one of "all", "dev", etc specifying which suite to run
        describe: if True, list all the test cases instead of running them.

    Returns: True iff success
    """

    if suite == "e2e":
        test_suite = TestSuite(e2e_tests)
    elif suite == "api":
        test_suite = TestSuite(api_tests)
    elif suite == "dev":
        test_suite = TestSuite(other_tests + e2e_tests)
    elif suite in ("prod", "all"):
        test_suite = LOADER.discover(os.path.dirname(__file__))
    elif suite == "other":
        test_suite = TestSuite(other_tests)
    else:
        LOGGER.error(
            "Sorry, you need to select a Test Suite to run, one of: "
            "dev, all (or prod), e2e, other"
        )
        return False

    if describe:
        describe_suite(test_suite)
        return True
    else:
        runner = TextTestRunner(verbosity=3)
        return runner.run(test_suite).wasSuccessful()


if __name__ == "__main__":
    describe = "--describe" in sys.argv
    if describe:
        sys.argv.remove("--describe")

    try:
        result = run_tests(sys.argv[1], describe)
        if not result:
            LOGGER.error("Some tests failed. Please see log above.")
            sys.exit(1)
    except IndexError:
        LOGGER.error("Please specify a test suite to run: i.e. 'dev' or 'all'")
        sys.exit(1)
