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

from typing import Dict, List, Optional, Tuple
import base64
import pickle
import os.path
import re
from absl import logging
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from setup_gmail import Message
from setup_gmail import find_thread

class Comment(object):
    def __init__(self, raw_line, message):
        self.raw_line = raw_line
        self.message = message
        self.children = []
        self.line = None
        self.file = None

class CoverLetter(object):
    def __init__(self, text, comments):
        self.text = text
        self.comments = comments

class Patch(object):
    def __init__(self, message_id, text, text_with_headers, set_index, comments, change_id):
        self.message_id = message_id
        self.text = text
        self.text_with_headers = text_with_headers
        self.set_index = set_index
        self.comments = comments
        self.change_id = change_id
        self.revision_id = None

class Patchset(object):
    def __init__(self, cover_letter, patches):
        self.cover_letter = cover_letter
        self.patches = patches

class Line(object):
    def __init__(self, line_number, text):
        self.line_number = line_number
        self.text = text

class QuotedLine(object):
    def __init__(self, parent_line_number, child_line_number, text):
        self.parent_line_number = parent_line_number
        self.child_line_number = child_line_number
        self.text = text

class CommentLine(object):
    def __init__(self, last_parent_line_number, child_line_number, text):
        self.last_parent_line_number = last_parent_line_number
        self.child_line_number = child_line_number
        self.text = text

class ProbablyQuoted(Line):
    def __init__(self, parent_line_number, child_line_number, text):
        self.parent_line_number = parent_line_number
        self.child_line_number = child_line_number
        self.line_number = child_line_number
        self.text = text

    def score(self) -> float:
        return 0.5

def line_iter(string: str):
    return iter(string.splitlines())

class Trie(object):
    def __init__(self):
        self._children = {}

    def insert(self, string: List[str]) -> None:
        if not string:
            return
        letter = string.pop(0)
        if letter not in self._children:
            self._children[letter] = TrieNode(letter)
        node = self._children[letter]
        node.insert(string)

    def diff_best_match(self, string: List[str]) -> List[str]:
        if not string:
            return []
        letter = string.pop(0)
        if letter not in self._children:
            string.insert(0, letter)
            return string
        node = self._children[letter]
        return node.diff_best_match(string)

class TrieNode(object):
    def __init__(self, letter):
        self._letter = letter
        self._children = {}
        self._leaf = False

    def insert(self, string: List[str]) -> None:
        if not string:
            self._leaf = True
            return
        letter = string.pop(0)
        if letter not in self._children:
            self._children[letter] = TrieNode(letter)
        node = self._children[letter]
        node.insert(string)

    def diff_best_match(self, string: List[str]) -> List[str]:
        if not string:
            return []
        letter = string.pop(0)
        if letter not in self._children:
            string.insert(0, letter)
            return string
        node = self._children[letter]
        return node.diff_best_match(string)

def get_quote_prefix(parent_lines: List[Line], child_lines: List[Line]) -> str:
    trie = Trie()
    for line in parent_lines:
        text = list(line.text)
        text.reverse()
        trie.insert(text)
    prefix_count_map = {}
    for line in child_lines:
        text = list(line.text)
        text.reverse()
        prefix = trie.diff_best_match(text)
        prefix.reverse()
        prefix_str = ''.join(prefix)
        if prefix_str not in prefix_count_map:
            prefix_count_map[prefix_str] = 1
        else:
            prefix_count_map[prefix_str] += 1
    prefix_str, count = max(prefix_count_map.items(), key=lambda x: x[1])
    return prefix_str

def build_traversal_map(parent_lines: List[Line], child_lines: List[Line], quote_prefix: str) -> Dict[str, List[Line]]:
    parent_line_set = set([line.text for line in parent_lines])
    traversal_map : Dict[str, List[Line]] = {}
    for line in child_lines:
        line_text = line.text
        if not line_text.startswith(quote_prefix):
            # TODO(brendanhiggins@google.com): I should really add this to the
            # comment_lines or something.
            continue
        line_text = line_text[len(quote_prefix):]
        if line_text in parent_line_set:
            if line_text not in traversal_map:
                traversal_map[line_text] = []
            traversal_map[line_text].append(line)
        else:
            # TODO(brendanhiggins@google.com): I should really add this to the
            # comment_lines or something.
            continue
    return traversal_map

