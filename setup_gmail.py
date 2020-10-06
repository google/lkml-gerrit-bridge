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
import base64
import pickle
import os.path
import re
from typing import Optional
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

class Patch(object):
    def __init__(self):
        self.messages = []

class Patchset(object):
    def __init__(self):
        self.patches = []

class MessageKey(object):
    def __init__(self, key: str):
        self.key = key

class PatchsetFetcher(object):
    def fetch_patchset(self, key: MessageKey) -> Patchset:
        raise NotImplementedError()

class Thread(object):
    def __init__(self, key: MessageKey, message_ids=[]):
        self.key = key
        self.message_id = message_ids

class Message(object):
    def __init__(self, id, subject, from_, in_reply_to, content):
        self.id = id
        self.subject = subject
        self.from_ = from_
        self.in_reply_to = in_reply_to
        self.content = content
        self.children = []

    def get_key(self):
        match = re.match(r'\[(.+)\] .+', self.subject)
        if match:
            return match.group(1)
        else:
            return None
        
    def is_patch(self) -> bool:
        if re.match(r'\[.+ (\d+)/(\d+)\] .+', self.subject):
            return True
        return False

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

def look_up_label_id(service, label_name):
    results = service.users().labels().list(userId='me').execute()
    labels = results.get('labels', [])
    for label in labels:
        print(label['name'])
    labels = [label for label in labels if label['name'] == label_name]
    assert len(labels) == 1
    return labels[0]['id']

def get_subject(raw_message) -> str:
    for header in raw_message['payload']['headers']:
        if header['name'].lower() == 'subject':
            return header['value']
    return ''

def get_from(raw_message) -> str:
    for header in raw_message['payload']['headers']:
        if header['name'].lower() == 'from':
            return header['value']
    return ''

def get_message_id(raw_message) -> str:
    for header in raw_message['payload']['headers']:
        if header['name'].lower() == 'message-id':
            return header['value']
    return ''

def get_in_reply_to(raw_message) -> Optional[str]:
    for header in raw_message['payload']['headers']:
        if header['name'].lower() == 'in-reply-to':
            return header['value']
    return None

class GmailMessageIndex(object):
    def __init__(self, service, label_name):
        self._service = service
        self._patchset_label_id = look_up_label_id(service, label_name)
        self._lookup_index = {} # Maps MessageKey to Thread
        self._messages_seen = {} # Maps message.id to message
        self._deserialize()

    def _deserialize(self):
        if os.path.exists('index.pickle'):
            with open('index.pickle', 'rb') as index:
                self._lookup_index, self._messages_seen = pickle.load(index)

    def _serialize(self):
        with open('index.pickle', 'wb') as index:
            pickle.dump((self._lookup_index, self._messages_seen), index)

    def find_thread(self, key: str) -> Message:
        return self._lookup_index[key]

    def update(self):
        fully_updated = False
        next_page_token = None
        new_messages = []
        while not fully_updated:
            response = self._service.users().messages().list(
                    userId='me',
                    labelIds=[self._patchset_label_id],
                    pageToken=next_page_token).execute()
            print('Found ' + str(len(response['messages'])) + ' new messages')
            if self._check_if_messages_seen(response['messages'], new_messages) or 'nextPageToken' not in response:
                break
            else:
                next_page_token = response['nextPageToken']
        self._add_messages_to_index(new_messages)
        self._serialize()

    def _check_if_messages_seen(self, message_candidates, new_messages) -> bool:
        """Returns True if it has seen some of the messages before"""
        for raw_message in message_candidates:
            raw_message = self._service.users().messages().get(
                    userId='me', id=raw_message['id']).execute()
            if get_message_id(raw_message) in self._messages_seen:
                return True
            body = base64.urlsafe_b64decode(raw_message['payload']['body']
                                            .get('data', '').encode('ASCII')).decode('utf-8')
            message = Message(id=get_message_id(raw_message),
                              subject=get_subject(raw_message),
                              from_=get_from(raw_message),
                              in_reply_to=get_in_reply_to(raw_message),
                              content=body)
            new_messages.append(message)
        return False

    def _add_messages_to_index(self, new_messages):
        need_parent = []
        for message in new_messages:
            self._messages_seen[message.id] = message

            if message.in_reply_to is None:
                key = message.get_key()
                if key:
                    self._lookup_index[key] = message
                else:
                    # If message doesn't have the LKML style [PATCH v4 00/11],
                    # we don't need to put it in the index.
                    continue
            else:
                need_parent.append(message)
        for message in need_parent:
            if message.in_reply_to not in self._messages_seen:
                # If we don't have the parent message, then we can't reconstruct
                # the patchset for this group of emails anyway, so just skip.
                continue
            parent = self._messages_seen[message.in_reply_to]
            parent.children.append(message)


def get_service():
    creds = get_credentials_or_setup()
    return build('gmail', 'v1', credentials=creds)

class GmailPatchsetFetcher(object):
    def fetch_patchset(self, key: MessageKey) -> Patchset:
        raise NotImplementedError()

    def _get_service(self):
        creds = get_credentials_or_setup()
        service = build('gmail', 'v1', credentials=creds)

def get_credentials_or_setup():
    """Shows basic usage of the Gmail API.
    Lists the user's Gmail labels.
    """
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
            creds = flow.run_local_server()
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return creds

def print_message_tree(message, prefix=''):
    print(prefix + message.subject)
    for message in message.children:
        print_message_tree(message, prefix=prefix + '  ')

def find_thread(key: str) -> Message:
    service = get_service()
    message_index = GmailMessageIndex(service=service, label_name='KUnit Patchset')
    message_index.update()
    return message_index.find_thread(key)

def main():
    service = get_service()
    message_index = GmailMessageIndex(service=service, label_name='KUnit Patchset')
    message_index.update()
    message = message_index.find_thread('PATCH v5 00/18')
    print_message_tree(message)


if __name__ == '__main__':
    main()
