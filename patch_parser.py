from typing import Dict, List, Optional, Tuple
        text = list(line.text)
        text.reverse()
        trie.insert(text)
        text = list(line.text)
        text.reverse()
        prefix = trie.diff_best_match(text)
        prefix_str = ''.join(prefix)
        if prefix_str not in prefix_count_map:
            prefix_count_map[prefix_str] = 1
            prefix_count_map[prefix_str] += 1
    prefix_str, count = max(prefix_count_map.items(), key=lambda x: x[1])
    return prefix_str
    traversal_map : Dict[str, List[Line]] = {}
        child_lines: List[Line]) -> Tuple[List[QuotedLine], str]:
                      child_lines: List[Line]) -> Tuple[List[QuotedLine], str]:
def is_same_line(child_line: Line, quoted_line: QuotedLine, quote_prefix: str) -> bool:
        if quoted_line and is_same_line(child_line, quoted_line, quote_prefix):
    comment_map : Dict[int, List[CommentLine]] = {}
def filter_patches_and_cover_letter_replies(email_thread: Message) -> Tuple[List[Message], List[Message]]:
    if (not email_thread.in_reply_to and parse_set_index(email_thread)[0] == 1):
def parse_set_index(email: Message) -> Tuple[int, int]:
    if match is None:
      raise ValueError(f'Missing patch index in subject: {email.subject}')
    def __init__(self, in_range: Tuple[int, int], side: str, offset: int):
    def map(self, raw_line: int) -> Tuple[str, int]:
    def map(self, raw_line: int) -> Tuple[str, int]:
    def map(self, raw_line: int) -> Tuple[str, int]:
    return (line == '--') or (len(lines) <= 1) or bool(SKIP_LINE_MATCHER.match(line) or DIFF_LINE_MATCHER.match(line))
        gerrit_new_line: int) -> Tuple[int, int, int, PatchFileChunkLineMap]:
        gerrit_new_line: int) -> Tuple[int, int, int, PatchFileChunkLineMap]:
        gerrit_new_line: int) -> Tuple[int, int, int, PatchFileChunkLineMap]:
                            gerrit_new_line: int) -> Tuple[int, int, int, PatchFileChunkLineMap]:
        return []
def _parse_patch_file_entry(lines: List[str], index: int) -> Optional[PatchFileLineMap]:
        raise ValueError('failed to find ---, instead found: ' + lines[0])
        raise ValueError('failed to find top level summary, instead found: ' + lines[0])
        raise ValueError('failed to find file diff, instead found: ' + lines[0])