def find_maximal_map_traversal(traversal_map: Dict[str, List[Line]],
                               parent_lines: List[Line],
                               lines_so_far: List[QuotedLine]) -> List[QuotedLine]:
    logging.info('len(parent_lines) = %d', len(parent_lines))
    if not parent_lines:
        return lines_so_far
    parent_lines = parent_lines[:]
    last_line = -1
    if lines_so_far:
        last_line = lines_so_far[-1].child_line_number
    else:
        lines_so_far = []
    while parent_lines:
        line = parent_lines.pop(0)
        if line.text not in traversal_map:
            continue
        possible_matches = traversal_map[line.text]
        possible_matches = [match for match in possible_matches if match.line_number > last_line]
        if not possible_matches:
            continue
        possible_matches = [min(possible_matches, key=lambda x: x.line_number)]
        # TODO(brendanhiggins@google.com): At the very least this recursion
        # should probably be unrolled.
        #
        # Possibly not necessary, but I suspect that there is a Thompson VM
        # style algorithmic improvement here.
        possible_traversals = [find_maximal_map_traversal(
                traversal_map,
                parent_lines,
                lines_so_far + [
                        QuotedLine(text=line.text,
                                   parent_line_number=line.line_number,
                                   child_line_number=match.line_number)])
                               for match in possible_matches]
        return max(possible_traversals, key=lambda x: len(x))
    return lines_so_far

def find_quoted_lines_max_traversal_method(
        parent_lines: List[Line],
        child_lines: List[Line]) -> Tuple[List[QuotedLine], str]:
    quote_prefix = get_quote_prefix(parent_lines, child_lines)
    traversal_map = build_traversal_map(parent_lines, child_lines, quote_prefix)
    return find_maximal_map_traversal(traversal_map, parent_lines, []), quote_prefix

NORMALIZE_WHITESPACE_MATCHER = re.compile(r'\s+')

def normalize_whitespace(string: str) -> str:
    return NORMALIZE_WHITESPACE_MATCHER.sub(' ', string)

def find_quoted_lines(parent_lines: List[Line],
                      child_lines: List[Line]) -> Tuple[List[QuotedLine], str]:
    quote_prefix = get_quote_prefix(parent_lines, child_lines)
    parent_line_set = {}
    for line in parent_lines:
        parent_line_set[normalize_whitespace(line.text)] = line
    quoted_lines = []
    for line in child_lines:
        line_text = line.text
        if not line_text.startswith(quote_prefix):
            continue
        line_text = normalize_whitespace(line_text[len(quote_prefix):])
        if line_text in parent_line_set:
            parent_line = parent_line_set[line_text]
            quoted_lines.append(QuotedLine(
                    text=parent_line.text,
                    parent_line_number=parent_line.line_number,
                    child_line_number=line.line_number))
        else:
            continue
    return quoted_lines, quote_prefix

def to_lines(text: str) -> List[Line]:
    line_list = []
    line_number = 0
    for line in text.splitlines():
        line_list.append(Line(text=line, line_number=line_number))
        line_number += 1
    return line_list

def filter_definitely_comments(child_lines: List[Line]) -> List[Line]:
    child_lines = child_lines[:]
    quote_matcher = re.compile(r'\s*>.*')
    comments = []
    for line in child_lines:
      if quote_matcher.match(line.text):
        comments.append(line)
    return comments

