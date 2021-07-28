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

import dataclasses
import textwrap
from typing import Any, Dict, List, Optional, Tuple
import re

from absl import logging
from message import Message


class Comment(object):
    def __init__(self, raw_line, message: str, file: Optional[str] = None, line: Optional[int] = None) -> None:
        self.raw_line = raw_line
        self.message = message
        self.file = file
        self.line = line


class CoverLetter(object):
    def __init__(self, text, comments: List[Comment]) -> None:
        self.text = text
        self.comments = comments


class Patch(object):
    def __init__(self, message_id, text, text_with_headers, set_index, comments, change_id) -> None:
        self.message_id = message_id
        self.text = text
        self.text_with_headers = text_with_headers
        self.set_index = set_index
        self.comments = comments
        self.change_id = change_id
        self.revision_id = None


class Patchset(object):
    def __init__(self, cover_letter, patches) -> None:
        self.cover_letter = cover_letter
        self.patches = patches


class InputSource:
    """Tracks the line number as we iterate over lines of text."""
    _lines: List[str]
    _base_line_number: int
    _previous_item: str

    def __init__(self, text: str, base_line_number=0):
        self._base_line_number = base_line_number
        self._lines = [l.strip() for l in text.split('\n')]
        self._previous_item = ""

    def __getitem__(self, index) -> str:
        return self._lines[index]

    def __len__(self) -> int:
        return len(self._lines)

    def line_number(self) -> int:
        return self._base_line_number

    def consume(self, n=1) -> None:
        self._previous_item = self._lines[1]
        self._lines = self._lines[n:]
        self._base_line_number += n

    def set_previous_line(self, item):
        self._previous_item = item

    def get_previous_line(self):
        return self._previous_item


class Line(object):
    """A line of text that tracks its line number."""

    def __init__(self, line_number: int, text: str) -> None:
        self.line_number = line_number
        self.text = text


class QuotedLine(object):
    def __init__(self, parent_line_number: int, child_line_number: int, text: str) -> None:
        self.parent_line_number = parent_line_number
        self.child_line_number = child_line_number
        self.text = text


class CommentLine(object):
    def __init__(self, last_parent_line_number: int, child_line_number: int, text: str) -> None:
        self.last_parent_line_number = last_parent_line_number
        self.child_line_number = child_line_number
        self.text = text


class Trie(object):
    def __init__(self) -> None:
        self._children = {}  # type: Dict[str, TrieNode]

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
    def __init__(self, letter: str) -> None:
        self._letter = letter
        self._children = {}  # type: Dict[str, TrieNode]
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


@dataclasses.dataclass
class HunkParserState:
    deleted_lines: int = 0
    gerrit_orig_line: int = 0
    gerrit_new_line: int = 0


def _get_quote_prefix(parent_lines: List[Line], child_lines: List[Line]) -> str:
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


NORMALIZE_WHITESPACE_MATCHER = re.compile(r'\s+')


def _normalize_whitespace(string: str) -> str:
    return NORMALIZE_WHITESPACE_MATCHER.sub(' ', string)


def _find_quoted_lines(parent_lines: List[Line],
                       child_lines: List[Line]) -> Tuple[List[QuotedLine], str]:
    quote_prefix = _get_quote_prefix(parent_lines, child_lines)
    parent_line_set = {}
    for line in parent_lines:
        parent_line_set[_normalize_whitespace(line.text)] = line
    quoted_lines = []
    for line in child_lines:
        line_text = line.text
        if not line_text.startswith(quote_prefix):
            continue
        line_text = _normalize_whitespace(line_text[len(quote_prefix):])
        if line_text in parent_line_set:
            parent_line = parent_line_set[line_text]
            quoted_lines.append(QuotedLine(
                text=parent_line.text,
                parent_line_number=parent_line.line_number,
                child_line_number=line.line_number))
        else:
            continue
    return quoted_lines, quote_prefix


def _to_lines(text: str) -> List[Line]:
    line_list = []
    for i, line in enumerate(text.splitlines()):
        line_list.append(Line(text=line, line_number=i))
    return line_list


