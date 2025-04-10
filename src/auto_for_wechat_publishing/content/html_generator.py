"""HTML generator for converting Markdown to WeChat-compatible HTML."""

import markdown
from pathlib import Path
from typing import List, Optional

from .data_models import ArticleContent, ArticleMetadata


class HTMLGenerator:
    """Converts Markdown to HTML and applies WeChat-specific styling."""

    def __init__(self, css_path: Optional[Path] = None):
        """Initialize the HTML generator with optional CSS file."""
        self.css_path = css_path
        self._load_css()

    def _load_css(self) -> None:
        """Load CSS from file if provided."""
        self.css = ""
        if self.css_path and self.css_path.exists():
            with open(self.css_path, "r", encoding="utf-8") as f:
                self.css = f.read()

    def convert_markdown(self, markdown_text: str) -> str:
        """Convert Markdown text to HTML."""
        html = markdown.markdown(
            markdown_text,
            extensions=[
                "markdown.extensions.tables",
                "markdown.extensions.fenced_code",
                "markdown.extensions.codehilite",
            ],
        )
        return html

    def wrap_in_wechat_format(self, html: str) -> str:
        """Wrap HTML content in WeChat-compatible format with CSS."""
        return f"""<div class="rich_media_content">
{html}
</div>"""

    def process_article(
        self, markdown_text: str, metadata: ArticleMetadata, media_files: List[Path]
    ) -> ArticleContent:
        """Process a complete article from Markdown to WeChat-ready HTML."""
        html = self.convert_markdown(markdown_text)
        wrapped_html = self.wrap_in_wechat_format(html)
        return ArticleContent(
            html_content=wrapped_html,
            media_files=media_files,
            metadata=metadata,
        ) 