def is_same_line(child_line: Line, quoted_line: QuotedLine, quote_prefix: str) -> bool:
    if child_line.line_number == quoted_line.child_line_number:
        if normalize_whitespace(
                child_line.text[len(quote_prefix):]) != normalize_whitespace(quoted_line.text):
            logging.info('child_line.text: %s', child_line.text)
            logging.info('quote_line.text: %s', quoted_line.text)
            raise ValueError('Lines have matching line numbers, but text does not match')
        else:
            return True
    else:
        return False

def filter_non_quoted_lines(all_child_lines: List[Line],
                            quoted_lines: List[QuotedLine],
                            quote_prefix: str) -> List[CommentLine]:
    comment_lines = []
    quoted_lines_iter = iter(quoted_lines)
    quoted_line = next(quoted_lines_iter, None)
    last_parent_line_number = -1
    for child_line in all_child_lines:
        if quoted_line and is_same_line(child_line, quoted_line, quote_prefix):
            last_parent_line_number = quoted_line.parent_line_number
            quoted_line = next(quoted_lines_iter, None)
        else:
            comment_lines.append(CommentLine(last_parent_line_number=last_parent_line_number,
                                             child_line_number=child_line.line_number,
                                             text=child_line.text))
    return comment_lines

def merge_comment_lines(comment_lines: List[CommentLine]) -> List[Comment]:
    comment_map : Dict[int, List[CommentLine]] = {}
    comment_lines.sort(key=lambda x: x.child_line_number)
    for line in comment_lines:
        if line.last_parent_line_number not in comment_map:
            comment_map[line.last_parent_line_number] = []
        comment_map[line.last_parent_line_number].append(line)
    comment_list = []
    for last_parent_line_number, line_list in comment_map.items():
        message = '\n'.join([line.text for line in line_list])
        comment_list.append(Comment(raw_line=last_parent_line_number, message=message))
    return comment_list

def find_comments(parent_lines: List[Line], all_child_lines: List[Line]) -> List[Comment]:
    probably_not_comment_lines = filter_definitely_comments(all_child_lines)
    quoted_lines, quote_prefix = find_quoted_lines(parent_lines, probably_not_comment_lines)
    comment_lines = filter_non_quoted_lines(all_child_lines, quoted_lines, quote_prefix)
    return merge_comment_lines(comment_lines)

def diff_reply(parent: Message, child: Message) -> List[Comment]:
    #TODO: to_lines only works on str, but Message.content is also sometimes a List
    parent_lines = to_lines(parent.content)
    child_lines = to_lines(child.content)
    return find_comments(parent_lines, child_lines)

def filter_patches_and_cover_letter_replies(email_thread: Message) -> Tuple[List[Message], List[Message]]:
    patches = []
    cover_letter_replies = []
    if (not email_thread.in_reply_to and email_thread.patch_index()[0] == 1):
        patches.append(email_thread)
    for message in email_thread.children:
        if message.is_patch():
            patches.append(message)
        else:
            cover_letter_replies.append(message)
    return patches, cover_letter_replies

def find_patches(email_thread: Message) -> List[Message]:
    patches, _ = filter_patches_and_cover_letter_replies(email_thread)
    return patches

def find_cover_letter_replies(email_thread: Message) -> List[Message]:
    _, cover_letter_replies = filter_patches_and_cover_letter_replies(email_thread)
    return cover_letter_replies

def parse_comments(email_thread: Message) -> Patchset:
    replies = find_cover_letter_replies(email_thread)
    comments = []
    for reply in replies:
        comments.extend(diff_reply(email_thread, reply))
    cover_letter = CoverLetter(text=email_thread.content, comments=comments)

    patches = find_patches(email_thread)
    patch_list = []
    for patch in patches:
        comments = []
        for reply in patch.children:
            comments.extend(diff_reply(patch, reply))
        if (len(patches) == 1 and not email_thread.in_reply_to):
            set_index = 0
        else:
            set_index, length = patch.patch_index()
            assert length == len(patches)
        text = 'From: {from_}\nSubject: {subject}\n\n{content}'.format(
            from_=patch.from_, subject=patch.subject, content=patch.content)
        patch_list.append(Patch(message_id = patch.id,
                                text=patch.content,
                                text_with_headers=text,
                                set_index=set_index,
                                comments=comments,
                                change_id=patch.change_id))
        patch_list.sort(key=lambda x: x.set_index)
    return Patchset(cover_letter=cover_letter, patches=patch_list)

