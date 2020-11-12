"""Collection of test helper functions."""

import os
from typing import List

from message import Message

def test_data_path(path='') -> str:
    """Returns an absolute path to the src/test_data/ directory."""
    # We don't have any subdirectories, so dirname should always be src/.
    base = os.path.join(os.path.dirname(__file__), 'test_data')
    if path:
        return os.path.join(base, path)
    return base


def compare_message_subjects(test, messages: List[Message], subjects: List[str]):
    test.assertCountEqual([m.subject for m in messages], subjects)
