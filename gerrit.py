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

from __future__ import print_function
from typing import Dict, List
import base64
import pickle
import os.path
import re
from git import GerritGit
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from patch_parser import map_comments_to_gerrit, parse_comments, Patch, Patchset
from pygerrit2 import GerritRestAPI
from requests import PreparedRequest
from requests.auth import AuthBase
from http.cookiejar import CookieJar, MozillaCookieJar
from setup_gmail import Message
from archive_converter import ArchiveMessageIndex
from message_dao import MessageDao

def get_gerrit_rest_api(cookie_jar_path: str, gerrit_url: str) -> GerritRestAPI:
    cookie_jar = MozillaCookieJar(cookie_jar_path)
    cookie_jar.load()
    auth = HTTPCookieAuth(cookie_jar)
    rest = GerritRestAPI(url=gerrit_url, auth=auth)
    return rest

class HTTPCookieAuth(AuthBase):
    def __init__(self, cookie_jar: CookieJar):
        self.cookie_jar = cookie_jar

    def __call__(self, request: PreparedRequest):
        request.prepare_cookies(self.cookie_jar)
        return request

class Gerrit(object):
    def __init__(self, rest_api: GerritRestAPI):
        self._rest_api = rest_api

    def new_change(self, change):
        return self._rest_api.post('/changes/', data=change)

    def get_change(self, change_id: str):
        return self._rest_api.get('/changes/{change_id}?o=CURRENT_REVISION'.format(change_id=change_id))

    def get_patch(self, change_id: str, revision_id: str):
        return self._rest_api.get(
                '/changes/{change_id}/revisions/{revision_id}/patch'.format(
                        change_id=change_id, revision_id=revision_id))

    def get_review(self, change_id: str, revision_id: str):
        return self._rest_api.get(
                '/changes/{change_id}/revisions/{revision_id}/review'.format(
                        change_id=change_id,
                        revision_id=revision_id))

    def set_review(self, change_id: str, revision_id: str, review):
        return self._rest_api.post(
                '/changes/{change_id}/revisions/{revision_id}/review'.format(
                        change_id=change_id,
                        revision_id=revision_id),
                data=review)

def find_and_label_revision_id(gerrit: Gerrit, patch: Patch):
    change_info = gerrit.get_change(patch.change_id)
    print(change_info)
    revision_id = change_info['current_revision']
    print(revision_id)
    patch.revision_id = revision_id

def find_and_label_all_revision_ids(gerrit: Gerrit, patchset: Patchset):
    for patch in patchset.patches:
        find_and_label_revision_id(gerrit, patch)

def upload_comments_for_patch(gerrit: Gerrit, patch: Patch):
    Comments = List[Dict[str,str]]

    patch_comments : List[str] = []
    file_comments : Dict[str,Comments] = {}
    for comment in patch.comments:
        if not comment.file:
            patch_comments.append(comment.message)
        else:
            file_name = comment.file
            if file_name not in file_comments:
                file_comments[file_name] = []
            comment_as_dict = {'message': comment.message}
            if comment.line:
                comment_as_dict['line'] = comment.line
            file_comments[file_name].append(comment_as_dict)
    review = {
            'tag': 'post_lkml_comments',
            'message': '\n\n'.join(patch_comments),
            'labels': {'Code-Review': 0},
            'comments': file_comments
    }
    print('review = ' + str(review))
    print('set_review response = ' + str(gerrit.set_review(change_id=patch.change_id, revision_id=patch.revision_id, review=review)))

def upload_all_comments(gerrit: Gerrit, patchset: Patchset):
    map_comments_to_gerrit(patchset)
    for patch in patchset.patches:
        upload_comments_for_patch(gerrit, patch)

def main():
    gerrit_url = 'https://linux-review.googlesource.com'
    gob_url = 'http://linux.googlesource.com'
    rest = get_gerrit_rest_api('gerritcookies', gerrit_url)
    gerrit = Gerrit(rest)
    gerrit_git = GerritGit(git_dir='gerrit_git_dir',
                           cookie_jar_path='gerritcookies',
                           url=gob_url, project='linux/kernel/git/torvalds/linux', branch='master')
    archive_index = ArchiveMessageIndex(MessageDao())
    archive_index.update('test_data')
    email_thread = archive_index.find('<20200831110450.30188-1-boyan.karatotev@arm.com>')
    patchset = parse_comments(email_thread)
    gerrit_git.apply_patchset_and_cleanup(patchset)
    find_and_label_all_revision_ids(gerrit, patchset)
    upload_all_comments(gerrit, patchset)
    #change = {
    #        'project': 'linux',
    #        'branch': 'kernel/git/torvalds/linux/',
    #        'subject': 'Testing...',
    #}
    #print(gerrit.new_change(change=change))
    #review = gerrit.get_review(change_id='1132', revision_id='72')
    #print(review)
    #print(gerrit.get_patch('1132', '72'))
    # review = {
    #         'tag': 'post_lkml_comments',
    #         'message': 'Some comments from LKML',
    #         'labels': {'Code-Review': 0},
    #         'comments': {
    #                 'MAINTAINERS': [{
    #                         'line': 8609,
    #                         'message': 'This is a comment.',
    #                 }],
    #         }
    # }
    # print(gerrit.set_review(change_id='1132', revision_id='72', review=review))

if __name__ == '__main__':
    main()
