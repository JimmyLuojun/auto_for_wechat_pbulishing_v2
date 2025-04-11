# src/auto_for_wechat_publishing/core/html_processor.py
"""
html_processor.py

Converts markdown content to HTML format with embedded CSS styles.

Dependencies:
    - markdown
    - exceptions.HTMLConversionError
    - file_handler (to read CSS)

Input: Markdown content, path to CSS file
Output: HTML formatted content
"""
# auto_for_wechat_publishing/core/html_processor.py
import logging
import re
from pathlib import Path
from typing import Callable # To type hint the upload function callback
from markdown import markdown
from bs4 import BeautifulSoup # Using BeautifulSoup for parsing

from ..utils.file_handler import read_file
# Import the specific upload function needed
from ..wechat.api import upload_content_image

logger = logging.getLogger(__name__)

# Regex to identify potential relative or absolute local file paths typical in Markdown
# This might need refinement based on actual usage patterns
# Example: matches ./img.png, ../img.png, /abs/path/img.png, images/img.png
# It AVOIDS http://, https://, data: URIs
LOCAL_IMAGE_SRC_PATTERN = re.compile(r"^(?!https?://|data:).+", re.IGNORECASE)

def process_html_content(
    md_content: str,
    css_path: str | Path,
    markdown_file_path: str | Path, # Need base path to resolve relative image paths
    image_uploader: Callable[[str | Path], str] # Function to upload image and return URL
    ) -> str:
    """
    Converts markdown to styled HTML, uploading local images to WeChat.

    Args:
        md_content: The raw markdown content (without frontmatter).
        css_path: Path to the CSS file for styling.
        markdown_file_path: The original path of the markdown file (for resolving relative image paths).
        image_uploader: A function (like wechat.api.upload_content_image partially applied
                        with access_token and base_url) that takes an image path and returns its WeChat URL.

    Returns:
        The final HTML string ready for the WeChat draft.

    Raises:
        FileNotFoundError: If CSS file or a referenced local image is not found.
        ValueError: If markdown conversion fails or image validation fails during upload.
        RuntimeError: If file reading, image uploading API call, or HTML processing fails.
    """
    logger.info("Starting HTML processing...")
    markdown_dir = Path(markdown_file_path).parent

    # 1. Convert Markdown to HTML body
    try:
        logger.debug("Converting Markdown to HTML...")
        # Enable extensions if needed, e.g., 'markdown.extensions.fenced_code'
        html_body = markdown(md_content, output_format='html5', extensions=['fenced_code'])
        logger.debug("Markdown conversion successful.")
    except Exception as e:
        logger.error(f"Markdown to HTML conversion failed: {e}")
        # Wrapping Markdown library errors
        raise RuntimeError("Markdown to HTML conversion failed") from e

    # 2. Parse HTML for image processing
    logger.debug("Parsing HTML body with BeautifulSoup...")
    # Use 'lxml' for performance if available, fallback to 'html.parser'
    try:
        soup = BeautifulSoup(html_body, 'lxml')
    except ImportError:
        logger.warning("lxml parser not found, falling back to html.parser.")
        soup = BeautifulSoup(html_body, 'html.parser')

    # 3. Find and replace local images
    logger.info("Searching for local images in HTML...")
    images_processed = 0
    img_tags = soup.find_all('img')
    logger.info(f"Found {len(img_tags)} <img> tags.")

    for img in img_tags:
        src = img.get('src')
        if src and LOCAL_IMAGE_SRC_PATTERN.match(src):
            logger.info(f"Found potential local image source: {src}")
            try:
                # Resolve the absolute path of the local image
                # Path(src).is_absolute() checks if it starts with '/'
                if Path(src).is_absolute():
                    local_image_path = Path(src)
                else:
                    # Resolve relative path based on the markdown file's directory
                    local_image_path = (markdown_dir / src).resolve()

                logger.info(f"Resolved local image path: {local_image_path}")

                if not local_image_path.is_file():
                     logger.error(f"Local image file referenced in HTML not found: {local_image_path}")
                     # Option: Raise error, or just log and skip? Let's raise.
                     raise FileNotFoundError(f"Image referenced in markdown not found: {local_image_path}")

                # Upload the image using the provided uploader function
                logger.info(f"Uploading image '{local_image_path.name}' via provided uploader...")
                wechat_url = image_uploader(local_image_path) # This calls wechat.api.upload_content_image

                # Replace the src attribute
                img['src'] = wechat_url
                logger.info(f"Replaced local src '{src}' with WeChat URL: {wechat_url}")
                images_processed += 1

            except (FileNotFoundError, ValueError, RuntimeError) as e:
                # Catch errors from path resolution or the uploader function
                logger.error(f"Failed to process/upload image '{src}': {e}")
                # Re-raise the error to stop the process
                raise e
            except Exception as e:
                 # Catch unexpected errors during image processing
                 logger.error(f"Unexpected error processing image '{src}': {e}")
                 raise RuntimeError(f"Unexpected error processing image '{src}'") from e
        elif src:
            logger.debug(f"Skipping non-local or data URI image source: {src[:50]}...")
        else:
             logger.warning("Found <img> tag without 'src' attribute.")

    logger.info(f"Finished processing images. {images_processed} local images uploaded and replaced.")

    # 4. Get processed HTML string from BeautifulSoup object
    # Decode ensures correct output without entity conversion issues
    processed_html_body = soup.decode()

    # 5. Read and embed CSS
    try:
        logger.info(f"Reading CSS file: {css_path}")
        # read_file handles FileNotFoundError and basic read errors
        css_content = read_file(css_path)
        # Prepend CSS within <style> tags
        final_html = f"<style>\n{css_content}\n</style>\n{processed_html_body}"
        logger.info("CSS embedded successfully.")
    except (FileNotFoundError, RuntimeError) as e:
        logger.error(f"Failed to read or embed CSS from {css_path}: {e}")
        raise e # Re-raise CSS related errors

    logger.info("HTML processing completed.")
    return final_html