def _filter_definitely_comments(child_lines: List[Line]) -> List[Line]:
    child_lines = child_lines[:]
    quote_matcher = re.compile(r'\s*>.*')
    comments = []
    for line in child_lines:
        if quote_matcher.match(line.text):
            comments.append(line)
    return comments


def _is_same_line(child_line: Line, quoted_line: QuotedLine, quote_prefix: str) -> bool:
    if child_line.line_number == quoted_line.child_line_number:
        if _normalize_whitespace(
                child_line.text[len(quote_prefix):]) != _normalize_whitespace(quoted_line.text):
            logging.info('child_line.text: %s', child_line.text)
            logging.info('quote_line.text: %s', quoted_line.text)
            raise ValueError('Lines have matching line numbers, but text does not match')
        else:
            return True
    else:
        return False


def _filter_non_quoted_lines(all_child_lines: List[Line],
                             quoted_lines: List[QuotedLine],
                             quote_prefix: str) -> List[CommentLine]:
    comment_lines = []
    quoted_lines_iter = iter(quoted_lines)
    quoted_line = next(quoted_lines_iter, None)
    last_parent_line_number = -1
    for child_line in all_child_lines:
        if quoted_line and _is_same_line(child_line, quoted_line, quote_prefix):
            last_parent_line_number = quoted_line.parent_line_number
            quoted_line = next(quoted_lines_iter, None)
        else:
            comment_lines.append(CommentLine(last_parent_line_number=last_parent_line_number,
                                             child_line_number=child_line.line_number,
                                             text=child_line.text))
    return comment_lines


def _merge_comment_lines(comment_lines: List[CommentLine]) -> List[Comment]:
    comment_map: Dict[int, List[CommentLine]] = {}
    comment_lines.sort(key=lambda x: x.child_line_number)
    for line in comment_lines:
        if line.last_parent_line_number not in comment_map:
            comment_map[line.last_parent_line_number] = []
        comment_map[line.last_parent_line_number].append(line)
    comment_list = []  # type: List[Comment]
    for last_parent_line_number, line_list in comment_map.items():
        message = '\n'.join([line.text for line in line_list])
        comment_list.append(Comment(raw_line=last_parent_line_number, message=message))
    return comment_list


def _find_comments(parent_lines: List[Line], all_child_lines: List[Line]) -> List[Comment]:
    probably_not_comment_lines = _filter_definitely_comments(all_child_lines)
    quoted_lines, quote_prefix = _find_quoted_lines(parent_lines, probably_not_comment_lines)
    comment_lines = _filter_non_quoted_lines(all_child_lines, quoted_lines, quote_prefix)
    return _merge_comment_lines(comment_lines)


def _diff_reply(parent: Message, child: Message) -> List[Comment]:
    # TODO: _to_lines only works on str, but Message.content is also sometimes a List
    parent_lines = _to_lines(parent.content)
    child_lines = _to_lines(child.content)
    return _find_comments(parent_lines, child_lines)


def _filter_patches_and_cover_letter_replies(email_thread: Message) -> Tuple[List[Message], List[Message]]:
    patches = []
    cover_letter_replies = []
    if not email_thread.in_reply_to and email_thread.patch_index()[0] == 1:
        patches.append(email_thread)
    for message in email_thread.children:
        if message.is_patch():
            patches.append(message)
        else:
            cover_letter_replies.append(message)
    return patches, cover_letter_replies


def _find_patches(email_thread: Message) -> List[Message]:
    patches, _ = _filter_patches_and_cover_letter_replies(email_thread)
    return patches


def _find_cover_letter_replies(email_thread: Message) -> List[Message]:
    _, cover_letter_replies = _filter_patches_and_cover_letter_replies(email_thread)
    return cover_letter_replies


