# Copyright 2019 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import email
from setup_gmail import Message

def generate_email_from_file(file: str):
    raw_email = open(file, "r")
    compiled_email = email.message_from_string(raw_email.read())
    raw_email.close()
    return email_to_message(compiled_email)
    
def email_to_message(compiled_email) -> Message:
    content = []
    if compiled_email.is_multipart():
        for payload in compiled_email.get_payload():
            content.append(payload.get_payload())
    else:
        content = compiled_email.get_payload()
    return Message(compiled_email['Message-Id'], compiled_email['subject'], compiled_email['from'], compiled_email['In-Reply-To'], content)

def main():
    generate_email_from_patches("test_data/patch6.txt")
    
if __name__ == "__main__":
    main()