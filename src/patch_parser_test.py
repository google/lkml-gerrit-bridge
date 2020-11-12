import unittest
from patch_parser import parse_comments
from archive_converter import ArchiveMessageIndex, generate_email_from_file
from message_dao import MessageDao

from test_helpers import test_data_path


class PatchParserTest(unittest.TestCase):

    def test_parse_comments_for_single_email_thread(self):
        archive_index = ArchiveMessageIndex(MessageDao())
        archive_index.update(test_data_path())
        patchset = parse_comments(
            archive_index.find(
                '<20200827144112.v2.1.I6981f9a9f0c12e60f8038f3b574184f8ffc1b9b5@changeid>'))

        self.assertTrue(len(patchset.patches) > 0)
        first_patch = patchset.patches[0]
        self.assertEqual(first_patch.set_index, 0)
        self.assertNotEqual(first_patch.text, '')
        self.assertIn('[PATCH v2 1/2] Input: i8042 - Prevent intermixing i8042 commands', first_patch.text_with_headers)
        self.assertEqual(first_patch.comments, [])

    def test_parse_comments_for_multi_email_thread_with_cover_letter(self):
        archive_index = ArchiveMessageIndex(MessageDao())
        archive_index.update(test_data_path())
        patchset = parse_comments(archive_index.find('<20200831110450.30188-1-boyan.karatotev@arm.com>'))

        self.assertEqual(len(patchset.patches), 4)
        first_patch = patchset.patches[0]
        self.assertEqual(first_patch.set_index, 1)
        self.assertIn('[PATCH v2 1/4] kselftests/arm64: add a basic Pointer Authentication test', first_patch.text_with_headers)
        self.assertNotEqual(first_patch.text, '')
        self.assertEqual(first_patch.comments, [])
        self.assertIn('[PATCH v2 2/4] kselftests/arm64: add nop checks for PAuth tests', patchset.patches[1].text_with_headers)

    def test_parse_comments_for_non_patch_email(self):
        patchset = parse_comments(generate_email_from_file(test_data_path('thread_patch0.txt')))

        self.assertEqual(len(patchset.patches), 0)

    #TODO(willliu@google.com): Add tests for Multiple patches, no cover letter


if __name__ == '__main__':
    unittest.main()
