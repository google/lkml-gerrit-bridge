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

    def __init__(self, raw_line, message):
        self.raw_line = raw_line
        self.line = None
        self.file = None
    def __init__(self, text, text_with_headers, set_index, comments):
        self.text_with_headers = text_with_headers
        comment_list.append(Comment(raw_line=last_parent_line_number, message=message))
    if (not email_thread.in_reply_to):
        patches.append(email_thread)
        if (len(patches) == 1 and not email_thread.in_reply_to):
            set_index = 0
        else:
            set_index, length = parse_set_index(patch)
            assert length == len(patches)
        text = 'From: {from_}\nSubject: {subject}\n\n{content}'.format(
            from_=patch.from_, subject=patch.subject, content=patch.content)
        patch_list.append(Patch(text=patch.content, text_with_headers=text, set_index=set_index, comments=comments))
def associate_comments_to_files(patchset: Patchset) -> None:
    pass

def associate_comment_to_file(comment: Comment) -> None:
    pass

class PatchFileChunkLineMap(object):
    def __init__(self, in_range: (int, int), side: str, offset: int):
        self.in_range = in_range
        self.side = side
        self.offset = offset

    def __contains__(self, raw_line):
        return self.in_range[0] <= raw_line and raw_line <= self.in_range[1]

    def map(self, raw_line: int) -> (str, int):
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
        print('Checking if ' + str(self.in_range[0]) + ' <= ' + str(raw_line) + ' <= ' + str(self.in_range[1]))
        return self.in_range[0] <= raw_line and raw_line <= self.in_range[1]

    def map(self, raw_line: int) -> (str, int):
        for chunk in self.chunks:
            if raw_line in chunk:
                side, line = chunk.map(raw_line)
                return self.name + side, line
        print(str(raw_line) + ' was not in any chunk')
        return self.name, -1


class RawLineToGerritLineMap(object):
    def __init__(self, patch_files: List[PatchFileLineMap]):
        self.patch_files = patch_files

    def __contains__(self, raw_line):
        for patch_file in self.patch_files:
            if raw_line in patch_file:
                return True
        return False

    def map(self, raw_line: int) -> (str, int):
        for patch_file in self.patch_files:
            print('Checking: ' + patch_file.name)
            if raw_line in patch_file:
                return patch_file.map(raw_line)
        print(str(raw_line) + ' was not found in patch')
        return '', -1

SKIP_LINE_MATCHER = re.compile(r'^@@ -(\d+)(,\d+)? \+(\d+)(,\d+)? @@.*$')

DIFF_LINE_MATCHER = re.compile(r'^diff --git a/\S+ b/(\S+)$')

def _does_match_end_of_super_chunk(lines: List[str]) -> bool:
    line = lines[0]
    return SKIP_LINE_MATCHER.match(line) or DIFF_LINE_MATCHER.match(line) or (line == '--') or (len(lines) <= 1)

def _parse_patch_file_unchanged_chunk(
        lines: List[str],
        raw_index: int,
        gerrit_orig_line: int,
        gerrit_new_line: int) -> (int, int, int, PatchFileChunkLineMap):
    in_start = raw_index
    while (not _does_match_end_of_super_chunk(lines)) and ((not lines[0]) or (lines[0] and lines[0][0] != '+' and lines[0][0] != '-')):
        print('dropping line: ' + lines[0])
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
        gerrit_new_line: int) -> (int, int, int, PatchFileChunkLineMap):
    in_start = raw_index
    print('First char - 1: ' + lines[0][0])
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
        gerrit_new_line: int) -> (int, int, int, PatchFileChunkLineMap):
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
                            gerrit_new_line: int) -> (int, int, int, PatchFileChunkLineMap):
    line = lines[0]
    start_line_len = len(lines)
    if _does_match_end_of_super_chunk(lines):
        raise ValueError('Unexpected line: ' + line)
    elif line and line[0] == '+':
        print('First char - 0: ' + line[0])
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
        return None
    gerrit_orig_line = int(match.group(1))
    gerrit_new_line = int(match.group(3))
    print('old starts at: ' + str(gerrit_orig_line) + ', new starts at: ' + str(gerrit_new_line))
    lines.pop(0)
    raw_index += 1
    chunks = []
    while not _does_match_end_of_super_chunk(lines):
        print('lines left: ' + str(len(lines)))
        (gerrit_orig_line,
         gerrit_new_line,
         raw_index,
         chunk) = _parse_patch_file_chunk(lines,
                                          raw_index,
                                          gerrit_orig_line,
                                          gerrit_new_line)
        chunks.append(chunk)
    return chunks

def _parse_patch_file_entry(lines: List[str], index: int) -> PatchFileLineMap:
    match = DIFF_LINE_MATCHER.match(lines[0])
    if not match:
        print('failed to find file diff, instead found: ' + lines[0])
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
        print('failed to find index line, instead found: ' + lines[0])
        return None
    if re.match(r'^--- ((a/\S+$)|(/dev/null))', lines[0]):
        lines.pop(0)
        index += 1
    else:
        print('failed to find -- a/* line, instead found: ' + lines[0])
        return None
    if re.match(r'^\+\+\+ b/\S+$', lines[0]):
        lines.pop(0)
        index += 1
    else:
        print('failed to find ++ b/* line, instead found: ' + lines[0])
        return None

    chunks = []
    super_chunk = _parse_patch_file_super_chunk(lines, index)
    while super_chunk:
        chunks.extend(super_chunk)
        chunk = super_chunk[-1]
        print('parsed super chunk: ' + str(index) + ' to ' + str(chunk.in_range[1]))
        index = chunk.in_range[1]
        print('about to parse: ' + lines[0])
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
        print('failed to find ---, instead found: ' + lines[0])
        return None

    # Drop high level summary before first file diff.
    while re.match(r'^\S+\s+\|\s+\d+ \+*-*$', lines[0]):
        lines.pop(0)
        index += 1
    if re.match(r'^\d+ file(s?) changed(, \d+ insertion(s?)\(\+\))?(, \d+ deletion(s?)\(\-\))?$', lines[0]):
        lines.pop(0)
        index += 1
    else:
        print('failed to find top level summary, instead found: ' + lines[0])
        return None
    while re.match(r'^create mode \d+ \S+$', lines[0]):
        lines.pop(0)
        index += 1

    if not lines[0]:
        lines.pop(0)
        index += 1
    else:
        print('expected blank line after summary, instead got: ' + lines[0])

    # Make sure the next line is the start of a file diff.
    if DIFF_LINE_MATCHER.match(lines[0]):
        return index
    else:
        print('failed to find file diff, instead found: ' + lines[0])
        return None

def _parse_git_patch(raw_patch: str) -> RawLineToGerritLineMap:
    lines = raw_patch.split('\n')
    lines = [line.strip() for line in lines]
    index = _parse_patch_header(lines)
    if not index:
        print('failed to find header')
        return None
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
    print(patch.text)
    raw_line_to_gerrit_map = _parse_git_patch(patch.text)
    for comment in patch.comments:
        print('raw_line: ' + str(comment.raw_line) + ', message: ' + comment.message)
        comment.file, comment.line = raw_line_to_gerrit_map.map(comment.raw_line)

def map_comments_to_gerrit(patchset: Patchset):
    for patch in patchset.patches:
        map_patch_to_gerrit_change(patch)
    email_thread = find_thread('PATCH v17 00/19')
    map_comments_to_gerrit(patchset)
            print('At ' + str(comment.raw_line) + ': ' + str(comment.file) + ':' + str(comment.line) + ':\n' + comment.message)