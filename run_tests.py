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

import argparse
import os
import re
import sys
from unittest import TestLoader, TestSuite, TextTestRunner

from readalongs.log import LOGGER
from tests.test_align_cli import TestAlignCli
from tests.test_anchors import TestAnchors
from tests.test_api import TestAlignApi
from tests.test_audio import TestAudio
from tests.test_config import TestConfig
from tests.test_dna_text import TestDNAText
from tests.test_dna_utils import TestDNAUtils
from tests.test_dtd import TestDTD
from tests.test_force_align import TestForceAlignment, TestXHTML
from tests.test_g2p_cli import TestG2pCli
from tests.test_make_xml_cli import TestMakeXMLCli
from tests.test_misc import TestMisc
from tests.test_package_urls import TestPackageURLs
from tests.test_silence import TestSilence
from tests.test_smil import TestSmilUtilities
from tests.test_temp_file import TestTempFile
from tests.test_tokenize_cli import TestTokenizeCli
from tests.test_tokenize_xml import TestTokenizer
from tests.test_web_api import TestWebApi

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
    print("Test suite includes:", *sorted(requested_list), sep="\n")
    print(
        "\nTest suite excludes:",
        *sorted(test for test in full_list if test not in requested_set),
        sep="\n",
    )


SUITES = ["all", "dev", "e2e", "prod", "api", "other"]


def run_tests(suite: str, describe: bool = False, verbosity=3) -> bool:
    """Run the specified test suite.

    Args:
        suite: one of SUITES, "dev" if the empty string
        describe: if True, list all the test cases instead of running them.

    Returns: True iff success
    """

    if not suite:
        LOGGER.info("No test suite specified, defaulting to dev.")
        suite = "dev"

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
            "Sorry, you need to select a Test Suite to run, one of: " + " ".join(SUITES)
        )
        return False

    if describe:
        describe_suite(test_suite)
        return True
    else:
        runner = TextTestRunner(verbosity=verbosity)
        success = runner.run(test_suite).wasSuccessful()
        if not success:
            LOGGER.error("Some tests failed. Please see log above.")
        return success


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run ReadAlongs/Studio test suites.")
    parser.add_argument("--quiet", "-q", action="store_true", help="reduce output")
    parser.add_argument(
        "--describe", action="store_true", help="describe the selected test suite"
    )
    parser.add_argument(
        "suite",
        nargs="?",
        default="dev",
        help="the test suite to run [dev]",
        choices=SUITES,
    )
    args = parser.parse_args()
    result = run_tests(args.suite, args.describe, 1 if args.quiet else 3)
    if not result:
        sys.exit(1)