def parse_comments(email_thread: Message) -> Patchset:
    replies = _find_cover_letter_replies(email_thread)
    comments = []  # type: List[Comment]
    for reply in replies:
        comments.extend(_diff_reply(email_thread, reply))
    cover_letter = CoverLetter(text=email_thread.content, comments=comments)

    patches = _find_patches(email_thread)
    patch_list = []
    for patch in patches:
        comments = []
        for reply in patch.children:
            comments.extend(_diff_reply(patch, reply))
        if (len(patches) == 1 and not email_thread.in_reply_to):
            set_index = 0
        else:
            set_index, length = patch.patch_index()
            assert length == len(patches)
        text = 'From: {from_}\nSubject: {subject}\n\n{content}'.format(
            from_=patch.from_, subject=patch.subject, content=patch.content)
        patch_list.append(Patch(message_id=patch.id,
                                text=patch.content,
                                text_with_headers=text,
                                set_index=set_index,
                                comments=comments,
                                change_id=patch.change_id))
    patch_list.sort(key=lambda x: x.set_index)
    return Patchset(cover_letter=cover_letter, patches=patch_list)


class PatchFileChunkLineMap(object):
    def __init__(self, in_range: Tuple[int, int], side: str, offset: int) -> None:
        self.in_range = in_range
        self.side = side
        self.offset = offset

    def __contains__(self, raw_line: int) -> bool:
        return self.in_range[0] <= raw_line and raw_line <= self.in_range[1]

    def map(self, raw_line: int) -> Tuple[str, int]:
        if raw_line in self:
            return self.side, raw_line + self.offset
        else:
            raise IndexError(
                'Expected ' + str(self.in_range[0]) + ' <= ' + str(raw_line) + ' <= ' + str(self.in_range[1]))

    def __repr__(self) -> str:
        return f'PatchFileLineMap(side={self.side}, offset={self.offset}, range={self.in_range})'


class PatchFileLineMap(object):
    def __init__(self, name: str, chunks: List[PatchFileChunkLineMap]) -> None:
        self.name = name
        self.chunks = chunks
        self.in_range = (chunks[0].in_range[0], chunks[-1].in_range[1])

    def __contains__(self, raw_line: int) -> bool:
        logging.info('Checking if %s <= %s <= %s', str(self.in_range[0]), str(raw_line), str(self.in_range[1]))
        return self.in_range[0] <= raw_line and raw_line <= self.in_range[1]

    def map(self, raw_line: int) -> Tuple[str, int]:
        for chunk in self.chunks:
            if raw_line in chunk:
                side, line = chunk.map(raw_line)
                return self.name + side, line
        logging.info('%s was not in any chunk', str(raw_line))
        return self.name, -1

    def __repr__(self) -> str:
        children = '\n'.join(textwrap.indent(repr(c), '  ') for c in self.chunks)
        return f'PatchFileLineMap(name={self.name} range={self.in_range}\nchunks=\n{children})'


class RawLineToGerritLineMap(object):
    def __init__(self, patch_files: List[PatchFileLineMap]) -> None:
        self.patch_files = patch_files

    def __contains__(self, raw_line: int) -> bool:
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

    def __repr__(self) -> str:
        children = '\n'.join(textwrap.indent(repr(p), '  ') for p in self.patch_files)
        return 'RawLineToGerritLineMap(\n' + children + '\n)'


SKIP_LINE_MATCHER = re.compile(r'^@@ -(\d+)(,\d+)? \+(\d+)(,\d+)? @@.*$')

DIFF_LINE_MATCHER = re.compile(r'^diff --git a/\S+ b/(\S+)$')


def _does_match_end_of_super_chunk(lines: InputSource) -> bool:
    line = lines[0]
    return (line == '--') or (len(lines) <= 1) or bool(SKIP_LINE_MATCHER.match(line) or DIFF_LINE_MATCHER.match(line))


