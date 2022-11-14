#!/usr/bin/env python

"""Test PortableNamedTemporaryFile class"""

import os
import unittest
from tempfile import NamedTemporaryFile

from readalongs.log import LOGGER
from readalongs.portable_tempfile import PortableNamedTemporaryFile


class TestTempFile(unittest.TestCase):
    """Test PortableNamedTemporaryFile class"""

    def test_basic_file(self):
        """Test basic file IO usage. This was more for me to learn file IO in Python..."""
        f = open("delme_test_temp_file", mode="w", encoding="utf8")
        f.write("some text")
        f.close()
        self.assertTrue(os.path.exists("delme_test_temp_file"))
        os.unlink("delme_test_temp_file")
        self.assertFalse(os.path.exists("delme_test_temp_file"))

    def test_ntf(self):
        """Regular usage of tempfile.NamedTemporaryFile from the standard library"""
        tf = NamedTemporaryFile(prefix="testtempfile_testNTF_", delete=False, mode="w")
        tf.write("Some text")
        # LOGGER.debug("tf.name {}".format(tf.name))
        tf.close()
        readf = open(tf.name, mode="r", encoding="utf8")
        text = readf.readline()
        self.assertEqual(text, "Some text")
        readf.close()
        os.unlink(tf.name)

    def test_delete_false(self):
        """PortableNamedTemporaryFile with delete=False behaves like tempfile.NamedTemporaryFile"""
        tf = PortableNamedTemporaryFile(
            prefix="testtempfile_testDeleteFalse_", delete=False, mode="w"
        )
        tf.write("Some text")
        tf.close()
        # LOGGER.info(tf.name)
        readf = open(tf.name, mode="r", encoding="utf8")
        text = readf.readline()
        readf.close()
        self.assertEqual(text, "Some text")
        os.unlink(tf.name)

    def test_typical_usage(self):
        """Typical usage of PortableNamedTemporaryFile, i.e., with delete=True

        This is what PortableNamedTemporaryFile is all about, since tempfile.NamedTemporaryFile
        with delete=True on Windows does not work like we might want it to.
        """
        tf = PortableNamedTemporaryFile(
            prefix="testtempfile_testTypicalUsage_", delete=True, mode="w"
        )
        # LOGGER.info(tf.name)
        tf.write("Some text")
        tf.close()
        # LOGGER.info(tf.name)
        readf = open(tf.name, mode="r", encoding="utf8")
        text = readf.readline()
        readf.close()
        self.assertEqual(text, "Some text")

    def test_using_with(self):
        """In a with statement, the file will be deleted when the with exits"""
        with PortableNamedTemporaryFile(
            prefix="testtempfile_testUsingWith_", delete=True, mode="w"
        ) as tf:
            # LOGGER.info(tf.name)
            tf.write("Some text")
            tf.close()
            # LOGGER.info(tf.name)
            filename = tf.name
            readf = open(tf.name, mode="r", encoding="utf8")
            text = readf.readline()
            readf.close()
            self.assertEqual(text, "Some text")
            self.assertTrue(os.path.exists(filename))
        self.assertFalse(os.path.exists(filename))

    def test_seek(self):
        """read/write operations should work on a PortableNamedTemporaryFile"""
        tf = PortableNamedTemporaryFile(
            prefix="testtempfile_testSeek_", delete=True, mode="w+"
        )
        tf.write("Some text")
        tf.seek(0)
        text = tf.readline()
        self.assertEqual(text, "Some text")
        tf.close()
        os.unlink(tf.named_temporary_file.name)


if __name__ == "__main__":
    LOGGER.setLevel("DEBUG")
    unittest.main()
