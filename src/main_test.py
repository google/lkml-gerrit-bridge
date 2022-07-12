import unittest
import os
import tempfile
import shutil
from unittest import mock
from typing import List
import archive_updater
import gerrit
import git

from archive_converter import ArchiveMessageIndex
from main import Server
from message_dao import FakeMessageDao
from patch_parser import parse_comments
from message import Message
from google.cloud.sql.connector import Connector

from test_helpers import compare_message_subjects, test_data_path

class MainTest(unittest.TestCase):

    def setUp(self):
        self.addCleanup(mock.patch.stopall)
        mock.patch.object(gerrit, 'get_gerrit_rest_api').start()
        mock.patch.object(archive_updater, 'setup_archive').start()
        self.message_dao = FakeMessageDao()

    def test_remove_files(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.assertEqual(len(os.listdir(self.tmp_dir)), 0)
        file = os.path.join(self.tmp_dir, 'file_to_be_removed.txt')
        with open(file, 'w') as f:
            f.write('this file will be removed')
        self.assertEqual(len(os.listdir(self.tmp_dir)), 1)
        Server.remove_files(self.tmp_dir)
        self.assertEqual(len(os.listdir(self.tmp_dir)), 0)
        shutil.rmtree(self.tmp_dir)

    def test_split_parent_and_reply_messages(self):
        archive_index = ArchiveMessageIndex(self.message_dao)
        messages = archive_index.update(test_data_path()).values()
        parents, replies = Server.split_parent_and_reply_messages(messages)
        self.assertEqual(len(parents), 2)
        self.assertEqual(len(replies), 6)

        expected_parents = ['[PATCH v2 1/2] Input: i8042 - Prevent intermixing i8042 commands',
                    '[PATCH v2 0/4] kselftests/arm64: add PAuth tests']
        expected_replies = ['Re: [PATCH] Remove final reference to superfluous smp_commence().',
                    '[PATCH v2 1/3] dmaengine: add dma_get_channel_caps()',
                    '[PATCH v2 1/4] kselftests/arm64: add a basic Pointer Authentication test',
                    '[PATCH v2 2/4] kselftests/arm64: add nop checks for PAuth tests',
                    '[PATCH v2 3/4] kselftests/arm64: add PAuth test for whether exec() changes keys',
                    '[PATCH v2 4/4] kselftests/arm64: add PAuth tests for single threaded consistency and key uniqueness']

        compare_message_subjects(self, parents, expected_parents)
        compare_message_subjects(self, replies, expected_replies)

    @mock.patch.object(archive_updater, 'fill_message_directory')
    @mock.patch.object(Server, 'upload_messages')
    @mock.patch.object(Server, 'upload_comments')
    def test_server_upload_across_batches(self, mock_upload_comments, mock_upload_messages,
                                          mock_fill_message_directory):
        archive_index = ArchiveMessageIndex(self.message_dao)
        messages_mapping = archive_index.update(test_data_path())
        messages = list(messages_mapping.values())

        # Make sure the ordering is deterministic.
        messages.sort(key=lambda m: m.id)
        first_batch = {message.id : message for message in messages[0:6]}
        second_batch = {message.id : message for message in messages[6:]}
        mock_fill_message_directory.return_value = ''

        # declaring mock objects here because I want to use the ArchiveMessageIndex functionality to build the test data
        with mock.patch.object(ArchiveMessageIndex, 'update') as mock_update, mock.patch.object(FakeMessageDao, 'get') as mock_get:
            mock_update.side_effect = [first_batch, second_batch]
            mock_get.side_effect = [None, None, messages[6], messages[7]]
            server = Server(self.message_dao)
            server.update_convert_upload()
            mock_upload_messages.assert_called_with([messages[2],messages[3]])
            mock_upload_comments.assert_called_with({})

            server.update_convert_upload()
            mock_upload_messages.assert_called_with([messages[6],messages[7]])
            mock_upload_comments.assert_called_with({})


    '''
    def test_upload_failed_apply(self):
        server = Server()
        server.update_message_dir()
        server.upload_messages(['<20201012222050.999431-1-dlatypov@google.com>'])
    '''


if __name__ == '__main__':
    unittest.main()