def _parse_patch_file_unchanged_chunk(
        lines: InputSource,
        parser_state: HunkParserState) -> PatchFileChunkLineMap:
    in_start = lines.line_number()
    while (not _does_match_end_of_super_chunk(lines)) and (
            (not lines[0]) or (lines[0] and lines[0][0] != '+' and lines[0][0] != '-')):
        logging.info('dropping line: %s', lines[0])
        lines.consume()
        parser_state.gerrit_orig_line += 1
        parser_state.gerrit_new_line += 1
        # logging.debug('Unchanged start: ' + str(in_start))
        # logging.debug('Unchanged line: ' + lines[0])
        # logging.debug('Unchanged lines - 1: ' + str(lines.line_number() - 1))
    offset = parser_state.gerrit_new_line - parser_state.deleted_lines - lines.line_number()
    return PatchFileChunkLineMap(in_range=(in_start, lines.line_number() - 1),
                                 side='', offset=offset)


def _parse_patch_file_added_chunk(
        lines: InputSource,
        parser_state: HunkParserState) -> PatchFileChunkLineMap:
    in_start = lines.line_number()
    parser_state.deleted_lines = 0
    logging.info('First char - 1: %c', lines[0][0])
    while lines[0] and lines[0][0] == '+':
        previous = lines.get_previous_line()
        lines.consume()
        parser_state.gerrit_orig_line += 1
        parser_state.gerrit_new_line += 1
        if previous[0] == '-':  # TODO: maybe add check to see if it is actually a modified one though I think this
            # situation only applies when it actually is modified
            return PatchFileChunkLineMap(in_range=(in_start, lines.line_number() - 1),
                                         side='',
                                         offset=(parser_state.gerrit_new_line - lines.line_number() - 1))
    return PatchFileChunkLineMap(in_range=(in_start, lines.line_number() - 1),
                                 side='',
                                 offset=(parser_state.gerrit_new_line - lines.line_number()))


def _parse_patch_file_removed_chunk(
        lines: InputSource,
        parser_state: HunkParserState) -> PatchFileChunkLineMap:
    in_start = lines.line_number()
    while lines[0] and lines[0][0] == '-':
        lines.consume()
        parser_state.gerrit_orig_line += 1
        parser_state.gerrit_new_line += 1
        parser_state.deleted_lines += 1
    return PatchFileChunkLineMap(in_range=(in_start, lines.line_number() - 1),
                                 side='b',
                                 offset=(parser_state.gerrit_new_line - lines.line_number()))


def _parse_patch_file_chunk(lines: InputSource,
                            parser_state: HunkParserState) -> PatchFileChunkLineMap:
    line = lines[0]
    start_line_len = len(lines)
    if _does_match_end_of_super_chunk(lines):
        raise ValueError('Unexpected line: ' + line)
    elif line and line[0] == '+':
        logging.info('First char - 0: %c', line[0])
        chunk_map = _parse_patch_file_added_chunk(lines, parser_state)
        if start_line_len == len(lines):
            raise ValueError('Could not parse add line: ' + line)
        return chunk_map
    elif line and line[0] == '-':
        chunk_map = _parse_patch_file_removed_chunk(lines, parser_state)
        if start_line_len == len(lines):
            raise ValueError('Could not parse remove line: ' + line)
        return chunk_map
    else:
        chunk_map = _parse_patch_file_unchanged_chunk(lines, parser_state)
        if start_line_len == len(lines):
            raise ValueError('Could not parse unchanged line: ' + line)
        return chunk_map


def _parse_patch_file_super_chunk(lines: InputSource) -> List[PatchFileChunkLineMap]:
    parser_state = HunkParserState()
    match = SKIP_LINE_MATCHER.match(lines[0])
    if not match:
        return []
    parser_state.gerrit_orig_line = int(match.group(1))
    parser_state.gerrit_new_line = int(match.group(3))
    logging.info('old starts at: %d, new starts at: %d', parser_state.gerrit_orig_line, parser_state.gerrit_new_line)

    lines.consume()
    chunks = []
    while not _does_match_end_of_super_chunk(lines):
        logging.info('lines left: %d', len(lines))
        chunk = _parse_patch_file_chunk(lines,
                                        parser_state)
        chunks.append(chunk)
    return chunks


