#!/usr/bin/env python

"""Unit testing for the anchors functionality in readalongs align"""

import os
import sys
from contextlib import redirect_stderr
from io import StringIO

from pytest import main

from readalongs.align import align_audio
from readalongs.log import LOGGER
from tests.basic_test_case import BasicTestCase


class TestAnchors(BasicTestCase):
    """Unit testing for the anchors functionality in readalongs align"""

    def test_anchors_inner_only(self):
        """Test aligning with anchors only between existing text"""

        # ej-fra-anchors has anchors between words/sentences only
        with redirect_stderr(StringIO()):
            results = align_audio(
                os.path.join(self.data_dir, "ej-fra-anchors.readalong"),
                os.path.join(self.data_dir, "ej-fra.m4a"),
            )
        words = results["words"]
        # The input text file has 99 words, so should the aligned segments.
        assert len(words) == 99

        # Make sure the aligned segments stay on the right side of their anchors
        assert words[0]["end"] <= 1.62
        assert words[1]["start"] >= 1.62
        assert words[8]["end"] <= 3.81
        assert words[9]["start"] >= 3.81
        assert words[21]["end"] <= 6.74
        assert words[22]["start"] >= 6.74

    def test_anchors_outer_too(self):
        """Test aligning with anchors defining DNA segments at start and end too"""

        # ej-fra-anchors2 also has anchors before the first word and after the last word
        save_temps_prefix = os.path.join(self.tempdir, "anchors2-temps")
        with redirect_stderr(StringIO()):
            results = align_audio(
                os.path.join(self.data_dir, "ej-fra-anchors2.readalong"),
                os.path.join(self.data_dir, "ej-fra.m4a"),
                save_temps=save_temps_prefix,
            )
        words = results["words"]
        # The input text file has 99 words, so should the aligned segments.
        assert len(words) == 99

        # Make sure the aligned segments stay on the right side of their anchors,
        # including the initial and final ones inserted into anchors2.readalong
        assert words[0]["start"] >= 0.5
        assert words[0]["end"] <= 1.2
        assert words[1]["start"] >= 1.2
        assert words[8]["end"] <= 3.6
        assert words[9]["start"] >= 3.9
        assert words[21]["end"] <= 7.0
        assert words[22]["start"] >= 7.0
        assert words[-1]["end"] <= 33.2

        # Make sure the audio segment temp files were written and are not empty
        for suff in ("", ".2", ".3", ".4"):
            partial_wav_file = save_temps_prefix + ".wav" + suff
            assert os.path.exists(partial_wav_file), f"{partial_wav_file} should exist"
            assert (
                os.path.getsize(partial_wav_file) > 0
            ), f"{partial_wav_file} should not be empty"

    def test_anchors_align_modes(self, caplog):
        xml_with_anchors = """<doc xml:lang="fra"><body>
            <s>Bonjour.</s>
            <anchor time="1.62s"/>
            <s>Ceci ne peut pas être aligné avec du bruit.</s>
            <anchor time="5.62s"/>
            </body></doc>
        """
        xml_file = os.path.join(self.tempdir, "text-with-anchors.readalong")
        with open(xml_file, "w", encoding="utf8") as f:
            print(xml_with_anchors, file=f)
        caplog.set_level("INFO", logger=LOGGER.name)
        with redirect_stderr(StringIO()):
            results = align_audio(
                xml_file,
                os.path.join(self.data_dir, "noise.mp3"),
            )
        words = results["words"]
        assert len(words) == 10
        logger_output = caplog.text
        assert "Align mode strict succeeded for sequence 0." in logger_output
        assert "Align mode strict failed for sequence 1." in logger_output
        assert "Align mode moderate failed for sequence 1." in logger_output
        assert "Align mode loose succeeded for sequence 1." in logger_output


if __name__ == "__main__":
    main(sys.argv)
