#!/usr/bin/env python3

from unittest import TestCase, main

from readalongs.text.util import parse_time


class TestMisc(TestCase):
    """ Testing miscellaneous stuff """

    def test_parse_time(self):
        for time_str, time_in_ms in (
            ("1234", 1234000),
            ("12s", 12000),
            ("0.1s", 100),
            (".12s", 120),
            ("123.s", 123000),
            ("123.", 123000),
            (".543", 543),
            ("1234ms", 1234),
            ("  1234  ms  ", 1234),
            ("3.213s", 3213),
        ):
            self.assertEqual(
                parse_time(time_str), time_in_ms, f'error parsing "{time_str}"'
            )

    def test_parse_time_errors(self):
        for err_time_str in ("3.4.5 ms", ".", "", "asdf"):
            with self.assertRaises(
                ValueError,
                msg=f'parsing "{err_time_str}" should have raised ValueError',
            ):
                _ = parse_time(err_time_str)


if __name__ == "__main__":
    main()
