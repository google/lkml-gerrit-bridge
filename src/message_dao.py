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

import json
import os
import subprocess

from functools import lru_cache
from typing import Dict, List, Optional

from dotenv import load_dotenv
from google.cloud.sql.connector import Connector
from message import lore_link, Message, parse_message_from_str

load_dotenv()
EPOCH_HASH = 'ae9e7be4a03765456fe38287533e6446e8bbc93c'

class MessageDao(object):
    def __init__(self, archive_path: str) -> None:
        """ Creates a connection as well as two tables: Messages and States.
        Message stores the messages we've uploaded and States is a key-value
        store which tracks things like 'last_hash', the last Lore git commit
        we've processed."""
        self._initialize_connection()
        self._initialize_tables()
        self.archive_path = archive_path

    def _initialize_connection(self) -> None:
        connector = Connector()
        self.connection = connector.connect(
            os.environ.get("HOST"),
            "pymysql",
            user = os.environ.get("USER"),
            password = os.environ.get("PASSWORD")
        )

    def _initialize_tables(self) -> None:
        db_name = os.environ.get("DB")
        if not db_name:
            raise Exception("Missing environment variable for name of database.")
        with self.connection.cursor() as cursor:
            cursor.execute("CREATE DATABASE IF NOT EXISTS " + db_name)
            self.connection.select_db(db_name)
            # Mapping from message id to message
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS Messages"
                "(message_id VARCHAR(255) NOT NULL,"
                "normalized_subject VARCHAR(255) NOT NULL,"
                "from_ VARCHAR(255) NOT NULL,"
                "in_reply_to VARCHAR(255),"
                "archive_hash VARCHAR(255) NOT NULL,"
                "change_id VARCHAR(255),"
                "lore_link VARCHAR(255),"
                "PRIMARY KEY (message_id))"
            )
            # Mapping from name of state attribute to state
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS States"
                "(state_name VARCHAR(255) NOT NULL,"
                "value VARCHAR(255) NOT NULL,"
                "PRIMARY KEY (state_name))"
            )
        self.connection.commit()

    def store(self, message: Message) -> None:
        link = lore_link(message.id)
        query = "REPLACE INTO Messages VALUES (%s, %s, %s, %s, %s, %s, %s)"
        with self.connection.cursor() as cursor:
            cursor.execute(query, (message.id, message.normalized_subject, message.from_,
            message.in_reply_to, message.archive_hash, message.change_id, link))
        if message.in_reply_to:
            # Clear cache because the parent's cache is no longer valid: list of children changed
            self.get.cache_clear()
        self.connection.commit()

    def _get_children(self, message_id: str) -> List[Optional[Message]]:
        query = "SELECT * FROM Messages WHERE in_reply_to=%s"
        with self.connection.cursor() as cursor:
            cursor.execute(query, (message_id,))
            res = cursor.fetchall()
        return [self.get(tup[0]) for tup in res]

    @lru_cache
    def get(self, message_id: str) -> Optional[Message]:
        query = "SELECT archive_hash, change_id FROM Messages WHERE message_id=%s"
        with self.connection.cursor() as cursor:
            cursor.execute(query, (message_id,))
            res = cursor.fetchone()
        if res is None:
            return None
        archive_hash, change_id = res[0], res[1]
        # Recreate the message object using the archive hash
        raw_email = subprocess.check_output(['git', '-C', self.archive_path, 'show', f'{archive_hash}:m'])
        msg = parse_message_from_str(raw_email.decode(), archive_hash=archive_hash)
        msg.change_id = change_id
        msg.children = self._get_children(message_id)
        return msg

    def find_matching(self, normalized_subject: str = "", from_: str = "") -> List[Message]:
        criteria = {
            "normalized_subject": normalized_subject,
            "from_": from_
        }
    
        non_empty = [(attr, value) for attr, value in criteria.items() if value != '']
        if len(non_empty) == 0:
            raise RuntimeError("Need to specify some attribute to match on!")
        clauses = [f' {attr}=%s' for attr, _ in non_empty]
        values = [value for _, value in non_empty]

        query = "SELECT message_id FROM Messages WHERE change_id IS NOT NULL AND" + " AND".join(clauses)
        with self.connection.cursor() as cursor:
            cursor.execute(query, tuple(values))
            res = cursor.fetchall()
        return [self.get(tup[0]) for tup in res]

    def size(self) -> int:
        query = "SELECT COUNT(*) FROM Messages"
        with self.connection.cursor() as cursor:
            cursor.execute(query)
            res = cursor.fetchone()
        return res[0]

    def store_last_hash(self, last_hash: str) -> None:
        query = "REPLACE INTO States VALUES (%s, %s)"
        with self.connection.cursor() as cursor:
            cursor.execute(query, ("last_hash", last_hash))
        self.connection.commit()

    def get_last_hash(self) -> str:
        query = "SELECT value FROM States WHERE state_name=%s"
        with self.connection.cursor() as cursor:
            cursor.execute(query, ("last_hash"))
            res = cursor.fetchone()
        return EPOCH_HASH if res is None else res[0]


class FakeMessageDao(MessageDao):
    def __init__(self) -> None:
        # Maps message.id to message
        self._messages_seen = {}
        self.last_hash = EPOCH_HASH

    def store(self, message: Message) -> None:
        self._messages_seen[message.id] = message

    def get(self, message_id: str) -> Optional[Message]:
        return self._messages_seen.get(message_id)

    def size(self) -> int:
        return len(self._messages_seen)

    def store_last_hash(self, last_hash: str) -> None:
        self.last_hash = last_hash

    def get_last_hash(self) -> int:
        return self.last_hash

    def find_matching(self, normalized_subject: str = "", from_: str = "") -> List[Message]:
        criteria = {
            "normalized_subject": normalized_subject,
            "from_": from_,
        }
    
        def _Match(msg: Message):
            if msg.change_id is None:
                return False
            return all(getattr(msg, attr) == value is not None for attr, value in criteria.items() if value != "")
        
        return filter(_Match, self._messages_seen.values())