#!/usr/bin/env python3

import os
import sys
from unittest import TestLoader, TestSuite, TextTestRunner

from test_align_cli import TestAlignCli
from test_anchors import TestAnchors
from test_audio import TestAudio
from test_config import TestConfig
from test_dna_text import TestDNAText
from test_dna_utils import TestDNAUtils
from test_force_align import TestForceAlignment, TestXHTML
from test_g2p_cli import TestG2pCli
from test_indices import TestIndices
from test_misc import TestMisc
from test_prepare_cli import TestPrepareCli
from test_temp_file import TestTempFile
from test_tokenize_cli import TestTokenizeCli
from test_tokenize_xml import TestTokenizer

from readalongs.log import LOGGER

loader = TestLoader()

e2e_tests = [
    loader.loadTestsFromTestCase(test) for test in (TestForceAlignment, TestXHTML)
]

indices_tests = [loader.loadTestsFromTestCase(test) for test in [TestIndices]]

other_tests = [
    loader.loadTestsFromTestCase(test)
    for test in [
        TestAnchors,
        TestConfig,
        TestDNAText,
        TestDNAUtils,
        TestTokenizer,
        TestTokenizeCli,
        TestTempFile,
        TestPrepareCli,
        TestAudio,
        TestAlignCli,
        TestG2pCli,
        TestMisc,
    ]
]


def run_tests(suite):
    if suite == "e2e":
        suite = TestSuite(e2e_tests)
    elif suite == "dev":
        suite = TestSuite(indices_tests + other_tests + e2e_tests)
    elif suite == "prod" or suite == "all":
        suite = loader.discover(os.path.dirname(__file__))
    elif suite == "other":
        suite = TestSuite(other_tests)
    else:
        LOGGER.error(
            "Sorry, you need to select a Test Suite to run, like 'dev' or 'prod'"
        )

    runner = TextTestRunner(verbosity=3)
    return runner.run(suite)


if __name__ == "__main__":
    try:
        result = run_tests(sys.argv[1])
        if not result.wasSuccessful():
            raise Exception("Some tests failed. Please see log above.")
    except IndexError:
        print("Please specify a test suite to run: i.e. 'dev' or 'all'")
