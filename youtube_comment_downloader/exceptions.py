"""Custom exceptions for the YouTube comment downloader."""

class YouTubeCommentDownloaderError(Exception):
    """Base exception for YouTube comment downloader."""
    pass

class CommentDownloadError(YouTubeCommentDownloaderError):
    """Exception raised when comments cannot be downloaded."""
    pass

class SortingError(YouTubeCommentDownloaderError):
    """Exception raised when the requested sorting method cannot be applied."""
    pass

class CommentsDisabledError(YouTubeCommentDownloaderError):
    """Exception raised when comments are disabled for a video."""
    pass

class YouTubeApiError(YouTubeCommentDownloaderError):
    """Exception raised when YouTube API returns an error."""
    pass
