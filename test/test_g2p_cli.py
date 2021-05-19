#!/usr/bin/env python3

import os
import tempfile
from unittest import TestCase, main

from readalongs.app import app
from readalongs.cli import g2p, prepare, tokenize


class TestG2pCli(TestCase):
    data_dir = os.path.join(os.path.dirname(__file__), "data")

    # Set this to True to keep the temp dirs after running, for manual inspection
    # but please never push a commit setting this to True!
    keep_temp_dir_after_running = True

    def setUp(self):
        app.logger.setLevel("DEBUG")
        self.runner = app.test_cli_runner()
        if not self.keep_temp_dir_after_running:
            # Temporary directories that get automatically cleaned up:
            self.tempdirobj = tempfile.TemporaryDirectory(
                prefix="tmpdir_test_g2p_cli_", dir="."
            )
            self.tempdir = self.tempdirobj.name
        else:
            # Alternative tempdir code keeps it after running, for manual inspection:
            self.tempdir = tempfile.mkdtemp(prefix="tmpdir_test_g2p_cli_", dir=".")
            print("tmpdir={}".format(self.tempdir))

    def tearDown(self):
        if not self.keep_temp_dir_after_running:
            self.tempdirobj.cleanup()

    def test_invoke_g2p(self):
        input_file = os.path.join(self.data_dir, "fra-tokenized.xml")
        g2p_file = os.path.join(self.tempdir, "fra-g2p.xml")
        results = self.runner.invoke(g2p, [input_file, g2p_file])
        print(f"g2p results.output='{results.output}'")
        self.assertEqual(results.exit_code, 0)
        self.assertTrue(os.path.exists(os.path.join(self.tempdir, "fra-g2p.xml")))

        # Testing that it fails when the file already exists has to be in the same test,
        # otherwise we have a different tempdir and the file won't already exist
        results = self.runner.invoke(g2p, [input_file, g2p_file])
        print(f"g2p results.output='{results.output}'")
        self.assertNotEqual(results.exit_code, 0)
        self.assertIn("use -f to overwrite", results.output)

        # And add -f to force the overwrite
        results = self.runner.invoke(g2p, ["-f", input_file, g2p_file])
        print(f"g2p results.output='{results.output}'")
        self.assertEqual(results.exit_code, 0)

    def test_mixed_langs(self):
        input_file = os.path.join(self.data_dir, "mixed-langs.tokenized.xml")
        g2p_file = os.path.join(self.tempdir, "mixed-langs.g2p.xml")
        results = self.runner.invoke(g2p, [input_file, g2p_file])
        print(f"g2p results.output='{results.output}'")
        self.assertEqual(results.exit_code, 0)
        self.assertTrue(os.path.exists(g2p_file))

        ref_file = os.path.join(self.data_dir, "mixed-langs.g2p.xml")
        with open(g2p_file) as output_f, open(ref_file) as ref_f:
            self.maxDiff = None
            self.assertListEqual(
                list(output_f),
                list(ref_f),
                f"output {g2p_file} and reference {ref_file} differ.",
            )

    # Write text to a temp file, pass it through prepare -l lang, and then tokenize,
    # saving the final results into filename.
    # filename is assumed to be inside self.tempdir, so we count on tearDown() to clean up.
    def write_prepare_tokenize(self, text, lang, filename):
        with open(filename + ".input.txt", "w") as f:
            print(text, file=f)
        self.runner.invoke(
            prepare, ["-l", lang, filename + ".input.txt", filename + ".prepared.xml"]
        )
        self.runner.invoke(tokenize, [filename + ".prepared.xml", filename])

    def test_english_oov(self):
        tok_file = os.path.join(self.tempdir, "tok.xml")
        g2p_file = os.path.join(self.tempdir, "g2p.xml")
        self.write_prepare_tokenize("This is a froobnelicious OOV.", "eng", tok_file)
        results = self.runner.invoke(g2p, [tok_file, g2p_file])
        print(
            f"test_english_oov: g2p "
            f"results.output='{results.output}' "
            f"results.exception={results.exception!r}"
        )
        self.assertNotEqual(results.exit_code, 0)
        self.assertTrue(isinstance(results.exception, KeyError))

    def test_french_oov(self):
        tok_file = os.path.join(self.tempdir, "tok.xml")
        g2p_file = os.path.join(self.tempdir, "g2p.xml")
        self.write_prepare_tokenize(
            "Le ñ n'est pas dans l'alphabet français.", "fra", tok_file
        )
        results = self.runner.invoke(g2p, [tok_file, g2p_file])
        print(
            f"test_french_oov: g2p "
            f"results.output='{results.output}' "
            f"results.exception={results.exception!r}"
        )
        self.assertIn("not fully valid", results.output)


if __name__ == "__main__":
    main()
