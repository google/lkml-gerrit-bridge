import unittest
import subprocess
import zlib

from unittest import mock
from google.cloud.sql.connector import Connector

import message
import message_dao
import archive_converter
from test_helpers import test_data_path

class StrContains(str):
   def __eq__(self, other):
      return self in other

class MessageDaoTest(unittest.TestCase):

    def setUp(self):
        self.addCleanup(mock.patch.stopall)
        self.mock_connect = mock.patch.object(Connector, 'connect').start()
        mock_connection = self.mock_connect.return_value
        self.mock_commit = mock_connection.commit
        self.mock_cursor = mock_connection.cursor.return_value.__enter__.return_value
        self.mock_execute = self.mock_cursor.execute
        # Check initialization of DAO
        self.dao = message_dao.MessageDao('FAKE_GIT_PATH')
        self.mock_connect.assert_called_once()
        self.mock_commit.assert_called_once()
        self.assertEqual(3, self.mock_execute.call_count)
        self.mock_execute.reset_mock()
        self.mock_commit.reset_mock()
        self.mock_connect.side_effect = RuntimeError("Shouldn't be called after init")

    def test_store(self):
        email = archive_converter.generate_email_from_file(test_data_path('patch6.txt'))
        sql_text = "REPLACE INTO Messages VALUES (%s, %s, %s, %s, %s, %s, %s)"
        self.dao.store(email)
        self.mock_execute.assert_called_once_with(sql_text, mock.ANY)
        self.mock_commit.assert_called_once()

    @mock.patch.object(subprocess, 'check_output')
    @mock.patch.object(message_dao, 'parse_message_from_str')
    def test_get(self, mock_parse_msg, mock_check_output):
        self.mock_commit.side_effect = RuntimeError("Shouldn't be called during get")
        email = archive_converter.generate_email_from_file(test_data_path('patch6.txt'))
        mock_parse_msg.return_value = email
        self.mock_cursor.fetchone.return_value = (email.archive_hash, email.change_id)
        self.assertEqual(email, self.dao.get('fake_message_id'))
        self.assertEqual(2, self.mock_execute.call_count)
        self.mock_execute.assert_has_calls([
            mock.call(StrContains("WHERE message_id=%s"), mock.ANY),  # get this msg
            mock.call(StrContains("WHERE in_reply_to=%s"), mock.ANY),  # get children
        ])

    def test_get_missing(self):
        self.mock_commit.side_effect = RuntimeError("Shouldn't be called during get")
        self.mock_cursor.fetchone.return_value = None
        self.assertIsNone(self.dao.get('not_in_dao'))
        self.mock_execute.assert_called_once()

    def test_size(self):
        self.mock_cursor.fetchone.return_value = (1,)
        self.assertEqual(1, self.dao.size())
        self.mock_execute.assert_called_once()

    def test_store_hash(self):
        self.dao.store_last_hash("some_hash")
        sql_text = "REPLACE INTO States VALUES (%s, %s)"
        self.mock_execute.assert_called_once_with(sql_text, mock.ANY)
        self.mock_commit.assert_called_once()

    def test_get_hash(self):
        self.mock_commit.side_effect = RuntimeError("Shouldn't be called during get_hash")
        self.mock_cursor.fetchone.return_value = ("fake_hash",)
        self.assertEqual("fake_hash", self.dao.get_last_hash())
        self.mock_execute.assert_called_once()

    def test_get_hash_missing(self):
        self.mock_commit.side_effect = RuntimeError("Shouldn't be called during get_hash")
        self.mock_cursor.fetchone.return_value = None
        self.assertEqual(message_dao.EPOCH_HASH, self.dao.get_last_hash())
        self.mock_execute.assert_called_once()

if __name__ == '__main__':
    # TODO(lenhard@google.com): Issue with Google's Connector that causes segmentation fault
    # unittest.main()
    pass