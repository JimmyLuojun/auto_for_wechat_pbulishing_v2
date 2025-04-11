# src/auto_for_wechat_publishing/main.py
import logging
import argparse
from pathlib import Path
import sys
# import webbrowser # No longer needed here
# import tempfile   # No longer needed here
# import time       # No longer needed here

# Import utility functions
from .utils.logging_setup import setup_logging
from .utils.config_loader import load_config, get_env_variable
# from .utils.file_handler import write_file # Only needed if saving intermediate HTML

# --- Import the preview function ---
from .utils.preview import show_preview_and_confirm
# --- End Import ---

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
    # (Keep this function as it was)
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
            log_file=log_config.get('log_file') or None
        )
        app_id = get_env_variable("WECHAT_APP_ID")
        app_secret = get_env_variable("WECHAT_APP_SECRET")
        # Read base_url from [WECHAT_API] section for consistency if defined there, else default
        # Note: Your config.ini has it under [wechat], let's assume that was intended or adjust config.ini
        api_config = config.get('WECHAT_API', config.get('wechat', {})) # Check both sections
        api_base_url = api_config.get('base_url', api_config.get('access_token_url', 'https://api.weixin.qq.com').rsplit('/cgi-bin/', 1)[0]) # Try to infer base_url

        # --- CORRECTED CSS Path Reading ---
        html_config = config.get('html', {}) # Get the [html] section
        # Read 'css_file' from [html], fallback to default if key or section missing
        css_path = html_config.get('css_file', 'data/templates/style.css')
        print(f"DEBUG: Using CSS Path: {css_path}") # Temporary debug print
        # --- End Correction ---

    except (FileNotFoundError, ValueError, KeyError) as e:
        logging.basicConfig(level=logging.ERROR)
        logging.error(f"Configuration Error: {e}", exc_info=False)
        print(f"Error: Configuration failed. {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
         logging.basicConfig(level=logging.ERROR)
         logging.error(f"Unexpected error during configuration: {e}", exc_info=True)
         print(f"Error: Unexpected error during configuration. Check logs.", file=sys.stderr)
         sys.exit(1)

    logger.info("Configuration loaded, logging setup complete.")
    logger.info(f"Processing article: {args.markdown_file}")

    access_token = None

    try:
        # (Steps 2-5 remain the same)
        logger.info("Fetching WeChat Access Token...")
        access_token = get_access_token(app_id, app_secret, api_base_url)
        logger.info("Access Token obtained successfully.")

        logger.info("Reading article metadata...")
        markdown_path = Path(args.markdown_file)
        metadata = extract_metadata(markdown_path)
        logger.info(f"Metadata loaded for title: '{metadata['title']}'")

        cover_image_path_str = metadata['cover_image_path']
        logger.info(f"Uploading cover image: {cover_image_path_str}")
        thumb_media_id = upload_thumb_media(access_token, cover_image_path_str, api_base_url)
        logger.info(f"Cover image uploaded. Thumb Media ID: {thumb_media_id}")

        logger.info("Extracting markdown content...")
        md_content = extract_markdown_content(markdown_path)

        # 6. Process HTML
        logger.info("Processing HTML content (incl. image uploads)...")
        uploader_callback = lambda img_path: upload_content_image(
            access_token=access_token, image_path=img_path, base_url=api_base_url
        )
        final_html = process_html_content(
            md_content=md_content, css_path=css_path,
            markdown_file_path=markdown_path, image_uploader=uploader_callback
        )
        logger.info("HTML content processed successfully.")

        # Preview Step
        show_preview_and_confirm(final_html)

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
         logger.error(f"Processing failed: {e}", exc_info=False)
         logger.debug("Detailed traceback:", exc_info=True)
         print(f"\nError: Processing failed. {e}", file=sys.stderr)
         sys.exit(1)
    except KeyboardInterrupt: # Catch Ctrl+C during the input prompt in preview
        logger.warning("Operation cancelled by user during preview.")
        print("\nOperation cancelled.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        print(f"\nError: An unexpected error occurred. Check logs for details.", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    run()