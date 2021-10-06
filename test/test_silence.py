import os
from unittest import main

from basic_test_case import BasicTestCase
from lxml import etree
from pydub import AudioSegment

from readalongs.cli import align


class TestSilence(BasicTestCase):
    def test_basic_silence_insertion(self):
        output = os.path.join(self.tempdir, "silence")
        # Run align from xml
        results = self.runner.invoke(
            align,
            [
                "-s",
                "-C",
                "-t",
                "-l",
                "fra",
                os.path.join(self.data_dir, "ej-fra-silence.xml"),
                os.path.join(self.data_dir, "ej-fra.m4a"),
                output,
            ],
        )
        self.assertEqual(results.exit_code, 0)
        self.assertTrue(os.path.exists(os.path.join(output, "silence.wav")))
        # test silence spans in output xml
        with open(os.path.join(output, "silence.xml"), "rb") as f:
            xml_bytes = f.read()
        root = etree.fromstring(xml_bytes)
        silence_spans = root.xpath("//*[@silence]")
        self.assertEqual(len(silence_spans), 3)
        # test audio has correct amount of silence added
        original_audio = AudioSegment.from_file(
            os.path.join(self.data_dir, "ej-fra.m4a")
        )
        new_audio = AudioSegment.from_wav(os.path.join(output, "silence.wav"))
        self.assertEqual(len(new_audio) - len(original_audio), 2882)


if __name__ == "__main__":
    main()
