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

import hashlib
import os
import re
import shutil
import subprocess
import tempfile

import message_dao
from message import lore_link, Message
from patch_parser import Patch, Patchset
from absl import logging

def _git(verb: str, *args, cwd=None, input=None) -> str:
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

class _Git(object):
    def __init__(self, git_dir: str) -> None:
        self._git_dir = git_dir

    def __call__(self, verb: str, *args) -> str:
        return _git(verb, *args, cwd=self._git_dir)

    def clone(self, remote, *args) -> str:
        return _git('clone', *args, '--', remote, self._git_dir)

    def am(self, patch_contents: str) -> str:
        return _git('am', cwd=self._git_dir, input=patch_contents)

    def push(self, remote_branch: str) -> str:
        return _git('push', '-u', 'origin', remote_branch, cwd=self._git_dir)

    def config(self, config: str, option: str) -> str:
        return _git('config', '--local', config, option, cwd=self._git_dir)

    def commit(self, *args) -> str:
        return _git('commit', *args, cwd=self._git_dir)

GERRIT_CHANGE_URL_MATCHER = re.compile(
r'SUCCESS\s+remote:\s+remote:\s+(https://[\w/+.-]+)\s+',
flags=re.MULTILINE)

GERRIT_CHANGE_ID_MATCHER = re.compile(r'^https://[\w/+.-]+\+/(\d+)$')

def _parse_gerrit_patch_push(gerrit_result: str) -> str:
    logging.info('%s', gerrit_result)
    match = GERRIT_CHANGE_URL_MATCHER.search(gerrit_result)
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

class GerritGit(object):
    def __init__(self, git_dir: str, cookie_jar_path: str, url: str, project: str, branch: str) -> None:
        self._git_dir = git_dir
        self._cookie_jar_path = cookie_jar_path
        self._git = _Git(git_dir)
        self._remote = url + '/' + project
        self._branch = branch

    def _shallow_clone(self, depth=1) -> str:
        return self._git.clone(self._remote, '--depth', str(depth), '--single-branch', '--branch', self._branch)

    def _apply_patch(self, patch: Patch) -> str:
        try:
            return self._git.am(patch.text_with_headers)
        except subprocess.CalledProcessError as e:
            logging.warning('Failed to apply patch %s due to %s. Aborting...',
                            patch.message_id,
                            e.output)
            self._git('am', '--abort')
            raise

    def _set_trailers(self, patch: Patch) -> str:
        """Assuming `patch` is HEAD, edits the commit message before we upload to Gerrit.

        Note: normally, we'd rely on a commit-msg or applypatch-msg hook for this.
        But we have more context here, namely the message id so we can include a
        link to the original message in Lore.

        Args:
            patch: the patch we've just applied.
        """
        original_message = self._git('log', '-1', '--format=%B').rstrip('\n')

        # Set a deterministic Change-Id so we don't create duplicate changes.
        # See https://gerrit-review.googlesource.com/Documentation/user-changeid.html
        sha1 = hashlib.sha1(patch.message_id.encode()).hexdigest()
        change_id_trailer = f'Change-Id: I{sha1}'
        lore_trailer = 'Lore-Link: ' + lore_link(patch.message_id)

        # Add trailers, changing them if they exist.
        # It's _highly_ unlikely that they'd exist, but this seems to be the
        # most sane way of handling that edge case.
        with tempfile.NamedTemporaryFile(mode='w+') as f:
          f.write(original_message)
          f.flush() # Flush before we write to the file externally below
          self._git('interpret-trailers', '--in-place', '--if-exists=addIfDifferent',
                    '--trailer', change_id_trailer,  '--trailer', lore_trailer, f.name)
          return self._git.commit('--amend', '-F', f.name)

    def _push_changes(self) -> str:
        try:
            return self._git.push(f'HEAD:refs/for/{self._branch}%notify=NONE')
        except subprocess.CalledProcessError as e:
            logging.warning('Failed to push upstream because %s.', e.output)
            raise

    def _push_patch(self, patch: Patch) -> Patch:
        self._apply_patch(patch)
        self._set_trailers(patch)
        gerrit_output = self._push_changes()
        change_id = _parse_gerrit_patch_push(gerrit_output)
        patch.change_id = change_id
        return patch

    def _setup_git_dir(self, clone_depth=1) -> None:
        os.makedirs(self._git_dir)
        self._shallow_clone(depth=clone_depth)
        self._git.config('http.cookiefile', '../' + self._cookie_jar_path)
        self._git.config('user.name', '"lkml-gerrit-bridge"')
        # TODO: Change config to use a service account instead of @willliu
        self._git.config('user.email', '"willliu@google.com"')

    def _cleanup_git_dir(self) -> None:
        shutil.rmtree(self._git_dir)

    # Pass in the dao so that patches can be updated when they are pushed, this way less lost data when an error happens,
    # and pass in the message directly to minimize database lookups
    def apply_patchset_and_cleanup(self, patchset: Patchset, message: Message, message_dao: message_dao.MessageDao):
        if not os.path.isdir(self._git_dir):
            self._setup_git_dir()
        for patch in patchset.patches:
            # This should cause the server to clean up the git dir because of potential failures
            try:
                message.change_id = self._push_patch(patch).change_id
                message_dao.store(message)
            except:
                self._cleanup_git_dir()
                raise