def associate_comments_to_files(patchset: Patchset) -> None:
    pass

def associate_comment_to_file(comment: Comment) -> None:
    pass

class PatchFileChunkLineMap(object):
    def __init__(self, in_range: Tuple[int, int], side: str, offset: int):
        self.in_range = in_range
        self.side = side
        self.offset = offset

    def __contains__(self, raw_line):
        return self.in_range[0] <= raw_line and raw_line <= self.in_range[1]

    def map(self, raw_line: int) -> Tuple[str, int]:
        if raw_line in self:
            return self.side, raw_line + self.offset
        else:
            raise IndexError('Expected ' + str(self.in_range[0]) + ' <= ' + str(raw_line) + ' <= ' + str(self.in_range[1]))

class PatchFileLineMap(object):
    def __init__(self, name: str, chunks: List[PatchFileChunkLineMap]):
        self.name = name
        self.chunks = chunks
        self.in_range = (chunks[0].in_range[0], chunks[-1].in_range[1])

    def __contains__(self, raw_line):
        logging.info('Checking if %s <= %s <= %s', str(self.in_range[0]), str(raw_line), str(self.in_range[1]))
        return self.in_range[0] <= raw_line and raw_line <= self.in_range[1]

    def map(self, raw_line: int) -> Tuple[str, int]:
        for chunk in self.chunks:
            if raw_line in chunk:
                side, line = chunk.map(raw_line)
                return self.name + side, line
        logging.info('%s was not in any chunk', str(raw_line))
        return self.name, -1


class RawLineToGerritLineMap(object):
    def __init__(self, patch_files: List[PatchFileLineMap]):
        self.patch_files = patch_files

    def __contains__(self, raw_line):
        for patch_file in self.patch_files:
            if raw_line in patch_file:
                return True
        return False

    def map(self, raw_line: int) -> Tuple[str, int]:
        for patch_file in self.patch_files:
            logging.info('Checking: %s', patch_file.name)
            if raw_line in patch_file:
                return patch_file.map(raw_line)
        logging.info('%s was not found in patch', str(raw_line))
        return '', -1

SKIP_LINE_MATCHER = re.compile(r'^@@ -(\d+)(,\d+)? \+(\d+)(,\d+)? @@.*$')

DIFF_LINE_MATCHER = re.compile(r'^diff --git a/\S+ b/(\S+)$')

def _does_match_end_of_super_chunk(lines: List[str]) -> bool:
    line = lines[0]
    return (line == '--') or (len(lines) <= 1) or bool(SKIP_LINE_MATCHER.match(line) or DIFF_LINE_MATCHER.match(line))

def _parse_patch_file_unchanged_chunk(
        lines: List[str],
        raw_index: int,
        gerrit_orig_line: int,
        gerrit_new_line: int) -> Tuple[int, int, int, PatchFileChunkLineMap]:
    in_start = raw_index
    while (not _does_match_end_of_super_chunk(lines)) and ((not lines[0]) or (lines[0] and lines[0][0] != '+' and lines[0][0] != '-')):
        logging.info('dropping line: %s', lines[0])
        lines.pop(0)
        gerrit_orig_line += 1
        gerrit_new_line += 1
        raw_index += 1
    return (gerrit_orig_line,
            gerrit_new_line,
            raw_index,
            PatchFileChunkLineMap(in_range=(in_start, raw_index - 1),
                                  side='',
                                  offset=(gerrit_new_line - raw_index)))

