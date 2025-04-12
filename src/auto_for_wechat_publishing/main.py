# src/auto_for_wechat_publishing/main.py
import logging
import argparse
from pathlib import Path
import sys
from typing import Dict, Any, Tuple

# Import utility functions
from .utils.logging_setup import setup_logging
from .utils.config_loader import load_config, get_env_variable
from .utils.preview import show_preview_and_confirm

# Import core processing modules
from .core.metadata_reader import extract_metadata
from .core.markdown_processor import extract_markdown_content
from .core.html_processor import process_html_content
from .core.payload_builder import build_draft_payload

# Import WeChat API interaction modules
from .wechat.auth import get_access_token
from .wechat.api import upload_thumb_media, add_draft, upload_content_image

logger = logging.getLogger(__name__)

CONFIG_FILE_PATH = "config/config.ini"
ENV_FILE_PATH = ".env"

# --- Helper Function for Setup ---
def _initial_setup(args: argparse.Namespace) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Loads config, sets up logging, gets credentials and paths."""
    config = load_config(args.config, args.env)
    log_config = config.get('LOGGING', {})
    setup_logging(
        log_level_str=log_config.get('level', 'INFO'),
        log_file=log_config.get('log_file') or None
    )

    app_id = get_env_variable("WECHAT_APP_ID")
    app_secret = get_env_variable("WECHAT_APP_SECRET")
    api_config = config.get('WECHAT_API', config.get('wechat', {}))
    api_base_url = api_config.get('base_url', 'https://api.weixin.qq.com')

    html_config = config.get('html', {})
    css_path = html_config.get('css_file', 'data/templates/style.css')
    # Get placeholder from config, with a default
    default_placeholder = "<p>Please paste formatted content here.</p>"
    placeholder_html = html_config.get('placeholder_html', default_placeholder)


    auth_info = {"app_id": app_id, "app_secret": app_secret, "base_url": api_base_url}
    settings = {"css_path": css_path, "placeholder_html": placeholder_html}

    logger.info("Configuration loaded, logging setup complete.")
    return auth_info, settings
# --- End Helper ---

def parse_arguments() -> argparse.Namespace:
    # (Keep this function as it is)
    parser = argparse.ArgumentParser(description="Publish Markdown articles to WeChat Official Account drafts.")
    parser.add_argument("markdown_file",type=str,help="Path to the input Markdown file.")
    parser.add_argument("-c", "--config",type=str,default=CONFIG_FILE_PATH, help=f"Path to the configuration INI file (default: {CONFIG_FILE_PATH}).")
    parser.add_argument("--env",type=str,default=ENV_FILE_PATH,help=f"Path to the environment file (default: {ENV_FILE_PATH}).")
    return parser.parse_args()


def run():
    """Main execution function."""
    args = parse_arguments()
    auth_info = {}
    settings = {}
    final_html = "" # Ensure defined for potential use in error handling

    # 1. Initial Setup (Config, Logging, Credentials)
    try:
        auth_info, settings = _initial_setup(args)
    except (FileNotFoundError, ValueError, KeyError) as e:
        # Basic logger needed if setup_logging failed
        logging.basicConfig(level=logging.ERROR)
        logging.error(f"Configuration Error: {e}", exc_info=False)
        print(f"Error: Configuration failed. {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
         logging.basicConfig(level=logging.ERROR)
         logging.error(f"Unexpected error during initial setup: {e}", exc_info=True)
         print(f"Error: Unexpected error during initial setup. Check logs.", file=sys.stderr)
         sys.exit(1)

    logger.info(f"Processing article: {args.markdown_file}")

    try:
        # 2. Get Access Token
        logger.info("Fetching WeChat Access Token...")
        access_token = get_access_token(
            auth_info["app_id"], auth_info["app_secret"], auth_info["base_url"]
        )
        logger.info("Access Token obtained successfully.")

        # 3. Read Metadata
        logger.info("Reading article metadata...")
        markdown_path = Path(args.markdown_file)
        metadata = extract_metadata(markdown_path)
        logger.info(f"Metadata loaded for title: '{metadata['title']}'")

        # 4. Upload Cover Image
        cover_image_path_str = metadata['cover_image_path']
        logger.info(f"Uploading cover image: {cover_image_path_str}")
        thumb_media_id = upload_thumb_media(
            access_token, cover_image_path_str, auth_info["base_url"]
        )
        logger.info(f"Cover image uploaded. Thumb Media ID: {thumb_media_id}")

        # 5. Extract Markdown Content
        logger.info("Extracting markdown content...")
        md_content = extract_markdown_content(markdown_path)

        # 6. Process HTML for Preview
        logger.info("Processing HTML content for PREVIEW...")
        uploader_callback = lambda img_path: upload_content_image(
            access_token=access_token, image_path=img_path, base_url=auth_info["base_url"]
        )
        final_html = process_html_content(
            md_content=md_content, css_path=settings["css_path"],
            markdown_file_path=markdown_path, image_uploader=uploader_callback
        )
        logger.info("HTML content for PREVIEW processed successfully.")

        # 7. Show Preview and Get Confirmation
        show_preview_and_confirm(final_html)
        # Execution continues only if user presses Enter

        # 8. Build Draft Payload (Using Placeholder)
        logger.info("Building draft payload with placeholder content...")
        placeholder_content = settings["placeholder_html"] # Get from settings
        draft_payload = build_draft_payload(metadata, placeholder_content, thumb_media_id)
        # (Optional size check removed for brevity, can be added back)

        # 9. Add Draft to WeChat
        logger.info("Submitting draft with placeholder content to WeChat...")
        draft_media_id = add_draft(access_token, draft_payload, auth_info["base_url"])
        logger.info(f"Successfully submitted draft placeholder to WeChat! Draft Media ID: {draft_media_id}")
        print(f"\nSuccess! Draft created for article '{metadata['title']}'.")
        print(f"Draft Media ID: {draft_media_id}")
        print("\nIMPORTANT: Now copy the styled content from the browser preview and paste it into the draft in the WeChat editor.")

    # --- Consolidated Error Handling ---
    except (FileNotFoundError, ValueError, KeyError, RuntimeError) as e:
         logger.error(f"Processing failed: {e}", exc_info=False)
         logger.debug("Detailed traceback:", exc_info=True)
         # Add specific checks back here if needed (e.g., for 45004)
         print(f"\nError: Processing failed. {e}", file=sys.stderr)
         sys.exit(1)
    except KeyboardInterrupt:
        logger.warning("Operation cancelled by user during preview.")
        print("\nOperation cancelled.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        print(f"\nError: An unexpected error occurred. Check logs for details.", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    run()