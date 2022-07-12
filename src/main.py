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
import glob
import time

from absl import app
from absl import logging

import archive_updater
import gerrit
import git
import patch_parser

from archive_converter import ArchiveMessageIndex
from message import Message
from message_dao import MessageDao
from typing import Collection, Dict, List, Set, Tuple

GIT_PATH = '../linux-kselftest/git/0.git'
FILE_DIR = 'index_files'
GERRIT_URL = 'https://linux-review.googlesource.com'
GOB_URL = 'http://linux.googlesource.com'
COOKIE_JAR_PATH = 'gerritcookies'
LOG_PATH = 'logs'
WAIT_TIME = 10

#TODO(@willliu): consider adding more specific errors to raise, instead of a catch-all

class Server(object):
    def __init__(self, message_dao : MessageDao) -> None:
        rest = gerrit.get_gerrit_rest_api(COOKIE_JAR_PATH, GERRIT_URL)
        self.gerrit = gerrit.Gerrit(rest)
        self.gerrit_git = git.GerritGit(git_dir='gerrit_git_dir',
                                        cookie_jar_path=COOKIE_JAR_PATH,
                                        url=GOB_URL,
                                        project='linux/kernel/git/torvalds/linux',
                                        branch='master')
        self.message_dao = message_dao
        self.archive_index = ArchiveMessageIndex(self.message_dao)
        self.last_hash = self.message_dao.get_last_hash()
        archive_updater.setup_archive(GIT_PATH)
        os.makedirs(FILE_DIR, exist_ok=True)
        os.makedirs(LOG_PATH, exist_ok=True)
        logging.get_absl_handler().use_absl_log_file('server_logs', LOG_PATH)

    @staticmethod
    def remove_files(file_dir : str):
        files = glob.glob(f'{file_dir}/*')
        for f in files:
            os.remove(f)

    @staticmethod
    def split_parent_and_reply_messages(messages : List[Message]) -> Tuple[List[Message], List[Message]]:
        ''' Splits a list of messages into parent (first email in a thread) and replies. '''
        parents : List[Message] = []
        replies : List[Message] = []
        for message in messages:
                if not message.in_reply_to:
                    parents.append(message)
                    continue
                replies.append(message)
        return (parents, replies)

    def run(self) -> None:
        while True:
            self.update_convert_upload()
            time.sleep(WAIT_TIME)

    def update_convert_upload(self) -> None:
        new_messages = self.update_message_dir()

        # Differentiate between messages to upload and comments
        messages_to_upload : List[Message] = []
        messages_with_new_comments : Dict[str, Message] = {}
        parent_patches : Set[str] = set()
        replies_to_store : List[Message] = []
        # First separate between parents and replies. All parents of patchsets will be uploaded
        parents, replies = self.split_parent_and_reply_messages(new_messages.values())

        for message in parents:
            parent_patches.add(message.id)
            messages_to_upload.append(message)

        # Determine which of the replies should be uploaded
        for message in replies:
            if message.in_reply_to in parent_patches:
                replies_to_store.append(message)
                continue
            if not new_messages.get(message.in_reply_to) and not self.message_dao.get(message.in_reply_to):
                continue
            replies_to_store.append(message)
            # Reply is a patch to be uploaded (as the parent of patchset is not in new_messages)
            if message.is_patch():
                messages_to_upload.append(message)
            # Reply is a comment that's parent is not in this batch of messages. Its parent's comments should be reuploaded
            elif not message.is_coverletter():
                parent = new_messages.get(message.in_reply_to)
                if not parent:
                    parent = self.message_dao.get(message.in_reply_to)
                messages_with_new_comments[parent.id] = parent

        self.upload_messages(messages_to_upload)

        self.upload_comments(messages_with_new_comments)

        self.store_replies(replies_to_store)

        self.message_dao.store_last_hash(self.last_hash)

        self.remove_files(FILE_DIR)

    def update_message_dir(self) -> Dict[str, Message]:
        self.last_hash = archive_updater.fill_message_directory(GIT_PATH, FILE_DIR, self.last_hash)
        messages = self.archive_index.update(FILE_DIR)
        return messages

    def upload_messages(self, messages_to_upload : List[Message]):
        failed = 0
        for email_thread in messages_to_upload:
            try:
                patchset = patch_parser.parse_comments(email_thread)
                self.gerrit_git.apply_patchset_and_cleanup(patchset, email_thread, self.message_dao)
                gerrit.find_and_label_all_revision_ids(self.gerrit, patchset)
                gerrit.upload_all_comments(self.gerrit, patchset)
            except Exception as e:
                failed += 1
                failed_message = email_thread.debug_info()
                logging.exception('Failed to upload %s.', failed_message)
                continue
        if failed > 0:
            logging.warning('Failed to upload %d/%d messages', failed, len(messages_to_upload))

    def upload_comments(self, messages_with_new_comments : Dict[str, Message]):
        failed = 0
        for email_thread in messages_with_new_comments.values():
            try:
                patchset = patch_parser.parse_comments(email_thread)
                gerrit.upload_all_comments(self.gerrit, patchset)
                self.message_dao.store(email_thread)
            except Exception as e:
                failed += 1
                failed_message = email_thread.debug_info()
                logging.exception('Failed to upload comments for %s.', failed_message)
                continue
        if failed > 0:
            logging.warning('Failed to upload %d/%d comments', failed, len(messages_with_new_comments))

    def store_replies(self, replies : Collection[Message]):
        failed = 0
        for reply in replies:
            try:
                self.message_dao.store(reply)
            except Exception as e:
                failed += 1
                failed_reply = reply.debug_info()
                logging.exception('Failed to upload %s.', failed_reply)
                continue
        if failed > 0:
            logging.warning('Failed to upload %d/%d replies', failed, len(replies))

def main(argv) -> None:
    server = Server(MessageDao(GIT_PATH))
    server.run()


if __name__ == '__main__':
    app.run(main)