def _parse_patch_file_added_chunk(
        lines: List[str],
        raw_index: int,
        gerrit_orig_line: int,
        gerrit_new_line: int) -> Tuple[int, int, int, PatchFileChunkLineMap]:
    in_start = raw_index
    logging.info('First char - 1: %c', lines[0][0])
    while lines[0] and lines[0][0] == '+':
        lines.pop(0)
        gerrit_orig_line += 1
        gerrit_new_line += 1
        raw_index += 1
    return (gerrit_orig_line,
            gerrit_new_line,
            raw_index,
            PatchFileChunkLineMap(in_range=(in_start, raw_index - 1),
                                  side='',
                                  offset=(gerrit_new_line - raw_index)))

def _parse_patch_file_removed_chunk(
        lines: List[str],
        raw_index: int,
        gerrit_orig_line: int,
        gerrit_new_line: int) -> Tuple[int, int, int, PatchFileChunkLineMap]:
    in_start = raw_index
    while lines[0] and lines[0][0] == '-':
        lines.pop(0)
        gerrit_orig_line += 1
        gerrit_new_line += 1
        raw_index += 1
    return (gerrit_orig_line,
            gerrit_new_line,
            raw_index,
            PatchFileChunkLineMap(in_range=(in_start, raw_index - 1),
                                  side='b',
                                  offset=(gerrit_new_line - raw_index)))

def _parse_patch_file_chunk(lines: List[str],
                            raw_index: int,
                            gerrit_orig_line: int,
                            gerrit_new_line: int) -> Tuple[int, int, int, PatchFileChunkLineMap]:
    line = lines[0]
    start_line_len = len(lines)
    if _does_match_end_of_super_chunk(lines):
        raise ValueError('Unexpected line: ' + line)
    elif line and line[0] == '+':
        logging.info('First char - 0: %c', line[0])
        ret_val =  _parse_patch_file_added_chunk(lines, raw_index, gerrit_orig_line, gerrit_new_line)
        if start_line_len == len(lines):
            raise ValueError('Could not parse add line: ' + line)
        return ret_val
    elif line and line[0] == '-':
        ret_val = _parse_patch_file_removed_chunk(lines, raw_index, gerrit_orig_line, gerrit_new_line)
        if start_line_len == len(lines):
            raise ValueError('Could not parse remove line: ' + line)
        return ret_val
    else:
        ret_val = _parse_patch_file_unchanged_chunk(lines, raw_index, gerrit_orig_line, gerrit_new_line)
        if start_line_len == len(lines):
            raise ValueError('Could not parse unchanged line: ' + line)
        return ret_val

def _parse_patch_file_super_chunk(lines: List[str], raw_index: int) -> List[PatchFileChunkLineMap]:
    match = SKIP_LINE_MATCHER.match(lines[0])
    if not match:
        return []
    gerrit_orig_line = int(match.group(1))
    gerrit_new_line = int(match.group(3))
    logging.info('old starts at: %d, new starts at: %d', gerrit_orig_line, gerrit_new_line)
    lines.pop(0)
    raw_index += 1
    chunks = []
    while not _does_match_end_of_super_chunk(lines):
        logging.info('lines left: %d', len(lines))
        (gerrit_orig_line,
         gerrit_new_line,
         raw_index,
         chunk) = _parse_patch_file_chunk(lines,
                                          raw_index,
                                          gerrit_orig_line,
                                          gerrit_new_line)
        chunks.append(chunk)
    return chunks