def _parse_patch_file_entry(lines: InputSource) -> Optional[PatchFileLineMap]:
    match = DIFF_LINE_MATCHER.match(lines[0])
    if not match:
        logging.info('failed to find file diff, instead found: %s', lines[0])
        return None
    file_name = match.group(1)
    lines.consume()

    if re.match(r'^new file mode \d+$', lines[0]):
        lines.consume()

    if re.match(r'^index [0-9a-f]+\.\.[0-9a-f]+( \d+)?$', lines[0]):
        lines.consume()
    else:
        logging.info('failed to find index line, instead found: %s', lines[0])
        return None
    if re.match(r'^--- ((a/\S+$)|(/dev/null))', lines[0]):
        lines.consume()
    else:
        logging.info('failed to find -- a/* line, instead found: %s', lines[0])
        return None
    if re.match(r'^\+\+\+ b/\S+$', lines[0]):
        lines.consume()
    else:
        logging.info('failed to find ++ b/* line, instead found: %s', lines[0])
        return None

    chunks = []
    old_index = lines.line_number()
    super_chunk = _parse_patch_file_super_chunk(lines)
    while super_chunk:
        chunks.extend(super_chunk)
        chunk = super_chunk[-1]
        logging.info('parsed super chunk: %d to %d', old_index, chunk.in_range[1])
        old_index = lines.line_number()
        logging.info('about to parse: %s', lines[0])
        super_chunk = _parse_patch_file_super_chunk(lines)
    if not chunks:
        raise ValueError('Expected chunks in file, but found: ' + lines[0])
    return PatchFileLineMap(name=file_name, chunks=chunks)


def _find_diff_start(lines: InputSource) -> None:
    """Finds the start of the actual diff, after the commit message and the diffstat."""
    # Ignore everything before last '---'.
    for i in reversed(range(len(lines))):
        if lines[i] == '---':
            lines.consume(i)
            break
    if lines[0] == '---':
        lines.consume()
    else:
        raise ValueError('failed to find ---, instead found: ' + lines[0])

    # Drop high level summary before first file diff.
    while re.match(r'^\S+\s+\|\s+\d+ \+*-*$', lines[0]):
        lines.consume()
    if re.match(r'^\d+ file(s?) changed(, \d+ insertion(s?)\(\+\))?(, \d+ deletion(s?)\(\-\))?$', lines[0]):
        lines.consume()
    else:
        raise ValueError('failed to find top level summary, instead found: ' + lines[0])
    while re.match(r'^create mode \d+ \S+$', lines[0]):
        lines.consume()

    if not lines[0]:
        lines.consume()
    else:
        logging.info('expected blank line after summary, instead got: %s', lines[0])

    # Make sure the next line is the start of a file diff.
    if not DIFF_LINE_MATCHER.match(lines[0]):
        raise ValueError('failed to find file diff, instead found: ' + lines[0])


def _parse_git_patch(raw_patch: str) -> RawLineToGerritLineMap:
    lines = InputSource(raw_patch)
    _find_diff_start(lines)
    file_entries = []
    file_entry = _parse_patch_file_entry(lines)
    while file_entry:
        file_entries.append(file_entry)
        index = file_entry.chunks[-1].in_range[-1]
        file_entry = _parse_patch_file_entry(lines)
    if lines and (lines[0] == '--' or lines[0] == ''):
        return RawLineToGerritLineMap(patch_files=file_entries)
    elif lines:
        raise ValueError(f'Could not parse entire file: error at line {lines.line_number()}: ' + lines[0])
    else:
        raise ValueError('Unknown error')


def _map_patch_to_gerrit_change(patch: Patch) -> None:
    logging.info('Patch: %s', patch.text)
    raw_line_to_gerrit_map = _parse_git_patch(patch.text)
    for comment in patch.comments:
        logging.info('raw_line: %d, messages: %s', comment.raw_line, comment.message)
        comment.file, comment.line = raw_line_to_gerrit_map.map(comment.raw_line)


def map_comments_to_gerrit(patchset: Patchset):
    for patch in patchset.patches:
        _map_patch_to_gerrit_change(patch)
