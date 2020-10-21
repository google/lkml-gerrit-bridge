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

import os
import re
import shutil
import subprocess
import message_dao
from patch_parser import Patch, Patchset
from absl import logging

def git(verb: str, *args, cwd=None, input=None) -> str:
    logging.debug('Running\ngit %s %s\n with input: %s', verb, ' '.join(args), input)
    result = subprocess.run(['git', verb] + list(args),
                            cwd=cwd, input=input,
                            text=True,
                            check = True,
                            stderr=subprocess.STDOUT,
                            stdout=subprocess.PIPE)
    stdout = str(result.stdout)
    logging.info('git %s stdout: %s', verb, stdout)
    return stdout

class Git(object):
    def __init__(self, git_dir: str):
        self._git_dir = git_dir

    def clone(self, remote, *args):
        return git('clone', *args, '--', remote, self._git_dir)

    def am(self, patch_contents: str):
        return git('am', cwd=self._git_dir, input=patch_contents)

    def push(self, remote_branch: str) -> str:
        return git('push', '-u', 'origin', remote_branch, cwd=self._git_dir)

    def config(self, config: str, option: str):
        return git('config', '--local', config, option, cwd=self._git_dir)

    def commit(self, *args):
        return git('commit', *args, cwd=self._git_dir)

GERRIT_PUSH_MATCHER = re.compile(
r'remote: Processing changes: refs: 1, new: 1, done(?:\s+remote: (?:(?:commit)|(?:warning)).+$)?\s+remote:\s+remote: SUCCESS\s+remote:\s+remote:\s+(https://[\w/+.-]+)\s+',
flags=re.MULTILINE)

GERRIT_CHANGE_ID_MATCHER = re.compile(r'^https://[\w/+.-]+\+/(\d+)$')

def _parse_gerrit_patch_push(gerrit_result: str) -> str:
    logging.info('%s', gerrit_result)
    match = GERRIT_PUSH_MATCHER.search(gerrit_result)
    if match is None:
      raise ValueError(f'Could not find change url from gerrit output: {gerrit_result}')
    change_url = match.group(1)
    logging.info('change_url = %s', change_url)

    match = GERRIT_CHANGE_ID_MATCHER.match(change_url)
    if match is None:
      raise ValueError(f'Could not extract change id from gerrit output: {gerrit_result}')
    change_id = match.group(1)
    logging.info('change_id = %s', change_id)
    return change_id

CURL_CHANGE_ID_CMD = 'curl -Lo `git rev-parse --git-dir`/hooks/commit-msg https://gerrit-review.googlesource.com/tools/hooks/commit-msg ; chmod +x `git rev-parse --git-dir`/hooks/commit-msg'

class GerritGit(object):
    def __init__(self, git_dir: str, cookie_jar_path: str, url: str, project: str, branch: str):
        self._git_dir = git_dir
        self._cookie_jar_path = cookie_jar_path
        self._git = Git(git_dir)
        self._remote = url + '/' + project
        self._branch = branch

    def shallow_clone(self, depth=1):
        return self._git.clone(self._remote, '--depth', str(depth), '--single-branch', '--branch', self._branch)

    def amend_commit(self):
        return self._git.commit('--amend', '--no-edit')

    def apply_patch(self, patch: Patch):
        try:
            output = self._git.am(patch.text_with_headers)
            return output
        except subprocess.CalledProcessError:
            logging.warning('Failed to apply patch %s. Aborting...', patch.message_id)
            git('am', '--abort', cwd=self._git_dir)
            raise

    def push_changes(self):
        return self._git.push('HEAD:refs/for/' + self._branch)

    def push_patch(self, patch: Patch) -> Patch:
        self.apply_patch(patch)
        self.amend_commit()
        gerrit_output = self.push_changes()
        change_id = _parse_gerrit_patch_push(gerrit_output)
        patch.change_id = change_id
        return patch

    def setup_git_dir(self, clone_depth=1):
        os.makedirs(self._git_dir)
        self.shallow_clone(depth=clone_depth)
        self._git.config('http.cookiefile', '../' + self._cookie_jar_path)
        subprocess.run(CURL_CHANGE_ID_CMD, cwd=self._git_dir, shell=True)

    def cleanup_git_dir(self):
        shutil.rmtree(self._git_dir)

    # Pass in the dao so that patches can be updated when they are pushed, this way less lost data when an error happens
    def apply_patchset_and_cleanup(self, patchset: Patchset, messages_dao: message_dao.MessageDao):
        if not os.path.isdir(self._git_dir):
            self.setup_git_dir()
        for patch in patchset.patches:
            # This should cause the server to clean up the git dir because of potential failures
            try:
                message = messages_dao.get(patch.message_id)
                if message:
                    message.change_id = self.push_patch(patch).change_id
                    messages_dao.store(message)
            except:
                self.cleanup_git_dir()
                raise


