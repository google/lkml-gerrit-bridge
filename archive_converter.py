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
import os
from typing import List, Dict
from setup_gmail import Message

class ArchiveMessageIndex(object):
    def __init__(self):
        # Maps message subject (str) to starting message of email thread
        self._key_to_thread_start : Dict[str, Message] = {}
        # Maps message.id to message
        self._messages_seen : Dict[str, Message] = {}

    def find_thread(self, key: str) -> Message:
        return self._key_to_thread_start[key]

    def update(self, data_dir: str):
        new_messages : List[Message] = []

        for filename in os.listdir(data_dir):
            if not filename.endswith(".txt"):
                continue
            email = generate_email_from_file(os.path.join(data_dir, filename))
            if email.id not in self._messages_seen:
                new_messages.append(email)
        self._add_messages_to_index(new_messages)

    def size(self):
        return len(self._messages_seen)

    def _add_messages_to_index(self, new_messages : List[Message]):
        """ Iterates through all new emails and links together emails that form a thread by populating message.children. """

        need_parent : List[Message] = []

        # First iterates through all messages to distinguish between 1.) replies and 2.) the start of a thread.
        for message in new_messages:
            if message.id not in self._messages_seen:
                self._messages_seen[message.id] = message

            # If message is a reply, it needs to be associated with an existing thread
            if message.in_reply_to is not None:
                need_parent.append(message)
                continue

            # If message doesn't have the LKML style [PATCH v4 00/11],
            # we don't need to put it in the index.
            key = message.get_key()
            if key:
                self._key_to_thread_start[key] = message

        for message in need_parent:
            if message.in_reply_to not in self._messages_seen:
                print("Could not find parent email, dropping " + message.subject)
                continue
            parent = self._messages_seen[message.in_reply_to]
            parent.children.append(message)

def find_thread(key: str) -> Message:
    archive_index = ArchiveMessageIndex()
    archive_index.update('test_data')
    return archive_index.find_thread(key)

def generate_email_from_file(file: str):
    with open(file, "r") as raw_email:
        compiled_email = email.message_from_string(raw_email.read())
        return _email_to_message(compiled_email)

def _email_to_message(compiled_email) -> Message:
    content = []
    if compiled_email.is_multipart():
        for payload in compiled_email.get_payload():
            content.append(payload.get_payload())
    else:
        content = compiled_email.get_payload()
    return Message(compiled_email['Message-Id'],
                   compiled_email['subject'],
                   compiled_email['from'],
                   compiled_email['In-Reply-To'],
                   content)