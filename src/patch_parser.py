    def __init__(self, raw_line, message) -> None:
        # TODO: is this field used anymore?
        self.children = []  # type: List[Any]
        self.line = None
        self.file = None
    def __init__(self, line_number, text) -> None:
    def __init__(self, parent_line_number, child_line_number, text) -> None:
    def __init__(self, last_parent_line_number, child_line_number, text) -> None:
class ProbablyQuoted(Line):
    def __init__(self, parent_line_number, child_line_number, text) -> None:
        self.parent_line_number = parent_line_number
        self.child_line_number = child_line_number
        self.line_number = child_line_number
        self.text = text

    def score(self) -> float:
        return 0.5
    line_number = 0
    for line in text.splitlines():
        line_list.append(Line(text=line, line_number=line_number))
        line_number += 1
        patch_list.sort(key=lambda x: x.set_index)
def _does_match_end_of_super_chunk(lines: List[str]) -> bool:
        lines: List[str],
        raw_index: int,
        gerrit_new_line: int) -> Tuple[int, int, int, PatchFileChunkLineMap]:
    in_start = raw_index
        lines.pop(0)
        raw_index += 1
            raw_index,
            PatchFileChunkLineMap(in_range=(in_start, raw_index - 1),
                                  offset=(gerrit_new_line - raw_index)))
        lines: List[str],
        raw_index: int,
        gerrit_new_line: int) -> Tuple[int, int, int, PatchFileChunkLineMap]:
    in_start = raw_index
        lines.pop(0)
        raw_index += 1
            raw_index,
            PatchFileChunkLineMap(in_range=(in_start, raw_index - 1),
                                  offset=(gerrit_new_line - raw_index)))
        lines: List[str],
        raw_index: int,
        gerrit_new_line: int) -> Tuple[int, int, int, PatchFileChunkLineMap]:
    in_start = raw_index
        lines.pop(0)
        raw_index += 1
            raw_index,
            PatchFileChunkLineMap(in_range=(in_start, raw_index - 1),
                                  offset=(gerrit_new_line - raw_index)))
def _parse_patch_file_chunk(lines: List[str],
                            raw_index: int,
                            gerrit_new_line: int) -> Tuple[int, int, int, PatchFileChunkLineMap]:
        ret_val =  _parse_patch_file_added_chunk(lines, raw_index, gerrit_orig_line, gerrit_new_line)
        ret_val = _parse_patch_file_removed_chunk(lines, raw_index, gerrit_orig_line, gerrit_new_line)
        ret_val = _parse_patch_file_unchanged_chunk(lines, raw_index, gerrit_orig_line, gerrit_new_line)
def _parse_patch_file_super_chunk(lines: List[str], raw_index: int) -> List[PatchFileChunkLineMap]:
    lines.pop(0)
    raw_index += 1
         raw_index,
                                          raw_index,
def _parse_patch_file_entry(lines: List[str], index: int) -> Optional[PatchFileLineMap]:
    lines.pop(0)
    index += 1
        lines.pop(0)
        index += 1
        lines.pop(0)
        index += 1
        lines.pop(0)
        index += 1
        lines.pop(0)
        index += 1
    super_chunk = _parse_patch_file_super_chunk(lines, index)
        logging.info('parsed super chunk: %d to %d', index, chunk.in_range[1])
        index = chunk.in_range[1]
        super_chunk = _parse_patch_file_super_chunk(lines, index)
def _parse_patch_header(lines: List[str]) -> int:
    index = 0

            index = i
    del lines[:index]
        lines.pop(0)
        index += 1
        lines.pop(0)
        index += 1
        lines.pop(0)
        index += 1
        lines.pop(0)
        index += 1
        lines.pop(0)
        index += 1
    if DIFF_LINE_MATCHER.match(lines[0]):
        return index
    else:
    lines = raw_patch.split('\n')
    lines = [line.strip() for line in lines]
    index = _parse_patch_header(lines)
    file_entry = _parse_patch_file_entry(lines, index)
        file_entry = _parse_patch_file_entry(lines, index)
        raise ValueError('Could not parse entire file: ' + str(lines))