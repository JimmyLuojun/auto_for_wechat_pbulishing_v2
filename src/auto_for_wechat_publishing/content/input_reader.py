"""Input reader for processing markdown and metadata files."""

import yaml
from pathlib import Path
from typing import Tuple, Optional, List
from docx import Document

from .data_models import ArticleMetadata


class InputReader:
    """Reads and processes input files (markdown, metadata, etc.)."""

    def __init__(self, input_dir: Path):
        """Initialize with the input directory path."""
        self.input_dir = input_dir

    def read_markdown(self, filename: str = "article.md") -> str:
        """Read markdown content from file."""
        file_path = self.input_dir / filename
        if not file_path.exists():
            raise FileNotFoundError(f"Markdown file not found: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    def read_metadata(self, filename: str = "metadata.docx") -> ArticleMetadata:
        """Read metadata from Word document."""
        file_path = self.input_dir / filename
        if not file_path.exists():
            raise FileNotFoundError(f"Metadata file not found: {file_path}")

        doc = Document(file_path)
        metadata = {}
        
        # Extract metadata from document paragraphs
        for para in doc.paragraphs:
            if ":" in para.text:
                key, value = para.text.split(":", 1)
                metadata[key.strip().lower()] = value.strip()

        return ArticleMetadata(
            title=metadata.get("title", ""),
            author=metadata.get("author", ""),
            summary=metadata.get("summary", ""),
            cover_image=self.input_dir / "inserting_media" / metadata.get("cover_image", ""),
            tags=metadata.get("tags", "").split(",") if metadata.get("tags") else [],
            original_url=metadata.get("original_url"),
        )

    def find_media_files(self) -> Tuple[List[Path], Optional[Path]]:
        """Find all media files in the media directory."""
        media_dir = self.input_dir / "inserting_media"
        if not media_dir.exists():
            return [], None

        media_files = []
        cover_image = None

        for file in media_dir.iterdir():
            if file.is_file():
                if file.name.lower().startswith("cover"):
                    cover_image = file
                else:
                    media_files.append(file)

        return media_files, cover_image 