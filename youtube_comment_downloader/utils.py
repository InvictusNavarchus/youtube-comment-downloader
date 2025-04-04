"""Utility functions for YouTube comment downloader."""

import json
import re
import os
from typing import Dict, Any, List, Generator, Optional, Union, Tuple


def regex_search(text: str, pattern: str, group: int = 1, default: Any = None) -> Any:
    """
    Search for a pattern in text and return the specified group if found.

    Args:
        text: Text to search in
        pattern: Regular expression pattern
        group: Capture group to return
        default: Default value to return if pattern not found

    Returns:
        The matched group or default value
    """
    match = re.search(pattern, text)
    return match.group(group) if match else default


def search_dict(partial: Union[Dict, List], search_key: str) -> Generator[Any, None, None]:
    """
    Search recursively for a key in a nested dictionary or list.

    Args:
        partial: Dictionary or list to search
        search_key: Key to search for

    Yields:
        Values found for the search key
    """
    stack = [partial]
    while stack:
        current_item = stack.pop()
        if isinstance(current_item, dict):
            for key, value in current_item.items():
                if key == search_key:
                    yield value
                else:
                    stack.append(value)
        elif isinstance(current_item, list):
            stack.extend(current_item)


def ensure_directory_exists(filepath: str) -> None:
    """
    Ensure the directory for the given filepath exists.

    Args:
        filepath: Path to a file
    """
    if os.sep in filepath:
        directory = os.path.dirname(filepath)
        if not os.path.exists(directory):
            os.makedirs(directory)
