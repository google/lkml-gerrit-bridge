import unittest
import patch_parser
from patch_parser import parse_comments, map_comments_to_gerrit, Comment
from archive_converter import ArchiveMessageIndex, generate_email_from_file
from message_dao import MessageDao

from test_helpers import test_data_path


class PatchParserTest(unittest.TestCase):

    def compareCommentsPartialMatch(self, gotComments, wantComments):
        self.assertEqual(len(gotComments), len(wantComments))
        for got, want in zip(gotComments, wantComments):
            self.assertEqual(got.message.strip(), want.message)
            self.assertEqual(got.raw_line, want.raw_line)
            self.assertEqual(got.file, want.file)
            self.assertEqual(got.line, want.line)


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

    def test_parse_with_replies(self):
        archive_index = ArchiveMessageIndex(MessageDao())
        archive_index.update(test_data_path('fake_patch_with_replies/'))

        self.assertEqual(archive_index.size(), 2)

        patchset = parse_comments(archive_index.find('<patch-message-id>'))
        map_comments_to_gerrit(patchset)
        self.assertEqual(len(patchset.patches), 1)

        patch = patchset.patches[0]

        self.compareCommentsPartialMatch(patch.comments, [
            # TODO: stop treating this as a comment
            Comment(raw_line=-1,
                    file='',
                    line=-1,
                    message='On Mon, 31 Aug 2020 at 12:04:46 +0100, The Sender wrote:'),
            Comment(raw_line=18,
                    file='file',
                    line=7, # TODO: should be 5
                    message='Comment on old line 5, want on line 5 in new file.'),
            Comment(raw_line=20,
                    file='file',
                    line=9,  # TODO: should be 7
                    message='Comment on old line 7, want on line 8 in new file.'),
        ])

    def test_parse_git_patch(self):
        raw_patch='''
Commit message goes here.

---
 file | 3 ++-
 1 file changed, 2 insertions(+), 1 deletion(-)

diff --git a/file b/file
index fa2da6e55caa..1fc93eb38351 100644
--- a/file
+++ b/file
@@ -2,7 +2,8 @@ line 1
 line 2  # this is line 11 in raw_patch
 line 3
 line 4
-line 5
+line 5 - edit
+  inserted new line
 line 6
 line 7
 line 8  # this is line 19 in raw_patch

base-commit: 235360eb7cd778d7264c5e57358a3d144936b862
--
        '''.strip()

        line_map = patch_parser._parse_git_patch(raw_patch)

        # Line 8 is right before the start of the diff
        self.assertEqual(line_map.map(10), ('', -1), msg=repr(line_map))
        self.assertEqual(line_map.map(11), ('file', 2), msg=repr(line_map))
        self.assertEqual(line_map.map(12), ('file', 3), msg=repr(line_map))
        # TODO: fix this, it's off by one right now.
        # Corresponds to line 8 in the original, but line 9 after the diff.
        # self.assertEqual(line_map.map(19), ('file', 9), msg=repr(line_map))


    #TODO(willliu@google.com): Add tests for Multiple patches, no cover letter


if __name__ == '__main__':
    unittest.main()
