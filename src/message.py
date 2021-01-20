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
import re
from typing import List, Optional, Tuple, BinaryIO

def lore_link(message_id: str) -> str:
    # We store message ids enclosed in <>, so trim those off.
    return 'https://lore.kernel.org/linux-kselftest/' + message_id[1:-1]

class Message(object):
    def __init__(self, id, subject, from_, in_reply_to, content, archive_hash) -> None:
        self.id = id
        self.subject = subject
        self.from_ = from_
        self.in_reply_to = in_reply_to
        self.content = content
        self.change_id = None
        self.archive_hash = archive_hash
        self.children = []  # type: List[Message]

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

    def __str__(self) -> str:
        in_reply_to = self.in_reply_to or ''
        return ('{\n' +
                'id = ' + self.id + '\n' +
                'subject = ' + self.subject + '\n' +
                'in_reply_to = ' + in_reply_to + '\n' +
                # 'content = ' + self.content + '\n' +
                '}')

    def __repr__(self) -> str:
        return str(self)

    def debug_info(self) -> str:
        return (f'Message ID: {self.id}\n'
                f'Lore Link: {lore_link(self.id)}\n'
                f'Commit Hash: {self.archive_hash}')

def parse_message_from_bytes(raw_email: bytes, archive_hash: str) -> Message:
    """Parses a Message from a raw email."""
    # Apparently email.message_from_{string|bytes|file} does not use the content
    # charset in the header to decode the payload so we have to do that
    # ourselves.
    header = email.parser.BytesHeaderParser().parsebytes(raw_email)
    charset = header.get_content_charset() or 'utf-8'
    compiled_email = email.message_from_string(raw_email.decode(charset))

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
                   content,
                   archive_hash)
