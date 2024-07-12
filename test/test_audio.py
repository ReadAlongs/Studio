#!/usr/bin/env python

"""Test suite for various audio contents handling methods"""

import os
from pathlib import Path
from subprocess import run
from unittest import main

from basic_test_case import BasicTestCase

from readalongs.audio_utils import (
    extract_section,
    join_section,
    mute_section,
    read_audio_from_file,
    remove_section,
    write_audio_to_file,
)
from readalongs.log import LOGGER


class TestAudio(BasicTestCase):
    """Test suite for various audio contents handling methods"""

    def setUp(self):
        super().setUp()
        self.audio_segment = read_audio_from_file(
            os.path.join(self.data_dir, "audio_sample.ogg")
        )
        self.noisy_segment = read_audio_from_file(
            os.path.join(self.data_dir, "noise_at_1500.mp3")
        )

    def align(self, input_text_path, input_audio_path, output_path, flags):
        """Wrapper for invoking readalongs align via subprocess.run"""
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
        return run(args, capture_output=True, check=False, encoding="utf-8")

    def test_mute_section(self):
        """Should mute section of audio"""
        max_before = self.audio_segment[1000:2000].max
        muted_segment = mute_section(self.audio_segment, 1000, 2000)
        muted_section = muted_segment[1000:2000]
        # This worked with pydub 0.23.1, but it does not work with 0.25.1
        # self.assertLessEqual(muted_section.max, 1)
        # Muting applies a gain of -120, so the results is not necessarily 0,
        # it's just much smaller.
        self.assertLessEqual(muted_section.max, max_before / 1000)

    def test_remove_section(self):
        """Should remove section of audio"""
        removed_segment = remove_section(self.audio_segment, 1000, 2000)
        self.assertNotEqual(len(removed_segment), len(self.audio_segment))
        self.assertEqual(len(removed_segment), len(self.audio_segment) - 1000)

    def test_rejoin_section(self):
        """Should rejoin removed/muted sections"""
        removed_section = self.audio_segment[1000:2000]
        removed_segment = remove_section(self.audio_segment, 1000, 2000)
        rejoined_segment = join_section(removed_segment, removed_section, 1000)
        self.assertEqual(len(rejoined_segment), len(self.audio_segment))

    def test_align_sample(self):
        """Sanity check that test audio should align"""
        # Align
        input_text_path = os.path.join(self.data_dir, "audio_sample.txt")
        input_audio_path = os.path.join(self.data_dir, "audio_sample.ogg")
        flags = ["-l", "eng"]
        output_path = os.path.join(self.tempdir, "output")
        process = self.align(input_text_path, input_audio_path, output_path, flags)
        if process.returncode != 0:
            LOGGER.error("Subprocess readalongs align failed: %s", process.stderr)
        # Check Result
        raspath = Path(output_path) / "www"
        ras_files = raspath.glob("*.readalong")
        self.assertTrue(
            next(ras_files, False),
            "No *.readalong files found; "
            "pip install --force-reinstall --upgrade might be required "
            "if dependencies changed.",
        )
        # Make sure ss logs are disabled
        self.assertNotIn("Current configuration", process.stderr)

    def test_align_removed(self):
        """Try aligning section with removed audio"""
        # Process Audio
        removed_segment = remove_section(self.noisy_segment, 1500, 2500)
        audio_output_path = os.path.join(self.tempdir, "removed_sample.mp3")
        with open(audio_output_path, "wb") as f:
            removed_segment.export(f)
        # Align
        input_text_path = os.path.join(self.data_dir, "audio_sample.txt")
        input_audio_path = audio_output_path
        flags = ["-l", "eng", "--debug-aligner"]
        output_path = os.path.join(self.tempdir, "output_removed")
        process = self.align(input_text_path, input_audio_path, output_path, flags)
        if process.returncode != 0:
            LOGGER.error("Subprocess readalongs align failed: %s", process.stderr)
        # Check Result
        raspath = Path(output_path) / "www"
        ras_files = raspath.glob("*.readalong")
        self.assertTrue(
            next(ras_files, False),
            "No *.readalong files found; "
            "pip install --force-reinstall --upgrade might be required "
            "if dependencies changed.",
        )
        # Make sure ss logs are enabled
        self.assertIn("Current configuration", process.stderr)

    def test_align_muted(self):
        """Try aligning section with muted audio"""
        # Process Audio
        muted_segment = mute_section(self.noisy_segment, 1500, 2500)
        audio_output_path = os.path.join(self.tempdir, "muted_sample.mp3")
        with open(audio_output_path, "wb") as f:
            muted_segment.export(f)
        # Align
        input_text_path = os.path.join(self.data_dir, "audio_sample.txt")
        input_audio_path = audio_output_path
        flags = ["-l", "eng", "-b"]
        output_path = os.path.join(self.tempdir, "output_muted")
        process = self.align(input_text_path, input_audio_path, output_path, flags)
        if process.returncode != 0:
            LOGGER.error("Subprocess readalongs align failed: %s", process.stderr)
        # Check Result
        raspath = Path(output_path) / "www"
        ras_files = raspath.glob("*.readalong")
        self.assertTrue(
            next(ras_files, False),
            "No *.readalong files found; "
            "pip install --force-reinstall --upgrade might be required "
            "if dependencies changed.",
        )

    def test_extract_section(self):
        """Unit test extract_section()"""
        self.assertEqual(len(extract_section(self.audio_segment, 1000, 2000)), 1000)
        self.assertEqual(len(extract_section(self.audio_segment, None, 500)), 500)
        self.assertEqual(
            len(extract_section(self.audio_segment, 1000, None)),
            len(self.audio_segment) - 1000,
        )

    def test_write_audio_to_file(self):
        """Mininal unit testing for write_audio_to_file"""
        section = extract_section(self.audio_segment, 1000, 2000)
        output_path = os.path.join(self.tempdir, "section_output.mp3")
        write_audio_to_file(section, output_path)
        self.assertTrue(os.path.exists(output_path))
        reloaded_section = read_audio_from_file(output_path)
        self.assertAlmostEqual(
            len(section),
            len(reloaded_section),
            msg="reloaded audio file is more than 50ms shorter or longer",
            delta=50,
        )


if __name__ == "__main__":
    main()
