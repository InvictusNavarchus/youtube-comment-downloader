"""Formatters for YouTube comment output."""

import json
from typing import Dict, Any, TextIO, Optional, List

from .constants import JSON_INDENT


def format_comment_as_json(comment: Dict[str, Any], indent: Optional[int] = None) -> str:
    """
    Format a comment as a JSON string.

    Args:
        comment: Comment data dictionary
        indent: Indentation level (None for no indentation)

    Returns:
        JSON string representation of the comment
    """
    comment_str = json.dumps(comment, ensure_ascii=False, indent=indent)
    if indent is None:
        return comment_str
    padding = ' ' * (2 * indent) if indent else ''
    return ''.join(padding + line for line in comment_str.splitlines(True))


class CommentWriter:
    """Handles writing comments to output files in different formats."""

    def __init__(self, output_file: TextIO, pretty: bool = False):
        """
        Initialize the comment writer.

        Args:
            output_file: File object to write to
            pretty: Whether to use pretty (indented) JSON format
        """
        self.output_file = output_file
        self.pretty = pretty
        self.count = 0
        
        if pretty:
            self.output_file.write('{\n' + ' ' * JSON_INDENT + '"comments": [\n')
    
    def write_comment(self, comment: Dict[str, Any], has_more: bool = True) -> None:
        """
        Write a comment to the output file.

        Args:
            comment: Comment data dictionary
            has_more: Whether more comments will follow
        """
        comment_str = format_comment_as_json(comment, indent=JSON_INDENT if self.pretty else None)
        if self.pretty and has_more:
            comment_str += ','
        print(comment_str.decode('utf-8') if isinstance(comment_str, bytes) else comment_str, 
              file=self.output_file)
        self.count += 1
    
    def finalize(self) -> None:
        """Finalize the output file (add closing brackets for pretty JSON)."""
        if self.pretty:
            self.output_file.write(' ' * JSON_INDENT + ']\n}')
