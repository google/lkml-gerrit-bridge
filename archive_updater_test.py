import unittest
import subprocess
import os
import tempfile
import shutil
from archive_updater import fill_message_directory, setup_archive
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
                                                                    cmd=['git', '-C',
                                                                         'archive_path', 'log',
                                                                         'last_used_commit_hash..',
                                                                         '--format=format:%H'],
                                                                    stderr=b'Failed to log')

        with self.assertRaises(subprocess.CalledProcessError):
            fill_message_directory('archive_path', self.tmp_dir, 'last_used_commit_hash')

        self.assertEqual(len(os.listdir(self.tmp_dir)), 0)

    @mock.patch.object(subprocess, 'check_output')
    @mock.patch.object(subprocess, 'check_call')
    def test_fill_message_directory_no_hashes_available(self, mock_check_call, mock_check_output):
        mock_check_output.return_value = b''

        last_used_hash = fill_message_directory('archive_path', self.tmp_dir, 'last_used_hash')

        self.assertEqual(len(os.listdir(self.tmp_dir)), 0)
        self.assertEqual(last_used_hash, 'last_used_hash')

    @mock.patch.object(subprocess, 'check_call')
    @mock.patch.object(os, 'path')
    def test_setup_directory_success(self, mock_path, mock_check_call):
        mock_path.isdir.return_value = False
        setup_archive('archive_path')
        mock_check_call.assert_called_with(['git', '-C', '..', 'clone', '--mirror',
                           'https://lore.kernel.org/linux-kselftest/0',
                           'linux-kselftest/git/0.git'])

    @mock.patch.object(subprocess, 'check_call')
    @mock.patch.object(os, 'path')
    def test_setup_directory_exists(self, mock_path, mock_check_call):
        mock_path.isdir.return_value = True
        setup_archive('archive_path')
        mock_check_call.assert_not_called()

    @mock.patch.object(subprocess, 'check_call')
    @mock.patch.object(os, 'path')
    def test_setup_directory_fails(self, mock_path, mock_check_call):
        mock_path.isdir.return_value = False
        mock_check_call.side_effect = subprocess.CalledProcessError(returncode=1,
                                                                    cmd=['git', '-C', '..', 'clone', '--mirror',
                                                                         'https://lore.kernel.org/linux-kselftest/0',
                                                                         'linux-kselftest/git/0.git'],
                                                                    stderr=b'Failed to log')
        with self.assertRaises(subprocess.CalledProcessError):
            setup_archive('archive_path')


if __name__ == '__main__':
    unittest.main()