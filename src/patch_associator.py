# Copyright 2022 Google LLC
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
import abc
import re
import subprocess

from typing import Dict, List, Optional
from message import Message
from patch_parser import Patch
from message_dao import MessageDao

class PatchAssociator(object, metaclass = abc.ABCMeta):
    def __init__(self) -> None:
        pass

    @abc.abstractmethod
    def get_previous_version(self, message : Message, message_dao: MessageDao) -> Optional[Message]:
        pass

class SimplePatchAssociator(PatchAssociator):

    def __init__(self, git_path: str) -> None:
        self.git_path = git_path

    def _get_time(self, message: Message):
        return int(subprocess.check_output(
            ['git', '-C', self.git_path , 'show', '-s', '--format=%ct', message.archive_hash]))

    def _newest_first(self, candidates: List[Message]):
        candidates_with_time = [(message, self._get_time(message)) for message in candidates]
        # sort by newest commit to latest commit
        candidates_with_time.sort(key=lambda x: -x[1])
        return [message for (message, time) in candidates_with_time]

    def get_previous_version(self, message: Message, message_dao: MessageDao) -> Optional[Message]:
        version = message.version()
        if version < 2:
            return None
        candidates = message_dao.find_matching(
                     normalized_subject = message.normalized_subject, 
                     from_ = message.from_)
        candidates = self._newest_first(candidates)
        previous_version = version - 1
        with_version = re.compile(fr'\[PATCH v{previous_version}.*\]')
        without_version = re.compile(r"\[PATCH(?!.*v.*]).*]")
        for candidate in candidates:
            if with_version.match(candidate.subject):
                return candidate
            if previous_version == 1:
                # Consider subjects that don't have a version number
                if without_version.match(candidate.subject):
                    return candidate
        return None