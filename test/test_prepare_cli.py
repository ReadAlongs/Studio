from unittest import main, TestCase
import tempfile
import os

from readalongs.log import LOGGER
from readalongs.app import app
from readalongs.cli import prepare

class TestPrepareCli(TestCase):
    LOGGER.setLevel('DEBUG')
    data_dir = os.path.join(os.path.dirname(__file__), 'data')

    def setUp(self):
        app.logger.setLevel('DEBUG')
        self.runner = app.test_cli_runner()
        self.tempdirobj = tempfile.TemporaryDirectory(prefix="test_prepare_cli_tmpdir", dir=".")
        self.tempdir = self.tempdirobj.name
        # Alternative tempdir code keeps it after running, for manual inspection:
        #self.tempdir = tempfile.mkdtemp(prefix="test_prepare_cli_tmpdir", dir=".")
        #print('tmpdir={}'.format(self.tempdir))

    def tearDown(self):
        self.tempdirobj.cleanup()

    def test_invoke_prepare(self):
        results = self.runner.invoke(prepare, '-l atj -d /dev/null ' + self.tempdir + '/delme')
        self.assertEqual(results.exit_code, 0)
        self.assertRegex(results.stdout, "Running readalongs prepare")
        #print('Prepare.stdout: {}'.format(results.stdout))

    def test_no_lang(self):
        results = self.runner.invoke(prepare, '/dev/null /dev/null')
        self.assertNotEqual(results.exit_code, 0)
        self.assertRegex(results.stdout, 'Missing.*language')

    def test_inputfile_not_exist(self):
        results = self.runner.invoke(prepare, '-l atj /file/does/not/exist delme')
        self.assertNotEqual(results.exit_code, 0)
        self.assertRegex(results.stdout, 'INPUTFILE.*does not exist')

    def test_outputfile_exists(self):
        results = self.runner.invoke(prepare, '-l atj /dev/null ' + self.tempdir + '/exists')
        results = self.runner.invoke(prepare, '-l atj /dev/null ' + self.tempdir + '/exists')
        self.assertNotEqual(results.exit_code, 0)
        self.assertRegex(results.stdout, 'exists.*overwrite')

    def test_output_exists(self):
        xmlfile=self.tempdir+'/fra.xml'
        results = self.runner.invoke(prepare, ['-l', 'fra', self.data_dir+'/fra.txt', xmlfile])
        self.assertTrue(os.path.exists(xmlfile), 'output xmlfile did not get created')

if __name__ == '__main__':
    main()
