#!/usr/bin/env python

"""
Top-level runner for out test suites

Invoke as
   ./run_tests.py [suite]
where [suite] can be one of:
   all: run everything, by searching the directory for all test suite files
   dev: now a synonym for all (used to exclude some expensive tests)
   api: run only the API-related tests
   cli: run only the CLI-related tests
   e2e: run the end-to-end tests
"""

import argparse
import io
import sys
from contextlib import redirect_stdout
from pathlib import Path
from typing import List, Optional

import pytest

from readalongs.log import LOGGER

SUITES = {
    "all": [],  # relies on discovery to collect all tests
    "dev": [],  # synonym for all
    "api": ["test_web_api", "test_api"],
    "cli": ["test_align_cli", "test_g2p_cli", "test_make_xml_cli", "test_tokenize_cli"],
    "e2e": ["test_force_align", "test_align_cli"],
}

# TODO: add some load testing with https://locust.io/


class PytestCollectorPlugin:
    def __init__(self):
        self.collected = []

    def pytest_collection_modifyitems(self, session, config, items):
        self.collected.extend([item.nodeid for item in items])


def list_tests(suite: List[str]):
    plugin = PytestCollectorPlugin()
    pytest_args = ["--collect-only", *suite, "-q"]
    if sys.version_info >= (3, 10):
        with redirect_stdout(io.StringIO()):  # broken with py 3.8/3.9...
            pytest.main(pytest_args, plugins=[plugin])
    else:
        pytest.main(pytest_args, plugins=[plugin])
    # print("===========\n", o.getvalue(), "\n================")
    return plugin.collected


def describe_suite(suite_name, suite_filenames: List[str]):
    full_list = list_tests([])
    requested_list = list_tests(suite_filenames)
    requested_set = set(requested_list)
    print(f"Test suite '{suite_name}' includes:", *sorted(requested_list), sep="\n")
    print(
        f"\nTest suite '{suite_name}' excludes:",
        *sorted(test for test in full_list if test not in requested_set),
        sep="\n",
    )
    print(
        "\nTotal test cases",
        f"found: {len(full_list)};",
        f"included: {len(requested_list)};",
        f"excluded: {len(full_list) - len(requested_list)}.",
    )


def run_tests(suite: Optional[str], describe=False, verbose=False) -> bool:
    """Run the specified test suite.

    Args:
        suite: one of SUITES, "dev" if the empty string
        describe: if True, list all the test cases instead of running them.

    Returns: Bool: True iff success
    """

    if not suite:
        LOGGER.info("No test suite specified, defaulting to dev, which runs all tests.")
        suite = "dev"

    if suite not in SUITES:
        LOGGER.error("Please specify a test suite to run among: " + ", ".join(SUITES))
        return False

    test_suite = SUITES[suite]
    tests_dir = Path(__file__).parent / "tests"
    test_suite_filenames = [str(tests_dir / f"{file}.py") for file in test_suite]
    if describe:
        describe_suite(suite, test_suite_filenames)
        return True
    else:
        pytest_args = ["--verbose"] if verbose else []
        return 0 == pytest.main([*test_suite_filenames, *pytest_args])


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ReadAlongs/Studio test suites.")
    parser.add_argument("--verbose", "-v", action="store_true", help="verbose output")
    parser.add_argument(
        "--describe", action="store_true", help="describe the selected test suite"
    )
    parser.add_argument(
        "suite",
        nargs="?",
        help="the test suite to run [dev]",
        choices=SUITES,
    )
    args = parser.parse_args()
    result = run_tests(args.suite, args.describe, args.verbose)
    if not result:
        sys.exit(1)


if __name__ == "__main__":
    main()
