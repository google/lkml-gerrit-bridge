import unittest
from archive_converter import generate_email_from_file

class TestStringMethods(unittest.TestCase):

    def test_generate_email_from_single_email_thread(self):
        email = generate_email_from_file("test_data/patch6.txt")
        self.assertEqual(email.subject, '[PATCH v2 1/2] Input: i8042 - Prevent intermixing i8042 commands')
        self.assertEqual(email.in_reply_to, None)
        self.assertEqual(email.from_, "Raul E Rangel <rrangel@chromium.org>")
        self.assertTrue(len(email.content) > 0)
        

if __name__ == '__main__':
    unittest.main()