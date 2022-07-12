import unittest
import patch_parser
from patch_parser import parse_comments, map_comments_to_gerrit, Comment
from archive_converter import ArchiveMessageIndex, generate_email_from_file
from message_dao import FakeMessageDao

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
        archive_index = ArchiveMessageIndex(FakeMessageDao())
        archives = archive_index.update(test_data_path())
        patchset = parse_comments(
            archives.get(
                '<20200827144112.v2.1.I6981f9a9f0c12e60f8038f3b574184f8ffc1b9b5@changeid>'))

        self.assertTrue(len(patchset.patches) > 0)
        first_patch = patchset.patches[0]
        self.assertEqual(first_patch.set_index, 0)
        self.assertNotEqual(first_patch.text, '')
        self.assertIn('[PATCH v2 1/2] Input: i8042 - Prevent intermixing i8042 commands', first_patch.text_with_headers)
        self.assertEqual(first_patch.comments, [])

    def test_parse_comments_for_multi_email_thread_with_cover_letter(self):
        archive_index = ArchiveMessageIndex(FakeMessageDao())
        archives = archive_index.update(test_data_path())
        patchset = parse_comments(archives.get('<20200831110450.30188-1-boyan.karatotev@arm.com>'))

        self.assertEqual(len(patchset.patches), 4)
        first_patch = patchset.patches[0]
        self.assertEqual(first_patch.set_index, 1)
        self.assertIn('[PATCH v2 1/4] kselftests/arm64: add a basic Pointer Authentication test',
                      first_patch.text_with_headers)
        self.assertNotEqual(first_patch.text, '')
        self.assertEqual(first_patch.comments, [])
        self.assertIn('[PATCH v2 2/4] kselftests/arm64: add nop checks for PAuth tests',
                      patchset.patches[1].text_with_headers)

    def test_parse_comments_for_non_patch_email(self):
        patchset = parse_comments(generate_email_from_file(test_data_path('thread_patch0.txt')))

        self.assertEqual(len(patchset.patches), 0)

    def test_parse_with_replies(self):
        archive_index = ArchiveMessageIndex(FakeMessageDao())
        archives = archive_index.update(test_data_path('fake_patch_with_replies/'))

        self.assertEqual(len(archives), 2)

        patchset = parse_comments(archives.get('<patch-message-id>'))
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
                    line=7,  # TODO: should be 5
                    message='Comment on old line 5, want on line 5 in new file.'),
            Comment(raw_line=20,
                    file='file',
                    line=9,  # TODO: should be 7
                    message='Comment on old line 7, want on line 8 in new file.'),
        ])

    def test_one_modified_line(self):
        raw_patch = '''
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
             - line 4
             + line 4 - edit
             line 5
             line 6
             line 7  # this is line 16 in raw_patch

            base-commit: 235360eb7cd778d7264c5e57358a3d144936b862
            --
                    '''.strip()
        line_map = patch_parser._parse_git_patch(raw_patch)
        self.assertEqual(line_map.map(11), ('file', 2), msg=repr(line_map))  # line 2, control assert
        self.assertEqual(line_map.map(13), ('fileb', 4), msg=repr(line_map))  # line 4 (deleted part due to edition)
        self.assertEqual(line_map.map(14), ('file', 5), msg=repr(line_map))  # line 4 the modified line
        self.assertEqual(line_map.map(16), ('file', 7), msg=repr(line_map))  # line 7, control assert

    def test_one_deleted_line(self):
        raw_patch = '''
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
                     - line 4
                     line 5 (then 4)
                     line 6 (then 5)
                     line 7  # this is line 16 in raw_patch

                    base-commit: 235360eb7cd778d7264c5e57358a3d144936b862
                    --
                            '''.strip()
        line_map = patch_parser._parse_git_patch(raw_patch)
        self.assertEqual(line_map.map(11), ('file', 2), msg=repr(line_map))  # line 2, control assert
        self.assertEqual(line_map.map(13), ('fileb', 4), msg=repr(line_map))  # line 4 (deleted but shows in b file)

    def test_many_deleted_lines(self):
        raw_patch = '''
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
                     line 3 - 12
                     - line 4 13
                     - line 5 14
                     - line 6 15
                     - line 7 16
                     line 8 (then 4) -17
                     line 9 (then 5) -18
                     line 10  (then 6) # this is line 19 in raw_patch

                    base-commit: 235360eb7cd778d7264c5e57358a3d144936b862
                    --
                            '''.strip()
        line_map = patch_parser._parse_git_patch(raw_patch)
        self.assertEqual(line_map.map(11), ('file', 2), msg=repr(line_map))  # line 2 (11), control assert
        self.assertEqual(line_map.map(12), ('file', 3), msg=repr(line_map))  # line 3 (12), control assert
        self.assertEqual(line_map.map(13), ('fileb', 4), msg=repr(line_map))  # Lines 13 - 16 are deleted and should
        self.assertEqual(line_map.map(14), ('fileb', 5), msg=repr(line_map))  # show on 'fileb' with their
        self.assertEqual(line_map.map(15), ('fileb', 6), msg=repr(line_map))  # corresponding numbers.
        self.assertEqual(line_map.map(16), ('fileb', 7), msg=repr(line_map))
        self.assertEqual(line_map.map(17), ('file', 4), msg=repr(line_map))  # This are control lines, since they aren't
        self.assertEqual(line_map.map(18), ('file', 5), msg=repr(line_map))  # aren't modified but they will break if
        self.assertEqual(line_map.map(19), ('file', 6), msg=repr(line_map))  # there's an issue with the numbering.

    def test_only_new_lines_patch(self):
        raw_patch = '''
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
    +  inserted new line
    +  inserted new line
    +  inserted new line
     line 5
     line 6
     line 7  # this is line 19 in raw_patch

    base-commit: 235360eb7cd778d7264c5e57358a3d144936b862
    --
            '''.strip()
        line_map = patch_parser._parse_git_patch(raw_patch)
        self.assertEqual(line_map.map(11), ('file', 2), msg=repr(line_map))  # line 2
        self.assertEqual(line_map.map(13), ('file', 4), msg=repr(line_map))  # line 4

    def test_parse_git_patch(self):
        raw_patch = '''
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
        print('line map first')
        print(line_map)
        print('line map end')

        # print(line_map.map(15))

        # Line 8 is right before the start of the diff
        self.assertEqual(line_map.map(10), ('', -1), msg=repr(line_map))
        self.assertEqual(line_map.map(11), ('file', 2), msg=repr(line_map))
        self.assertEqual(line_map.map(12), ('file', 3), msg=repr(line_map))
        self.assertEqual(line_map.map(13), ('file', 4), msg=repr(line_map))
        self.assertEqual(line_map.map(14), ('fileb', 5), msg=repr(line_map))
        # self.assertEqual(line_map.map(15), ('file', 5), msg=repr(line_map)) # here the off by one starts
        # TODO: fix this, it's off by one right now.
        # Corresponds to line 8 in the original, but line 9 after the diff.
        # self.assertEqual(line_map.map(19), ('file', 9), msg=repr(line_map))

    # TODO(willliu@google.com): Add tests for Multiple patches, no cover letter


if __name__ == '__main__':
    unittest.main()
