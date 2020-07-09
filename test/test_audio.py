import os
from readalongs.log import LOGGER
from pathlib import Path
from subprocess import run
from shutil import rmtree
from unittest import TestCase, main
from readalongs.audio_utils import read_audio_from_file, write_audio_to_file, mute_section, join_section, remove_section
from readalongs.align import calculate_adjustment, correct_adjustments


class TestAudio(TestCase):
    def setUp(self):
        self.data_path = os.path.join(os.path.dirname(__file__), 'data')
        self.audio_segment = read_audio_from_file(
            os.path.join(self.data_path, 'audio_sample.ogg'))
        self.noisy_segment = read_audio_from_file(
            os.path.join(self.data_path, 'noise_at_1500.mp3'))
        self.to_remove = []

    def tearDown(self):
        for path in self.to_remove:
            if os.path.exists(path):
                if os.path.isfile(path):
                    LOGGER.info(f'Cleaning up {path}')
                    os.remove(path)
                elif os.path.isdir(path):
                    LOGGER.info(f'Cleaning up {path}')
                    rmtree(path)

    def align(self, input_text_path, input_audio_path, output_path, flags):
        args = ['readalongs', 'align', input_text_path,
                input_audio_path, output_path] + flags
        LOGGER.info(
            f'Aligning {input_text_path} and {input_audio_path}, outputting to {output_path}')
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
        input_text_path = os.path.join(self.data_path, 'audio_sample.txt')
        input_audio_path = os.path.join(self.data_path, 'audio_sample.ogg')
        flags = ['-i', '-l', 'eng']
        output_path = os.path.join(self.data_path, 'output')
        log = self.align(input_text_path, input_audio_path, output_path, flags)
        # Check Result
        smilpath = Path(output_path)
        smil_files = smilpath.glob('*.smil')
        self.assertGreaterEqual(len([x for x in smil_files]), 1)
        self.assertFalse('error' in str(log).lower())
        # Cleanup
        self.to_remove.append(output_path)

    def test_align_removed(self):
        """ Try aligning section with removed audio
        """
        # Process Audio
        removed_segment = remove_section(self.noisy_segment, 1500, 2500)
        audio_output_path = os.path.join(self.data_path, 'removed_sample.mp3')
        removed_segment.export(audio_output_path)
        # Align
        input_text_path = os.path.join(self.data_path, 'audio_sample.txt')
        input_audio_path = audio_output_path
        flags = ['-i', '-l', 'eng']
        output_path = os.path.join(self.data_path, 'output_removed')
        log = self.align(input_text_path, input_audio_path, output_path, flags)
        # Check Result
        smilpath = Path(output_path)
        smil_files = smilpath.glob('*.smil')
        self.assertGreaterEqual(len([x for x in smil_files]), 1)
        self.assertFalse('error' in str(log).lower())
        # Cleanup
        self.to_remove.append(output_path)
        self.to_remove.append(audio_output_path)

    def test_align_muted(self):
        """ Try aligning section with muted audio
        """
        # Process Audio
        muted_segment = mute_section(self.noisy_segment, 1500, 2500)
        audio_output_path = os.path.join(self.data_path, 'muted_sample.mp3')
        muted_segment.export(audio_output_path)
        # Align
        input_text_path = os.path.join(self.data_path, 'audio_sample.txt')
        input_audio_path = audio_output_path
        flags = ['-i', '-l', 'eng', '-b']
        output_path = os.path.join(self.data_path, 'output_muted')
        log = self.align(input_text_path, input_audio_path, output_path, flags)
        # Check Result
        smilpath = Path(output_path)
        smil_files = smilpath.glob('*.smil')
        self.assertGreaterEqual(len([x for x in smil_files]), 1)
        self.assertFalse('error' in str(log).lower())
        # Cleanup
        self.to_remove.append(output_path)
        self.to_remove.append(audio_output_path)

    def test_adjustment_calculation(self):
        """ Try adjusting alignments of re-built audio
        """
        self.assertEqual(calculate_adjustment(
            1.0, [{'begin': 1000, 'end': 1100}]), 100)
        self.assertEqual(calculate_adjustment(
            0.9, [{'begin': 1000, 'end': 1100}]), 0)
        self.assertEqual(calculate_adjustment(
            1000, [{'begin': 1000, 'end': 1100}]), 100)
        self.assertEqual(calculate_adjustment(
            900, [{'begin': 1000, 'end': 1100}]), 0)
        self.assertEqual(calculate_adjustment(
            2.0, [{'begin': 1000, 'end': 1100}]), 100)
        self.assertEqual(calculate_adjustment(
            1.0, [{'begin': 1000, 'end': 1100}, {'begin': 1500, 'end': 1700}]), 100)
        self.assertEqual(calculate_adjustment(
            2.0, [{'begin': 1000, 'end': 1100}, {'begin': 1500, 'end': 2100}]), 700)

    def test_adjustment_correction(self):
        """ Try correcting adjusted alignments of re-built audio
        """
        self.assertEqual(correct_adjustments(
            950, 1125, [{'begin': 1000, 'end': 1100}]), (950, 1000))
        self.assertEqual(correct_adjustments(
            975, 1150, [{'begin': 1000, 'end': 1100}]), (1100, 1150))
        self.assertEqual(correct_adjustments(
            .950, 1.125, [{'begin': 1000, 'end': 1100}]), (950, 1000))
        self.assertEqual(correct_adjustments(
            .975, 1.150, [{'begin': 1000, 'end': 1100}]), (1100, 1150))


if __name__ == '__main__':
    main()
