#!/usr/bin/env python

"""Test suite for DNA segment manupulation methods"""

from unittest import TestCase, main

from readalongs.dna_utils import (
    calculate_adjustment,
    correct_adjustments,
    dna_union,
    segment_intersection,
    sort_and_join_dna_segments,
)


def segments_from_pairs(*pairs):
    """Pseudo constructor for a list of segment dicts with begin and end

    segments should really be represented using an @dataclass, but that's for
    a future refactoring task. For now, this gives me something easy to use for
    unit testing.
    """
    return list({"begin": b, "end": e} for b, e in pairs)


class TestDNAUtils(TestCase):
    """Test suite for dna segment manipulation methods in dna_utils.py"""

    def test_sort_and_join_dna_segments(self):
        """Make sure sorting and joining DNA segments works."""
        self.assertEqual(
            sort_and_join_dna_segments(segments_from_pairs((1000, 1100), (1500, 2100))),
            segments_from_pairs((1000, 1100), (1500, 2100)),
        )
        self.assertEqual(
            sort_and_join_dna_segments(segments_from_pairs((1500, 2100), (1000, 1100))),
            segments_from_pairs((1000, 1100), (1500, 2100)),
        )
        self.assertEqual(
            sort_and_join_dna_segments(
                segments_from_pairs(
                    (2, 3), (11, 14), (23, 25), (1, 4), (12, 13), (24, 26)
                )
            ),
            segments_from_pairs((1, 4), (11, 14), (23, 26)),
        )

    def test_adjustment_calculation(self):
        """Try adjusting alignments of re-built audio"""
        self.assertEqual(
            calculate_adjustment(1000, [{"begin": 1000, "end": 1100}]), 100
        )
        self.assertEqual(calculate_adjustment(900, [{"begin": 1000, "end": 1100}]), 0)
        self.assertEqual(
            calculate_adjustment(1000, [{"begin": 1000, "end": 1100}]), 100
        )
        self.assertEqual(calculate_adjustment(900, [{"begin": 1000, "end": 1100}]), 0)
        self.assertEqual(
            calculate_adjustment(2000, [{"begin": 1000, "end": 1100}]), 100
        )
        # Function only accepts args in ms, so 1.0 and 2.0 are the same as 1 and 2 ms
        self.assertEqual(
            calculate_adjustment(
                1.0, [{"begin": 1000, "end": 1100}, {"begin": 1500, "end": 1700}]
            ),
            0,
        )
        self.assertEqual(
            calculate_adjustment(
                2.0, [{"begin": 1000, "end": 1100}, {"begin": 1500, "end": 2100}]
            ),
            0,
        )
        # When there are multiple dna segments, the timestamp to adjust has to
        # shift with the adjustment, e.g.:
        #    if DNA= [1000,2000)+[4000,5000)
        #    then 0-999 -> 0-999, 1000-2999 -> 2000-3999, and 3000+ -> 5000+
        for value, adjustment in [
            (0, 0),
            (999, 0),
            (1000, 1000),
            (2999, 1000),
            (3000, 2000),
            (4000, 2000),
        ]:
            self.assertEqual(
                calculate_adjustment(
                    value, [{"begin": 1000, "end": 2000}, {"begin": 4000, "end": 5000}]
                ),
                adjustment,
                f"DNA removal adjustment for t={value}ms should have been {adjustment}ms",
            )

    def test_adjustment_correction(self):
        """Try correcting adjusted alignments of re-built audio"""
        self.assertEqual(
            correct_adjustments(950, 1125, [{"begin": 1000, "end": 1100}]), (950, 1000)
        )
        self.assertEqual(
            correct_adjustments(975, 1150, [{"begin": 1000, "end": 1100}]), (1100, 1150)
        )
        # Function only accepts args in ms
        self.assertNotEqual(
            correct_adjustments(0.950, 1.125, [{"begin": 1000, "end": 1100}]),
            (950, 1000),
        )
        self.assertNotEqual(
            correct_adjustments(0.975, 1.150, [{"begin": 1000, "end": 1100}]),
            (1100, 1150),
        )

    def test_segment_intersection(self):
        """Unit testing of segment_intersection()"""
        self.assertEqual(segment_intersection([], []), [])
        self.assertEqual(segment_intersection(segments_from_pairs((1, 3)), []), [])
        self.assertEqual(segment_intersection([], segments_from_pairs((1, 3))), [])
        self.assertEqual(
            segment_intersection(
                segments_from_pairs(
                    (15, 16), (30, 40), (42, 48), (50, 60), (65, 66), (84, 89), (90, 91)
                ),
                segments_from_pairs(
                    (20, 21), (23, 24), (45, 50), (55, 57), (60, 70), (80, 85), (93, 94)
                ),
            ),
            segments_from_pairs(
                (45, 48), (50, 50), (55, 57), (60, 60), (65, 66), (84, 85)
            ),
        )
        self.assertEqual(
            segment_intersection(
                segments_from_pairs((10, 30)), segments_from_pairs((19, 19))
            ),
            segments_from_pairs((19, 19)),
        )
        self.assertEqual(
            segment_intersection(
                segments_from_pairs((1610, 1620)), segments_from_pairs((1620, 1620))
            ),
            segments_from_pairs((1620, 1620)),
        )
        self.assertEqual(
            segment_intersection(
                segments_from_pairs((1610, 1620)),
                segments_from_pairs((1610, 1610), (1620, 1620)),
            ),
            segments_from_pairs((1610, 1610), (1620, 1620)),
        )

    def test_dna_union(self):
        """Unit testing of dna_union()"""
        self.assertEqual(
            dna_union(1000, 2000, 3000, [{"begin": 1100, "end": 1200}]),
            segments_from_pairs((0, 1000), (1100, 1200), (2000, 3000)),
        )
        self.assertEqual(
            dna_union(None, 2000, 3000, [{"begin": 1100, "end": 1200}]),
            segments_from_pairs((1100, 1200), (2000, 3000)),
        )
        self.assertEqual(
            dna_union(1000, None, 3000, [{"begin": 1100, "end": 1200}]),
            segments_from_pairs((0, 1000), (1100, 1200)),
        )
        self.assertEqual(
            dna_union(
                1000,
                2000,
                3000,
                segments_from_pairs(
                    (400, 500), (900, 1100), (1200, 1300), (1900, 2100), (2500, 2600)
                ),
            ),
            segments_from_pairs((0, 1100), (1200, 1300), (1900, 3000)),
        )


if __name__ == "__main__":
    main()
