# Copyright 2020 Google LLC
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

import os

from absl import logging

from typing import List, Dict, Optional
from message import Message, parse_message_from_str
from message_dao import MessageDao

class ArchiveMessageIndex(object):
    def __init__(self, message_dao : MessageDao) -> None:
        self._message_dao = message_dao

    def update(self, data_dir: str) -> List[Message]:
        """ Updates index with messages in the passed in directory.
        Returns a list of new messages """

        new_messages : List[Message] = []

        for filename in os.listdir(data_dir):
            if not filename.endswith(".txt"):
                continue
            email = generate_email_from_file(os.path.join(data_dir, filename))
            if email and not self._message_dao.get(email.id):
                new_messages.append(email)
        self._add_messages_to_index(new_messages)
        return new_messages

    def size(self):
        return self._message_dao.size()

    def find(self, message_id : str) -> Message:
        message = self._message_dao.get(message_id)
        if message is None:
            raise ValueError(f'Could not find message: {message_id}')
        return message

    def _add_messages_to_index(self, new_messages : List[Message]):
        """ Iterates through all new emails and links together emails that form a thread by populating message.children. """

        need_parent : List[Message] = []

        # First iterates through all messages to distinguish between 1.) replies and 2.) the start of a thread.
        for message in new_messages:
            if not self._message_dao.get(message.id):
                self._message_dao.store(message)

            # If message is a reply, it needs to be associated with an existing thread
            if message.in_reply_to is not None:
                need_parent.append(message)
                continue

        for message in need_parent:
            parent = self._message_dao.get(message.in_reply_to)
            if not parent:
                logging.info('Could not find parent email, dropping %s', message.debug_info())
                continue
            parent.children.append(message)
            self._message_dao.store(parent)

def generate_email_from_file(file: str) -> Optional[Message]:
    archive_hash = file[12:-4]
    with open(file, "r") as raw_email:
        try:
          return parse_message_from_str(raw_email.read(), archive_hash=archive_hash)
        except Exception as e:
            logging.error('Failed to generate %s from archive. Error: %s', archive_hash, e)
            return None
