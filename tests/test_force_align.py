"""
Test force-alignment with PocketSphinx FSG search from Python API
"""

from readalongs.align import align_audio
import unittest
import logging
import os

class TestForceAlignment(unittest.TestCase):
    logging.basicConfig(level=logging.DEBUG)
    data_dir = os.path.dirname(__file__)
    def testAlign(self):
        xml_path = os.path.join(self.data_dir, 'test_atj_sample.xml') 
        wav_path = os.path.join(self.data_dir, 'test_atj_sample.wav')
        alignments = align_audio(xml_path, wav_path)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
