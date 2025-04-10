"""Media extractor for processing images and other media files."""

import re
from pathlib import Path
from typing import List, Set
from bs4 import BeautifulSoup


class MediaExtractor:
    """Extracts and processes media files from HTML content."""

    def __init__(self, media_dir: Path):
        """Initialize with the directory containing media files."""
        self.media_dir = media_dir

    def extract_image_paths(self, html: str) -> Set[Path]:
        """Extract local image paths from HTML content."""
        soup = BeautifulSoup(html, "html.parser")
        image_paths = set()

        # Find all img tags
        for img in soup.find_all("img"):
            src = img.get("src", "")
            if src and not src.startswith(("http://", "https://")):
                # Convert relative path to absolute path
                image_path = self.media_dir / src
                if image_path.exists():
                    image_paths.add(image_path)

        return image_paths

    def validate_media_files(self, files: List[Path]) -> List[Path]:
        """Validate media files and return only existing ones."""
        return [f for f in files if f.exists()]

    def process_media_references(self, html: str) -> str:
        """Process media references in HTML to ensure correct paths."""
        soup = BeautifulSoup(html, "html.parser")

        # Update image src attributes
        for img in soup.find_all("img"):
            src = img.get("src", "")
            if src and not src.startswith(("http://", "https://")):
                # Convert to absolute path for WeChat
                img["src"] = str(self.media_dir / src)

        return str(soup) 