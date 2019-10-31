from __future__ import print_function
from typing import Dict, List
import base64
import pickle
import os.path
import re
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from pygerrit2 import GerritRestAPI
from requests import PreparedRequest
from requests.auth import AuthBase
from http.cookiejar import CookieJar, MozillaCookieJar
from setup_gmail import Message
from setup_gmail import find_thread

def get_gerrit_rest_api(cookie_jar_path: str) -> GerritRestAPI:
    cookie_jar = MozillaCookieJar(cookie_jar_path)
    cookie_jar.load()
    auth = HTTPCookieAuth(cookie_jar)
    rest = GerritRestAPI(url='https://kunit-review.googlesource.com', auth=auth)
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

    def get_change(self, change_id: str):
        return self._rest_api.get('/changes/{change_id}'.format(change_id=change_id))

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

def main():
    rest = get_gerrit_rest_api('gerritcookies')
    gerrit = Gerrit(rest)
    #review = gerrit.get_review(change_id='1132', revision_id='72')
    #print(review)
    print(gerrit.get_patch('1132', '72'))
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
