#!/usr/bin/env python3

import os
import tempfile
from pathlib import Path
from shutil import rmtree
from subprocess import run
from unittest import TestCase, main

from readalongs.audio_utils import (
    calculate_adjustment,
    correct_adjustments,
    dna_intersection,
    extract_section,
    join_section,
    mute_section,
    read_audio_from_file,
    remove_section,
    sort_and_join_dna_segments,
    write_audio_to_file,
)
from readalongs.log import LOGGER


class TestAudio(TestCase):
    def setUp(self):
        self.data_path = os.path.join(os.path.dirname(__file__), "data")
        self.audio_segment = read_audio_from_file(
            os.path.join(self.data_path, "audio_sample.ogg")
        )
        self.noisy_segment = read_audio_from_file(
            os.path.join(self.data_path, "noise_at_1500.mp3")
        )
        # Use a TemporaryDirectory object for temp outputs, so they get cleaned
        # automatically cleaned even in case of errors or aborted runs.
        self.tempdirobj = tempfile.TemporaryDirectory(
            prefix="test_audio_tmpdir", dir="."
        )
        self.tempdir = self.tempdirobj.name

    def tearDown(self):
        self.tempdirobj.cleanup()

    def align(self, input_text_path, input_audio_path, output_path, flags):
        args = [
            "readalongs",
            "align",
            input_text_path,
            input_audio_path,
            output_path,
        ] + flags
        LOGGER.info(
            f"Aligning {input_text_path} and {input_audio_path}, outputting to {output_path}"
        )
        return run(args, capture_output=True)

    def test_mute_section(self):
        """ Should mute section of audio
        """
        muted_segment = mute_section(self.audio_segment, 1000, 2000)
        muted_section = muted_segment[1000:2000]
        self.assertLessEqual(muted_section.max, 1)

    def test_remove_section(self):
        """ Should remove section of audio
        """
        removed_segment = remove_section(self.audio_segment, 1000, 2000)
        self.assertNotEqual(len(removed_segment), len(self.audio_segment))
        self.assertEqual(len(removed_segment), len(self.audio_segment) - 1000)

    def test_rejoin_section(self):
        """ Should rejoin removed/muted sections
        """
        removed_section = self.audio_segment[1000:2000]
        removed_segment = remove_section(self.audio_segment, 1000, 2000)
        rejoined_segment = join_section(removed_segment, removed_section, 1000)
        self.assertEqual(len(rejoined_segment), len(self.audio_segment))

    def test_align_sample(self):
        """ Sanity check that test audio should align
        """
        # Align
        input_text_path = os.path.join(self.data_path, "audio_sample.txt")
        input_audio_path = os.path.join(self.data_path, "audio_sample.ogg")
        flags = ["-i", "-l", "eng"]
        output_path = os.path.join(self.tempdir, "output")
        log = self.align(input_text_path, input_audio_path, output_path, flags)
        LOGGER.info(str(log))
        # Check Result
        smilpath = Path(output_path)
        smil_files = smilpath.glob("*.smil")
        self.assertTrue(next(smil_files, False), "No *.smil files found")
        self.assertFalse("error" in str(log).lower())

    def test_align_removed(self):
        """ Try aligning section with removed audio
        """
        # Process Audio
        removed_segment = remove_section(self.noisy_segment, 1500, 2500)
        audio_output_path = os.path.join(self.tempdir, "removed_sample.mp3")
        removed_segment.export(audio_output_path)
        # Align
        input_text_path = os.path.join(self.data_path, "audio_sample.txt")
        input_audio_path = audio_output_path
        flags = ["-i", "-l", "eng"]
        output_path = os.path.join(self.tempdir, "output_removed")
        log = self.align(input_text_path, input_audio_path, output_path, flags)
        LOGGER.info(str(log))
        # Check Result
        smilpath = Path(output_path)
        smil_files = smilpath.glob("*.smil")
        self.assertTrue(next(smil_files, False), "No *.smil files found")
        self.assertFalse("error" in str(log).lower())

    def test_align_muted(self):
        """ Try aligning section with muted audio
        """
        # Process Audio
        muted_segment = mute_section(self.noisy_segment, 1500, 2500)
        audio_output_path = os.path.join(self.tempdir, "muted_sample.mp3")
        muted_segment.export(audio_output_path)
        # Align
        input_text_path = os.path.join(self.data_path, "audio_sample.txt")
        input_audio_path = audio_output_path
        flags = ["-i", "-l", "eng", "-b"]
        output_path = os.path.join(self.tempdir, "output_muted")
        log = self.align(input_text_path, input_audio_path, output_path, flags)
        LOGGER.info(str(log))
        # Check Result
        smilpath = Path(output_path)
        smil_files = smilpath.glob("*.smil")
        self.assertTrue(next(smil_files, False), "No *.smil files found")
        self.assertFalse("error" in str(log).lower())

    def test_sort_and_join_dna_segments(self):
        """ Make sure sorting and joining DNA segments works. """
        self.assertEqual(
            sort_and_join_dna_segments(
                [{"begin": 1000, "end": 1100}, {"begin": 1500, "end": 2100}]
            ),
            [{"begin": 1000, "end": 1100}, {"begin": 1500, "end": 2100}],
        )
        self.assertEqual(
            sort_and_join_dna_segments(
                [{"begin": 1500, "end": 2100}, {"begin": 1000, "end": 1100}]
            ),
            [{"begin": 1000, "end": 1100}, {"begin": 1500, "end": 2100}],
        )
        self.assertEqual(
            sort_and_join_dna_segments(
                [
                    {"begin": 2, "end": 3},
                    {"begin": 11, "end": 14},
                    {"begin": 23, "end": 25},
                    {"begin": 1, "end": 4},
                    {"begin": 12, "end": 13},
                    {"begin": 24, "end": 26},
                ]
            ),
            [
                {"begin": 1, "end": 4},
                {"begin": 11, "end": 14},
                {"begin": 23, "end": 26},
            ],
        )

    def test_adjustment_calculation(self):
        """ Try adjusting alignments of re-built audio
        """
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
        # When there are multiple dna segments, the timestamp to adjust has to shift with the adjustment
        # e.g.:
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
        """ Try correcting adjusted alignments of re-built audio
        """
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

    def test_dna_intersection(self):
        self.assertEqual(
            dna_intersection(1000, 2000, 3000, [{"begin": 1100, "end": 1200}]),
            [
                {"begin": 0, "end": 1000},
                {"begin": 1100, "end": 1200},
                {"begin": 2000, "end": 3000},
            ],
        )
        self.assertEqual(
            dna_intersection(None, 2000, 3000, [{"begin": 1100, "end": 1200}]),
            [{"begin": 1100, "end": 1200}, {"begin": 2000, "end": 3000}],
        )
        self.assertEqual(
            dna_intersection(1000, None, 3000, [{"begin": 1100, "end": 1200}]),
            [{"begin": 0, "end": 1000}, {"begin": 1100, "end": 1200}],
        )
        self.assertEqual(
            dna_intersection(
                1000,
                2000,
                3000,
                [
                    {"begin": 900, "end": 1100},
                    {"begin": 1200, "end": 1300},
                    {"begin": 1900, "end": 2100},
                ],
            ),
            [
                {"begin": 0, "end": 1100},
                {"begin": 1200, "end": 1300},
                {"begin": 1900, "end": 3000},
            ],
        )

    def test_extract_section(self):
        self.assertEqual(len(extract_section(self.audio_segment, 1000, 2000)), 1000)
        self.assertEqual(len(extract_section(self.audio_segment, None, 500)), 500)
        self.assertEqual(
            len(extract_section(self.audio_segment, 1000, None)),
            len(self.audio_segment) - 1000,
        )


if __name__ == "__main__":
    main()
