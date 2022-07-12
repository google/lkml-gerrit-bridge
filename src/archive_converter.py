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
    def __init__(self, message_dao: MessageDao) -> None:
        self._message_dao = message_dao

    def update(self, data_dir: str) -> Dict[str, Message]:
        """ Updates index with messages in the passed in directory.
        Returns a dictionary mapping new messages' ids to their corresponding message."""

        new_messages : Dict[str, Message] = {}

        for filename in os.listdir(data_dir):
            if not filename.endswith(".txt"):
                continue
            email = generate_email_from_file(os.path.join(data_dir, filename))
            if email and not self._message_dao.get(email.id):
                new_messages[email.id] = email
        self._populate_children(new_messages)
        return new_messages

    def _populate_children(self, new_messages: Dict[str, Message]) -> None:
        """ Iterates through all new emails and links together emails that form
        a thread by populating message.children. Parents from the database
        that have a new reply are added to 'new_messages' in order to be stored
        in the database once re-uploaded."""

        # Iterate through a copy of the values to avoid altering the size of the iterator
        for message in list(new_messages.values()):

            # Associate a message with an existing thread only if the message is a reply
            if message.in_reply_to is None:
                continue

            if message.in_reply_to in new_messages:
                parent = new_messages.get(message.in_reply_to)
                parent.children.append(message)
            else:
                parent = self._message_dao.get(message.in_reply_to)
                if not parent:
                    logging.info('Could not find parent email, dropping %s', message.debug_info())
                    continue
                parent.children.append(message)
                new_messages[parent.id] = parent

def generate_email_from_file(file: str) -> Optional[Message]:
    archive_hash = file[12:-4]
    with open(file, "r") as raw_email:
        try:
          return parse_message_from_str(raw_email.read(), archive_hash=archive_hash)
        except Exception as e:
            logging.error('Failed to generate %s from archive. Error: %s', archive_hash, e)
            return None
