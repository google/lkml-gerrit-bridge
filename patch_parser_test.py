import unittest
from patch_parser import parse_comments
from archive_converter import generate_email_from_file

class Patch_Parser_Test(unittest.TestCase):

    def test_parse_comments_for_single_email_thread(self):
        email = generate_email_from_file("test_data/patch6.txt")
        patchset = parse_comments(email)
        self.assertTrue(len(patchset.patches) > 0)
        self.assertTrue(patchset.patches[0].set_index == 0)
        self.assertTrue(len(patchset.patches[0].text) > 0)
        self.assertTrue(len(patchset.patches[0].text_with_headers) > 18)
        self.assertEqual(patchset.patches[0].comments, [])
        
    #TODO(willliu@google.com): Add tests for Multiple patches, no cover letter, Multiple patches with cover letter, Email no patches.
        

if __name__ == '__main__':
    unittest.main()