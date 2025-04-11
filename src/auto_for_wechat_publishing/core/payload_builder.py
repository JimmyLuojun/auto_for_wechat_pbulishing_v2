"""
payload_builder.py

Constructs JSON payload for WeChat Draft API.

Dependencies:
    - wechat.schemas (WeChat payload schemas)

Input: Metadata dict, HTML content, thumb_media_id
Output: JSON payload dict
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

def build_draft_payload(metadata: Dict[str, Any], html_content: str, thumb_media_id: str) -> Dict[str, Any]:
    """
    Builds the payload dictionary for adding a draft article to WeChat.

    Args:
        metadata: Dictionary containing article metadata (from YAML frontmatter).
                  Expected keys: 'title' (required), 'author', 'digest',
                  'content_source_url', 'need_open_comment', 'only_fans_can_comment'.
        html_content: The final processed HTML content of the article.
        thumb_media_id: The permanent media ID for the cover image thumbnail.

    Returns:
        A dictionary formatted for the WeChat draft/add API.

    Raises:
        KeyError: If the required 'title' metadata is missing.
        ValueError: If thumb_media_id is empty.
    """
    logger.info("Building payload for WeChat draft API...")

    # Ensure required fields are present (title should be validated earlier, but double-check)
    if not metadata.get("title"):
        raise KeyError("Required metadata 'title' is missing.")
    if not thumb_media_id:
        raise ValueError("thumb_media_id cannot be empty.")

    # Determine digest: use provided, else truncate HTML, ensure max 54 chars
    digest = metadata.get("digest", "")
    if not digest and html_content:
        # Basic truncation - remove HTML tags first for better results?
        # For simplicity now, just truncate raw HTML. Max 54 chars for digest.
        # A better approach would strip tags then truncate text.
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_content, 'lxml') # Or 'html.parser'
        plain_text = soup.get_text()
        digest = plain_text[:54]
        logger.debug(f"Generated digest by truncating content: {digest}")
    elif len(digest) > 54:
         logger.warning(f"Provided digest length ({len(digest)}) exceeds 54 characters. Truncating.")
         digest = digest[:54]


    # Structure according to WeChat draft/add API documentation for 'news' type
    article_payload = {
        # "article_type": "news", # Default, can be omitted unless using "newspic"
        "title": metadata["title"],
        "author": metadata.get("author", ""), # Optional, defaults if empty
        "digest": digest,
        "content": html_content,
        "content_source_url": metadata.get("content_source_url", ""), # Optional
        "thumb_media_id": thumb_media_id, # Required
        "need_open_comment": int(metadata.get("need_open_comment", 0)), # Default 0
        "only_fans_can_comment": int(metadata.get("only_fans_can_comment", 0)) # Default 0
        # Add cropping fields (pic_crop_235_1, pic_crop_1_1) if needed
    }

    # The API expects a list under the 'articles' key
    final_payload = {"articles": [article_payload]}
    logger.info("Draft payload built successfully.")
    # logger.debug(f"Payload: {final_payload}") # Be careful logging full HTML content

    return final_payload
