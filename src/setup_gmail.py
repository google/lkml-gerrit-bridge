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

import re
from typing import Optional, Tuple

class Patch(object):
    def __init__(self):
        self.messages = []

class Patchset(object):
    def __init__(self):
        self.patches = []

class Message(object):
    def __init__(self, id, subject, from_, in_reply_to, content, archive_hash):
        self.id = id
        self.subject = subject
        self.from_ = from_
        self.in_reply_to = in_reply_to
        self.content = content
        self.change_id = None
        self.archive_hash = archive_hash
        self.children = []

    def get_key(self):
        match = re.match(r'\[(.+)\] .+', self.subject)
        if match:
            return match.group(1)
        else:
            return None

    def is_patch(self) -> bool:
        if re.match(r'\[.+\] .+', self.subject):
            return True
        return False

    def patch_index(self) -> Tuple[int, int]:
        if not self.is_patch():
            raise ValueError(f'Missing patch index in subject: {self.subject}')
        match = re.match(r'\[.+ (\d+)/(\d+)\] .+', self.subject)
        if match:
            return int(match.group(1)), int(match.group(2))
        return (1, 1)

    def __str__(self):
        in_reply_to = self.in_reply_to or ''
        return ('{\n' +
                'id = ' + self.id + '\n' +
                'subject = ' + self.subject + '\n' +
                'in_reply_to = ' + in_reply_to + '\n' +
                # 'content = ' + self.content + '\n' +
                '}')

    def __repr__(self):
        return str(self)

    def debug_info(self) -> str:
        return (f'Message ID: {self.id}\n'
                f'Lore Link: https://lore.kernel.org/linux-kselftest/{self.id[1:-1]}/\n'
                f'Commit Hash: {self.archive_hash}')
