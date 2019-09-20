import os
import sys
from unittest import TestLoader, TextTestRunner, TestSuite
from readalongs.log import LOGGER
# Unit tests

## End-to-End
from test_force_align import TestForceAlignment, TestXHTML

## G2P
from test_context_g2p import TestG2P

## Langs
from test_atj_g2p import TestAtikamekwG2P
from test_crj_g2p import TestSouthEastCreeG2P

## Other tests
from test_tokenize_xml import TestTokenizer

## Eric Joanis created tests
from test_basic_case import TestBasicCase

loader = TestLoader()

e2e_tests = [
    loader.loadTestsFromTestCase(test)
    for test in (TestForceAlignment, TestXHTML)
]

g2p_tests = [
    loader.loadTestsFromTestCase(test)
    for test in [TestG2P]
]

lang_tests = [
    loader.loadTestsFromTestCase(test)
    for test in (TestAtikamekwG2P, TestSouthEastCreeG2P)
]

other_tests = [
    loader.loadTestsFromTestCase(test)
    for test in [TestTokenizer]
]

ej_tests = [
    loader.loadTestsFromTestCase(test)
    for test in [TestBasicCase]
]

def run_tests(suite):
    if suite == 'e2e':
        suite = TestSuite(e2e_tests)
    elif suite == 'g2p':
        suite = TestSuite(g2p_tests)
    elif suite == 'langs':
        suite = TestSuite(lang_tests)
    elif suite == 'dev':
        suite = TestSuite(g2p_tests + other_tests + ej_tests)
    elif suite == 'ej':
        suite = TestSuite(ej_tests)
    elif suite == 'prod':
        suite = loader.discover(os.path.dirname(__file__))
    elif suite == 'other':
        suite = TestSuite(other_tests)
    else:
        LOGGER.error("Sorry, you need to select a Test Suite to run, like 'dev', 'g2p' or 'prod'")

    runner = TextTestRunner(verbosity=3)
    runner.run(suite)

if __name__ == "__main__":
    run_tests(sys.argv[1])
