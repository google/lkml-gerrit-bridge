import unittest
from patch_parser import parse_comments
from archive_converter import find_thread, generate_email_from_file

class PatchParserTest(unittest.TestCase):

    def test_parse_comments_for_single_email_thread(self):
        patchset = parse_comments(find_thread('PATCH v2 1/2'))

        self.assertTrue(len(patchset.patches) > 0)
        first_patch = patchset.patches[0]
        self.assertEqual(first_patch.set_index, 0)
        self.assertNotEqual(first_patch.text, '')
        self.assertIn('[PATCH v2 1/2] Input: i8042 - Prevent intermixing i8042 commands', first_patch.text_with_headers)
        self.assertEqual(first_patch.comments, [])

    def test_parse_comments_for_multi_email_thread_with_cover_letter(self):
        patchset = parse_comments(find_thread('PATCH v2 0/4'))

        self.assertEqual(len(patchset.patches), 4)
        first_patch = patchset.patches[0]
        self.assertEqual(first_patch.set_index, 1)
        self.assertIn('[PATCH v2 1/4] kselftests/arm64: add a basic Pointer Authentication test', first_patch.text_with_headers)
        self.assertNotEqual(first_patch.text, '')
        self.assertEqual(first_patch.comments, [])
        self.assertIn('[PATCH v2 2/4] kselftests/arm64: add nop checks for PAuth tests', patchset.patches[1].text_with_headers)

    def test_parse_comments_for_non_patch_email(self):
        patchset = parse_comments(generate_email_from_file('test_data/thread_patch0.txt'))

        self.assertEqual(len(patchset.patches), 0)

    #TODO(willliu@google.com): Add tests for Multiple patches, no cover letter


if __name__ == '__main__':
    unittest.main()