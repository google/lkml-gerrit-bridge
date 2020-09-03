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
from patch_parser import Patch, Patchset

def git(verb: str, *args, cwd=None, input=None) -> str:
    print(args)
    print(list(args))
    result = subprocess.run(['git', verb] + list(args),
                            cwd=cwd, input=input,
                            text=True,
                            stderr=subprocess.STDOUT,
                            stdout=subprocess.PIPE)
    stdout = str(result.stdout)
    print('stdout: ' + stdout)
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
    print(gerrit_result)
    match = GERRIT_PUSH_MATCHER.search(gerrit_result)
    if match is None:
      raise ValueError(f'Could not find change url from gerrit output: {gerrit_result}')
    change_url = match.group(1)
    print('change_url = ' + change_url)

    match = GERRIT_CHANGE_ID_MATCHER.match(change_url)
    if match is None:
      raise ValueError(f'Could not extract change id from gerrit output: {gerrit_result}')
    change_id = match.group(1)
    print('change_id = ' + change_id)
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
        print(patch.text_with_headers)
        return self._git.am(patch.text_with_headers)

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

    def apply_patchset_and_cleanup(self, patchset: Patchset):
        self.setup_git_dir()
        for patch in patchset.patches:
            self.push_patch(patch)
        self.cleanup_git_dir()
