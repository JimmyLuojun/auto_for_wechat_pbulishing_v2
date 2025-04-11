"""
main.py

Entry point for the WeChat publishing automation script.

Dependencies:
    - core modules: markdown_processor, html_processor, payload_builder
    - wechat modules: api, auth
    - utils: logging_setup, file_handler

Input: markdown articles and media files
Output: Published articles to WeChat Draft Box
"""
# auto_for_wechat_publishing/main.py
import logging
import argparse
from pathlib import Path
import sys
from functools import partial # To create upload callback with token

# Import utility functions
from .utils.logging_setup import setup_logging
from .utils.config_loader import load_config, get_env_variable
from .utils.file_handler import read_file, write_file # If needed for output

# Import core processing modules
from .core.metadata_reader import extract_metadata
from .core.markdown_processor import extract_markdown_content
from .core.html_processor import process_html_content
from .core.payload_builder import build_draft_payload

# Import WeChat API interaction modules
from .wechat.auth import get_access_token
from .wechat.api import upload_thumb_media, add_draft, upload_content_image

# Initialize logger for this module
logger = logging.getLogger(__name__)

# --- Configuration Paths ---
CONFIG_FILE_PATH = "config/config.ini"
ENV_FILE_PATH = ".env"

def parse_arguments() -> argparse.Namespace:
    """Parses command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Publish Markdown articles to WeChat Official Account drafts."
    )
    parser.add_argument(
        "markdown_file",
        type=str,
        help="Path to the input Markdown file.",
    )
    parser.add_argument(
        "-c", "--config",
        type=str,
        default=CONFIG_FILE_PATH,
        help=f"Path to the configuration INI file (default: {CONFIG_FILE_PATH}).",
    )
    parser.add_argument(
        "--env",
        type=str,
        default=ENV_FILE_PATH,
        help=f"Path to the environment file (default: {ENV_FILE_PATH}).",
    )
    return parser.parse_args()

def run():
    """Main execution function."""
    args = parse_arguments()

    # 1. Load Configuration and Setup Logging
    try:
        config = load_config(args.config, args.env)
        log_config = config.get('LOGGING', {})
        setup_logging(
            log_level_str=log_config.get('level', 'INFO'),
            log_file=log_config.get('log_file') or None # Pass None if empty
        )
        # Load required environment variables after .env is potentially loaded
        app_id = get_env_variable("WECHAT_APP_ID")
        app_secret = get_env_variable("WECHAT_APP_SECRET")
        api_base_url = config.get('WECHAT_API', {}).get('base_url', 'https://api.weixin.qq.com')
        paths_config = config.get('PATHS', {})
        css_path = paths_config.get('css_template', 'data/templates/style.css')

    except (FileNotFoundError, ValueError, KeyError) as e:
        # Log error even if logging setup failed partially
        logging.basicConfig(level=logging.ERROR) # Basic fallback logger
        logging.error(f"Configuration Error: {e}", exc_info=False) # Log concise error
        print(f"Error: Configuration failed. {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
         logging.basicConfig(level=logging.ERROR)
         logging.error(f"Unexpected error during configuration: {e}", exc_info=True)
         print(f"Error: Unexpected error during configuration. Check logs.", file=sys.stderr)
         sys.exit(1)

    logger.info("Configuration loaded, logging setup complete.")
    logger.info(f"Processing article: {args.markdown_file}")

    access_token = None # Initialize

    try:
        # 2. Get WeChat Access Token
        logger.info("Fetching WeChat Access Token...")
        access_token = get_access_token(app_id, app_secret, api_base_url)
        logger.info("Access Token obtained successfully.")

        # 3. Read Metadata
        logger.info("Reading article metadata...")
        markdown_path = Path(args.markdown_file)
        metadata = extract_metadata(markdown_path)
        logger.info(f"Metadata loaded for title: '{metadata['title']}'")

        # 4. Upload Cover Image (Thumbnail)
        cover_image_path_str = metadata['cover_image_path'] # Already validated in extract_metadata
        logger.info(f"Uploading cover image: {cover_image_path_str}")
        thumb_media_id = upload_thumb_media(access_token, cover_image_path_str, api_base_url)
        logger.info(f"Cover image uploaded. Thumb Media ID: {thumb_media_id}")

        # 5. Extract Markdown Content
        logger.info("Extracting markdown content...")
        md_content = extract_markdown_content(markdown_path)

        # 6. Process HTML (Convert MD, Inject CSS, Upload/Replace Content Images)
        logger.info("Processing HTML content (incl. image uploads)...")
        # Create a partial function for the image uploader callback, pre-filling token and url
        # With this line:
        uploader_callback = lambda img_path: upload_content_image(
            access_token=access_token,
            image_path=img_path,
            base_url=api_base_url
        )
        final_html = process_html_content(
            md_content=md_content,
            css_path=css_path,
            markdown_file_path=markdown_path,
            image_uploader=uploader_callback # Pass the callback
        )
        logger.info("HTML content processed successfully.")
        # Optional: Save intermediate HTML for debugging
        # html_output_path = Path(config['PATHS']['output_dir']) / f"{markdown_path.stem}.html"
        # write_file(html_output_path, final_html)
        # logger.info(f"Intermediate HTML saved to {html_output_path}")


        # 7. Build Draft Payload
        logger.info("Building draft payload...")
        draft_payload = build_draft_payload(metadata, final_html, thumb_media_id)

        # 8. Add Draft to WeChat
        logger.info("Submitting draft to WeChat...")
        draft_media_id = add_draft(access_token, draft_payload, api_base_url)
        logger.info(f"Successfully submitted draft to WeChat! Draft Media ID: {draft_media_id}")
        print(f"\nSuccess! Article '{metadata['title']}' uploaded as draft.")
        print(f"Draft Media ID: {draft_media_id}")

    except (FileNotFoundError, ValueError, KeyError, RuntimeError) as e:
         logger.error(f"Processing failed: {e}", exc_info=False) # Log concise error for known types
         logger.debug("Detailed traceback:", exc_info=True) # Log full trace only at debug level
         print(f"\nError: Processing failed. {e}", file=sys.stderr)
         sys.exit(1)
    except Exception as e:
        # Catch any unexpected errors during the main workflow
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        print(f"\nError: An unexpected error occurred. Check logs for details.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    # This allows running the script directly, although using the Poetry script is preferred
    run()