from __future__ import print_function
from typing import Dict, List
import base64
import pickle
import os.path
import re
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from setup_gmail import Message
from setup_gmail import find_thread

class Comment(object):
    def __init__(self, line, message):
        self.line = line
        self.message = message
        self.children = []

class CoverLetter(object):
    def __init__(self, text, comments):
        self.text = text
        self.comments = comments

class Patch(object):
    def __init__(self, text, comments):
        self.text = text
        self.comments = comments

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
        line = list(line.text)
        line.reverse()
        trie.insert(line)
    prefix_count_map = {}
    for line in child_lines:
        line = list(line.text)
        line.reverse()
        prefix = trie.diff_best_match(line)
        prefix.reverse()
        prefix = ''.join(prefix)
        if prefix not in prefix_count_map:
            prefix_count_map[prefix] = 1
        else:
            prefix_count_map[prefix] += 1
    prefix, count = max(prefix_count_map.items(), key=lambda x: x[1])
    return prefix

def build_traversal_map(parent_lines: List[Line], child_lines: List[Line], quote_prefix: str) -> Dict[str, List[Line]]:
    parent_line_set = set([line.text for line in parent_lines])
    traversal_map = {}
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
    print('len(parent_lines) = ' + str(len(parent_lines)))
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
        child_lines: List[Line]) -> (List[QuotedLine], str):
    quote_prefix = get_quote_prefix(parent_lines, child_lines)
    traversal_map = build_traversal_map(parent_lines, child_lines, quote_prefix)
    return find_maximal_map_traversal(traversal_map, parent_lines, []), quote_prefix

NORMALIZE_WHITESPACE_MATCHER = re.compile(r'\s+')

def normalize_whitespace(string: str) -> str:
    return NORMALIZE_WHITESPACE_MATCHER.sub(' ', string)

def find_quoted_lines(parent_lines: List[Line],
                      child_lines: List[Line]) -> (List[QuotedLine], str):
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

def is_same_line(child_line: Line, quoted_line: QuotedLine, quote_prefix: str) -> List[CommentLine]:
    if not quoted_line:
        return False
    if child_line.line_number == quoted_line.child_line_number:
        if normalize_whitespace(
                child_line.text[len(quote_prefix):]) != normalize_whitespace(quoted_line.text):
            print('child_line.text: ' + child_line.text)
            print('quote_line.text: ' + quoted_line.text)
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
        if is_same_line(child_line, quoted_line, quote_prefix):
            last_parent_line_number = quoted_line.parent_line_number
            quoted_line = next(quoted_lines_iter, None)
        else:
            comment_lines.append(CommentLine(last_parent_line_number=last_parent_line_number,
                                             child_line_number=child_line.line_number,
                                             text=child_line.text))
    return comment_lines

def merge_comment_lines(comment_lines: List[CommentLine]) -> List[Comment]:
    comment_map = {}
    comment_lines.sort(key=lambda x: x.child_line_number)
    for line in comment_lines:
        if line.last_parent_line_number not in comment_map:
            comment_map[line.last_parent_line_number] = []
        comment_map[line.last_parent_line_number].append(line)
    comment_list = []
    for last_parent_line_number, line_list in comment_map.items():
        message = '\n'.join([line.text for line in line_list])
        comment_list.append(Comment(line=last_parent_line_number, message=message))
    return comment_list

def find_comments(parent_lines: List[Line], all_child_lines: List[Line]) -> List[Comment]:
    probably_not_comment_lines = filter_definitely_comments(all_child_lines)
    quoted_lines, quote_prefix = find_quoted_lines(parent_lines, probably_not_comment_lines)
    comment_lines = filter_non_quoted_lines(all_child_lines, quoted_lines, quote_prefix)
    return merge_comment_lines(comment_lines)

def diff_reply(parent: Message, child: Message) -> List[Comment]:
    parent_lines = to_lines(parent.content)
    child_lines = to_lines(child.content)
    return find_comments(parent_lines, child_lines)

def filter_patches_and_cover_letter_replies(email_thread: Message) -> (List[Message], List[Message]):
    patches = []
    cover_letter_replies = []
    for message in email_thread.children:
        if re.match(r'\[.+ \d+/\d+\] .+', message.subject):
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
        patch_list.append(Patch(text=patch.content, comments=comments))
    return Patchset(cover_letter=cover_letter, patches=patch_list)

def main():
    email_thread = find_thread('PATCH v5 00/18')
    patchset = parse_comments(email_thread)
    for patch in patchset.patches:
        for comment in patch.comments:
            print('At line ' + str(comment.line) + ':\n' + comment.message)

if __name__ == '__main__':
    main()
