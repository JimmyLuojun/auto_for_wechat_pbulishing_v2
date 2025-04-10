"""Data models for article content and metadata."""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict, Any


@dataclass
class ArticleMetadata:
    """Metadata for a WeChat article."""
    title: str
    author: str
    summary: str
    cover_image: Optional[Path] = None
    tags: List[str] = None
    original_url: Optional[str] = None
    custom_data: Dict[str, Any] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.custom_data is None:
            self.custom_data = {}


@dataclass
class ArticleContent:
    """Processed article content ready for WeChat publishing."""
    html_content: str
    media_files: List[Path]
    metadata: ArticleMetadata

    @property
    def has_media(self) -> bool:
        """Check if the article contains any media files."""
        return len(self.media_files) > 0


@dataclass
class WeChatArticle:
    """Final article data structure for WeChat API."""
    title: str
    content: str
    author: str
    digest: str
    content_source_url: Optional[str] = None
    thumb_media_id: Optional[str] = None
    need_open_comment: bool = True
    only_fans_can_comment: bool = False 