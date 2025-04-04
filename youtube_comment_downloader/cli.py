"""Command-line interface for YouTube comment downloader."""

import argparse
import io
import sys
import time
from typing import List, Optional

from .constants import SORT_BY_POPULAR, SORT_BY_RECENT, JSON_INDENT
from .downloader import YoutubeCommentDownloader
from .exceptions import YouTubeCommentDownloaderError
from .formatters import CommentWriter
from .utils import ensure_directory_exists


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """
    Parse command line arguments.

    Args:
        argv: Command line arguments (uses sys.argv if None)

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        add_help=False, 
        description='Download Youtube comments without using the Youtube API'
    )
    parser.add_argument('--help', '-h', action='help', default=argparse.SUPPRESS, 
                      help='Show this help message and exit')
    parser.add_argument('--youtubeid', '-y', 
                      help='ID of Youtube video for which to download the comments')
    parser.add_argument('--url', '-u', 
                      help='Youtube URL for which to download the comments')
    parser.add_argument('--output', '-o', 
                      help='Output filename (output format is line delimited JSON)')
    parser.add_argument('--pretty', '-p', action='store_true', 
                      help='Change the output format to indented JSON')
    parser.add_argument('--limit', '-l', type=int, 
                      help='Limit the number of comments')
    parser.add_argument('--language', '-a', type=str, default=None, 
                      help='Language for Youtube generated text (e.g. en)')
    parser.add_argument('--sort', '-s', type=int, default=SORT_BY_RECENT,
                      help=f'Whether to download popular ({SORT_BY_POPULAR}) or recent ({SORT_BY_RECENT}) comments. Defaults to {SORT_BY_RECENT}')

    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    """
    Main entry point for the command line interface.

    Args:
        argv: Command line arguments (uses sys.argv if None)

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        args = parse_args(argv)

        youtube_id = args.youtubeid
        youtube_url = args.url
        output = args.output
        limit = args.limit
        pretty = args.pretty
        
        # Validate required arguments
        if (not youtube_id and not youtube_url) or not output:
            print('Error: you need to specify a Youtube ID/URL and an output filename')
            return 1

        # Ensure output directory exists
        ensure_directory_exists(output)

        # Initialize downloader
        print('Downloading Youtube comments for', youtube_id or youtube_url)
        downloader = YoutubeCommentDownloader()
        
        # Get comment generator
        generator = (
            downloader.get_comments(youtube_id, args.sort, args.language)
            if youtube_id
            else downloader.get_comments_from_url(youtube_url, args.sort, args.language)
        )

        # Download and write comments
        with io.open(output, 'w', encoding='utf8') as fp:
            writer = CommentWriter(fp, pretty)
            start_time = time.time()
            
            # Process first comment
            try:
                comment = next(generator, None)
                while comment:
                    has_more = not limit or writer.count < limit - 1
                    writer.write_comment(comment, has_more=has_more)
                    
                    # Progress indicator
                    sys.stdout.write(f'Downloaded {writer.count} comment(s)\r')
                    sys.stdout.flush()
                    
                    # Get next comment if within limit
                    comment = None if limit and writer.count >= limit else next(generator, None)
                    
                # Finalize the output
                writer.finalize()
                
            except StopIteration:
                # Handle empty generator
                writer.finalize()

            elapsed = time.time() - start_time
            print(f'\n[{elapsed:.2f} seconds] Done!')
        
        return 0

    except YouTubeCommentDownloaderError as e:
        print(f'Error: {str(e)}')
        return 1
    except Exception as e:
        print(f'Unexpected error: {str(e)}')
        return 1