def _parse_patch_file_entry(lines: List[str], index: int) -> Optional[PatchFileLineMap]:
    match = DIFF_LINE_MATCHER.match(lines[0])
    if not match:
        logging.info('failed to find file diff, instead found: %s', lines[0])
        return None
    file_name = match.group(1)
    lines.pop(0)
    index += 1

    if re.match(r'^new file mode \d+$', lines[0]):
        lines.pop(0)
        index += 1

    if re.match(r'^index [0-9a-f]+\.\.[0-9a-f]+( \d+)?$', lines[0]):
        lines.pop(0)
        index += 1
    else:
        logging.info('failed to find index line, instead found: %s', lines[0])
        return None
    if re.match(r'^--- ((a/\S+$)|(/dev/null))', lines[0]):
        lines.pop(0)
        index += 1
    else:
        logging.info('failed to find -- a/* line, instead found: %s', lines[0])
        return None
    if re.match(r'^\+\+\+ b/\S+$', lines[0]):
        lines.pop(0)
        index += 1
    else:
        logging.info('failed to find ++ b/* line, instead found: %s', lines[0])
        return None

    chunks = []
    super_chunk = _parse_patch_file_super_chunk(lines, index)
    while super_chunk:
        chunks.extend(super_chunk)
        chunk = super_chunk[-1]
        logging.info('parsed super chunk: %d to %d', index, chunk.in_range[1])
        index = chunk.in_range[1]
        logging.info('about to parse: %s', lines[0])
        super_chunk = _parse_patch_file_super_chunk(lines, index)
    if not chunks:
        raise ValueError('Expected chunks in file, but found: ' + lines[0])
    return PatchFileLineMap(name=file_name, chunks=chunks)

def _parse_patch_header(lines: List[str]) -> int:
    index = 0

    # Ignore everything before last '---'.
    for i in reversed(range(len(lines))):
        if lines[i] == '---':
            index = i
            break
    del lines[:index]
    if lines[0] == '---':
        lines.pop(0)
        index += 1
    else:
        raise ValueError('failed to find ---, instead found: ' + lines[0])

    # Drop high level summary before first file diff.
    while re.match(r'^\S+\s+\|\s+\d+ \+*-*$', lines[0]):
        lines.pop(0)
        index += 1
    if re.match(r'^\d+ file(s?) changed(, \d+ insertion(s?)\(\+\))?(, \d+ deletion(s?)\(\-\))?$', lines[0]):
        lines.pop(0)
        index += 1
    else:
        raise ValueError('failed to find top level summary, instead found: ' + lines[0])
    while re.match(r'^create mode \d+ \S+$', lines[0]):
        lines.pop(0)
        index += 1

    if not lines[0]:
        lines.pop(0)
        index += 1
    else:
        logging.info('expected blank line after summary, instead got: %s', lines[0])

    # Make sure the next line is the start of a file diff.
    if DIFF_LINE_MATCHER.match(lines[0]):
        return index
    else:
        raise ValueError('failed to find file diff, instead found: ' + lines[0])

def _parse_git_patch(raw_patch: str) -> RawLineToGerritLineMap:
    lines = raw_patch.split('\n')
    lines = [line.strip() for line in lines]
    index = _parse_patch_header(lines)
    file_entries = []
    file_entry = _parse_patch_file_entry(lines, index)
    while file_entry:
        file_entries.append(file_entry)
        index = file_entry.chunks[-1].in_range[-1]
        file_entry = _parse_patch_file_entry(lines, index)
    if lines and (lines[0] == '--' or lines[0] == ''):
        return RawLineToGerritLineMap(patch_files=file_entries)
    elif lines:
        raise ValueError('Could not parse entire file: ' + str(lines))
    else:
        raise ValueError('Unknown error')

def map_patch_to_gerrit_change(patch: Patch) -> None:
    logging.info('Patch: %s', patch.text)
    raw_line_to_gerrit_map = _parse_git_patch(patch.text)
    for comment in patch.comments:
        logging.info('raw_line: %d, messages: %s', comment.raw_line, comment.message)
        comment.file, comment.line = raw_line_to_gerrit_map.map(comment.raw_line)

def map_comments_to_gerrit(patchset: Patchset):
    for patch in patchset.patches:
        map_patch_to_gerrit_change(patch)

def main():
    email_thread = find_thread('PATCH v17 00/19')
    patchset = parse_comments(email_thread)
    map_comments_to_gerrit(patchset)
    for patch in patchset.patches:
        for comment in patch.comments:
            logging.info('At %d: %s: %s:\n %s', comment.raw_line, str(comment.file), str(comment.line), comment.message)

if __name__ == '__main__':
    main()
