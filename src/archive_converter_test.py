import unittest
from archive_converter import generate_email_from_file, ArchiveMessageIndex
from message_dao import FakeMessageDao
from typing import List
from message import Message

from test_helpers import compare_message_subjects, test_data_path

class ArchiveConverterTest(unittest.TestCase):

    def setUp(self):
        self.message_dao = FakeMessageDao()

    def test_generate_email_from_single_email_thread(self):
        email = generate_email_from_file(test_data_path('patch6.txt'))
        self.assertEqual(email.subject, '[PATCH v2 1/2] Input: i8042 - Prevent intermixing i8042 commands')
        self.assertEqual(email.in_reply_to, None)
        self.assertEqual(email.from_, "Raul E Rangel <rrangel@chromium.org>")
        self.assertTrue(len(email.content) > 0)

    def test_update_with_no_changes_to_data(self):
        archive_index = ArchiveMessageIndex(self.message_dao)
        archive_index.update(test_data_path())
        old_size = self.message_dao.size()
        archive_index.update(test_data_path())
        self.assertEqual(old_size, self.message_dao.size())

    def test_update_return_proper_patches(self):
        archive_index = ArchiveMessageIndex(self.message_dao)
        new_messages = archive_index.update(test_data_path()).values()
        self.assertEqual(len(new_messages), 8)

        subjects = ['Re: [PATCH] Remove final reference to superfluous smp_commence().',
                    '[PATCH v2 1/3] dmaengine: add dma_get_channel_caps()',
                    '[PATCH v2 1/2] Input: i8042 - Prevent intermixing i8042 commands',
                    '[PATCH v2 0/4] kselftests/arm64: add PAuth tests',
                    '[PATCH v2 1/4] kselftests/arm64: add a basic Pointer Authentication test',
                    '[PATCH v2 2/4] kselftests/arm64: add nop checks for PAuth tests',
                    '[PATCH v2 3/4] kselftests/arm64: add PAuth test for whether exec() changes keys',
                    '[PATCH v2 4/4] kselftests/arm64: add PAuth tests for single threaded consistency and key uniqueness']
        compare_message_subjects(self, new_messages, subjects)




if __name__ == '__main__':
    unittest.main()
