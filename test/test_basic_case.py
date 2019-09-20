from unittest import TestCase
import os
from readalongs.align import align_audio

class TestBasicCase(TestCase):
    data_dir = os.path.dirname(__file__)

    def setUp(self):
        pass

    def testAPFile(self):
        # align ap.xml/ap.wav
        xml_path = os.path.join(self.data_dir, 'data/ap.xml')
        wav_path = os.path.join(self.data_dir, 'data/ap.wav')
        results = align_audio(xml_path, wav_path, unit='w')
        print(results)

    def testAPLongFile(self):
        # align ap.xml/ap.wav
        xml_path = os.path.join(self.data_dir, 'data/ap-long.xml')
        wav_path = os.path.join(self.data_dir, 'data/ap.wav')
        results = align_audio(xml_path, wav_path, unit='w')
        print(results)

    def testAPHeadFile(self):
        # align ap.xml/ap.wav
        xml_path = os.path.join(self.data_dir, 'data/ap-head.xml')
        wav_path = os.path.join(self.data_dir, 'data/ap.wav')
        results = align_audio(xml_path, wav_path, unit='w')
        print(results)

    def testAPTailFile(self):
        # align ap.xml/ap.wav
        xml_path = os.path.join(self.data_dir, 'data/ap-tail.xml')
        wav_path = os.path.join(self.data_dir, 'data/ap.wav')
        results = align_audio(xml_path, wav_path, unit='w')
        print(results)

if __name__ == '__main__':
    LOGGER.setLevel('DEBUG')
    unittest.main()
