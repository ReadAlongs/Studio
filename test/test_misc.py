#!/usr/bin/env python3

"""Test suite for misc stuff that don't need their own stand-alone suite"""

from unittest import TestCase, main

from test_dna_utils import segments_from_pairs

from readalongs.align import split_silences
from readalongs.text.util import parse_time


class TestMisc(TestCase):
    """Testing miscellaneous stuff"""

    def test_parse_time(self):
        """Test readalongs.text.util.parse_time() with valid inputs"""
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
            ("1h10m43.123s", 4243123),
            ("2h", 7200000),
            ("2h3", 7203000),
            ("2h3ms", 7200003),
        ):
            self.assertEqual(
                parse_time(time_str), time_in_ms, f'error parsing "{time_str}"'
            )

    def test_parse_time_errors(self):
        """Test readalongs.text.util.parse_time() with invalid inputs"""
        for err_time_str in ("3.4.5 ms", ".", "", "asdf", " 0 h z ", "nm"):
            with self.assertRaises(
                ValueError,
                msg=f'parsing "{err_time_str}" should have raised ValueError',
            ):
                _ = parse_time(err_time_str)

    def test_split_silences(self):
        """Test readalongs.align.split_silences()"""
        dna = segments_from_pairs((1000, 2000), (5000, 5000))
        words = [
            {"id": i, "start": s, "end": e}
            for i, s, e in (
                ("1", 0.100, 0.200),
                ("2", 0.300, 0.900),
                ("3", 2.002, 2.100),
                ("4", 2.200, 4.900),
                ("5", 5.004, 6.000),
            )
        ]
        split_silences(words, 6.100, dna)
        ref = [
            {"id": i, "start": s, "end": e}
            for i, s, e in (
                ("1", 0.050, 0.250),
                ("2", 0.250, 1.000),
                ("3", 2.000, 2.150),
                ("4", 2.150, 4.952),
                ("5", 5.000, 6.050),
            )
        ]
        self.assertEqual(words, ref)


if __name__ == "__main__":
    main()
