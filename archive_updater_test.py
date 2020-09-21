import unittest
import subprocess
import os
import tempfile
import shutil
from archive_updater import fill_message_directory, MAX_NUMBER_OF_RECENT_COMMITS
from unittest import mock

class ArchiveUpdaterFillMessageDirectoryTest(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
    def tearDown(self):
        shutil.rmtree(self.tmp_dir)

    @mock.patch.object(subprocess, 'check_call')
    def test_update_failure(self, mock_check_call):
        mock_check_call.side_effect = subprocess.CalledProcessError(returncode=1,
                                                                    cmd=['git', '-C', 'archive_path', 'fetch'],
                                                                    stderr=b'Failed to fetch')
        with self.assertRaises(subprocess.CalledProcessError):
            fill_message_directory('archive_path', self.tmp_dir, '')

    @mock.patch.object(subprocess, 'check_output')
    @mock.patch.object(subprocess, 'call')
    @mock.patch.object(subprocess, 'check_call')
    def test_fill_message_directory_success(self, mock_check_call, mock_call, mock_check_output):
        def writeFile(args, stdout):
            stdout.write('called with: ' + ' '.join(args))
        mock_call.side_effect = writeFile
        mock_check_output.return_value = b'success1 success2 success3'

        last_used_hash = fill_message_directory('archive_path', self.tmp_dir, '')

        self.assertEqual(len(os.listdir(self.tmp_dir)), 3)
        for filename in os.listdir(self.tmp_dir):
            with open(os.path.join(self.tmp_dir,filename), "r") as file:
                val = file.read()
                self.assertIn('git -C archive_path show', val)
        self.assertEqual(last_used_hash, 'success1')

    @mock.patch.object(subprocess, 'check_output')
    @mock.patch.object(subprocess, 'check_call')
    def test_fill_message_directory_fail_to_log(self, mock_check_call, mock_check_output):
        mock_check_output.side_effect = subprocess.CalledProcessError(returncode=1,
                                                                    cmd=['git', '-C', 'archive_path',
                                                                         'log', '--format=format:%H',
                                                                         '-n',str(MAX_NUMBER_OF_RECENT_COMMITS)],
                                                                    stderr=b'Failed to log')

        with self.assertRaises(subprocess.CalledProcessError):
            fill_message_directory('archive_path', self.tmp_dir, '')

        self.assertEqual(len(os.listdir(self.tmp_dir)), 0)

    @mock.patch.object(subprocess, 'check_output')
    @mock.patch.object(subprocess, 'check_call')
    def test_fill_message_directory_no_hashes_available(self, mock_check_call, mock_check_output):
        mock_check_output.return_value = b''

        with self.assertRaisesRegex(Exception, 'no commits'):
            fill_message_directory('', self.tmp_dir, '')

        self.assertEqual(len(os.listdir(self.tmp_dir)), 0)


if __name__ == '__main__':
    unittest.main()