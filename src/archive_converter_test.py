import unittest
from archive_converter import generate_email_from_file, ArchiveMessageIndex
from message_dao import MessageDao
from typing import List
from message import Message

class ArchiveConverterTest(unittest.TestCase):

    def test_generate_email_from_single_email_thread(self):
        email = generate_email_from_file("test_data/patch6.txt")
        self.assertEqual(email.subject, '[PATCH v2 1/2] Input: i8042 - Prevent intermixing i8042 commands')
        self.assertEqual(email.in_reply_to, None)
        self.assertEqual(email.from_, "Raul E Rangel <rrangel@chromium.org>")
        self.assertTrue(len(email.content) > 0)

    def test_update_with_no_changes_to_data(self):
        archive_index = ArchiveMessageIndex(MessageDao())
        archive_index.update('test_data')
        old_size = archive_index.size()
        archive_index.update('test_data')
        self.assertEqual(old_size, archive_index.size())

    def test_update_return_proper_patches(self):
        archive_index = ArchiveMessageIndex(MessageDao())
        new_messages = archive_index.update('test_data')
        self.assertEqual(len(new_messages), 8)

        def compare_message_subject(messages : List[Message], subjects : List[str]):
            self.assertCountEqual([m.subject for m in messages], subjects)

        subjects = ['Re: [PATCH] Remove final reference to superfluous smp_commence().',
                    '[PATCH v2 1/3] dmaengine: add dma_get_channel_caps()',
                    '[PATCH v2 1/2] Input: i8042 - Prevent intermixing i8042 commands',
                    '[PATCH v2 0/4] kselftests/arm64: add PAuth tests',
                    '[PATCH v2 1/4] kselftests/arm64: add a basic Pointer Authentication test',
                    '[PATCH v2 2/4] kselftests/arm64: add nop checks for PAuth tests',
                    '[PATCH v2 3/4] kselftests/arm64: add PAuth test for whether exec() changes keys',
                    '[PATCH v2 4/4] kselftests/arm64: add PAuth tests for single threaded consistency and key uniqueness']
        compare_message_subject(new_messages, subjects)




if __name__ == '__main__':
    unittest.main()
