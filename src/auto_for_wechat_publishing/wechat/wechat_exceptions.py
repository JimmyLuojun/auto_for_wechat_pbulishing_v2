"""Custom exceptions for WeChat API interactions."""

class WeChatAPIError(Exception):
    """Base exception for WeChat API errors."""
    pass


class AuthenticationError(WeChatAPIError):
    """Raised when authentication with WeChat API fails."""
    pass


class MediaUploadError(WeChatAPIError):
    """Raised when media upload fails."""
    pass


class ArticlePublishError(WeChatAPIError):
    """Raised when article publishing fails."""
    pass


class InvalidMediaError(WeChatAPIError):
    """Raised when media file is invalid or unsupported."""
    pass


class RateLimitError(WeChatAPIError):
    """Raised when WeChat API rate limit is exceeded."""
    pass 