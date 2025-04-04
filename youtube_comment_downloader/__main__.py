#!/usr/bin/env python
"""Entry point for YouTube comment downloader."""

import sys
import os.path

if __package__ is None:
    path = os.path.realpath(os.path.abspath(__file__))
    sys.path.insert(0, os.path.dirname(os.path.dirname(path)))

from youtube_comment_downloader.cli import main

if __name__ == '__main__':
    sys.exit(main())
