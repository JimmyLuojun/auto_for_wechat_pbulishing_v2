# src/auto_for_wechat_publishing/core/html_processor.py
import logging
import re
from pathlib import Path
from typing import Callable
from markdown import markdown
from bs4 import BeautifulSoup, Tag

# Use relative imports for utils and wechat modules
from ..utils.file_handler import read_file
# Note: upload_content_image is NOT imported here anymore, decoupling this module further

logger = logging.getLogger(__name__)
LOCAL_IMAGE_SRC_PATTERN = re.compile(r"^(?!https?://|data:).+", re.IGNORECASE)

# --- Helper function to add inline styles safely (Keep if using inline styles) ---
# (If you reverted the inline style experiment, this helper can be removed)
# def _add_inline_style(tag: Tag, style_string: str):
#     # ... implementation ...

# --- Helper function for image processing ---
def _find_and_replace_local_images(
    soup: BeautifulSoup,
    markdown_dir: Path,
    image_uploader: Callable[[Path], str]
) -> None:
    """
    Finds local images in the parsed HTML, uploads them, and updates src.
    Modifies the soup object in place.

    Args:
        soup: The BeautifulSoup object representing the parsed HTML body.
        markdown_dir: The directory containing the original markdown file (for resolving relative paths).
        image_uploader: The callback function to upload an image Path and return a URL string.

    Raises:
        FileNotFoundError: If a referenced local image is not found.
        ValueError: If image validation fails during upload (via callback).
        RuntimeError: If image uploading API call fails (via callback).
    """
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
                if Path(src).is_absolute():
                    local_image_path = Path(src)
                else:
                    local_image_path = (markdown_dir / src).resolve()

                logger.info(f"Resolved local image path: {local_image_path}")

                if not local_image_path.is_file():
                     logger.error(f"Local image file referenced in HTML not found: {local_image_path}")
                     raise FileNotFoundError(f"Image referenced in markdown not found: {local_image_path}")

                # Upload the image using the provided uploader function
                logger.info(f"Uploading image '{local_image_path.name}' via provided uploader...")
                wechat_url = image_uploader(local_image_path) # Calls the lambda -> wechat.api.upload_content_image

                # Replace the src attribute
                img['src'] = wechat_url
                logger.info(f"Replaced local src '{src}' with WeChat URL: {wechat_url}")
                images_processed += 1

            except (FileNotFoundError, ValueError, RuntimeError) as e:
                # Catch errors from path resolution or the uploader function
                logger.error(f"Failed to process/upload image '{src}': {e}")
                raise e # Re-raise the error to stop the process
            except Exception as e:
                 # Catch unexpected errors during image processing
                 logger.error(f"Unexpected error processing image '{src}': {e}")
                 raise RuntimeError(f"Unexpected error processing image '{src}'") from e
        elif src:
            logger.debug(f"Skipping non-local or data URI image source: {src[:50]}...")
        else:
             logger.warning("Found <img> tag without 'src' attribute.")

    logger.info(f"Finished processing images. {images_processed} local images uploaded and replaced.")
# --- End Helper ---

def process_html_content(
    md_content: str,
    css_path: str | Path,
    markdown_file_path: str | Path,
    image_uploader: Callable[[Path], str] # Changed arg type hint slightly
    ) -> str:
    """
    Converts markdown to HTML, handles image uploads, and embeds CSS.

    Args:
        md_content: The raw markdown content (without frontmatter).
        css_path: Path to the CSS file for styling.
        markdown_file_path: The original path of the markdown file.
        image_uploader: Function that takes an image Path and returns its WeChat URL.

    Returns:
        The final HTML string (with embedded CSS and WeChat image URLs).
    """
    logger.info("Starting HTML processing...")
    markdown_dir = Path(markdown_file_path).parent # Used for resolving images

    # 1. Convert Markdown to HTML body
    try:
        logger.debug("Converting Markdown to HTML...")
        html_body = markdown(md_content, output_format='html5', extensions=['fenced_code'])
        logger.debug("Markdown conversion successful.")
    except Exception as e:
        logger.error(f"Markdown to HTML conversion failed: {e}")
        raise RuntimeError("Markdown to HTML conversion failed") from e

    # 2. Parse HTML
    logger.debug("Parsing HTML body with BeautifulSoup...")
    try:
        soup = BeautifulSoup(html_body, 'lxml')
    except ImportError:
        logger.warning("lxml parser not found, falling back to html.parser.")
        soup = BeautifulSoup(html_body, 'html.parser')

    # 3. Find and replace local images (using helper function)
    # This modifies the 'soup' object in place
    _find_and_replace_local_images(soup, markdown_dir, image_uploader)

    # --- (Remove inline styling block if you reverted that change) ---

    # 4. Get processed HTML string
    processed_html_body = soup.decode()

    # 5. Read CSS file and embed its content in <style> tags
    try:
        logger.info(f"Reading CSS file for embedding: {css_path}")
        css_content = read_file(css_path)
        if css_content.strip():
             final_html = f"<style>\n{css_content.strip()}\n</style>\n{processed_html_body}"
             logger.info("CSS embedded successfully.")
        else:
             final_html = processed_html_body
             logger.info("CSS file was empty, skipping embedding.")
    except FileNotFoundError:
        logger.warning(f"CSS file not found at {css_path}. Proceeding without embedded styles.")
        final_html = processed_html_body
    except Exception as e:
        logger.error(f"Failed to read or embed CSS from {css_path}: {e}")
        raise RuntimeError(f"Failed to read or embed CSS from {css_path}") from e

    logger.info("HTML processing completed.")
    return final_html