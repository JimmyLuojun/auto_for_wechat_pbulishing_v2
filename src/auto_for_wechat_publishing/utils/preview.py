# src/auto_for_wechat_publishing/utils/preview.py
"""
Handles generating and displaying a local HTML preview in the browser
and pausing for user confirmation.
"""

import logging
import webbrowser
import tempfile
from pathlib import Path
import time
import os

logger = logging.getLogger(__name__)

def show_preview_and_confirm(html_content: str) -> bool:
    """
    Saves HTML content to a temporary file, opens it in the default browser,
    and prompts the user to continue or cancel.

    Args:
        html_content: The HTML string to preview.

    Returns:
        True if the user presses Enter to continue, raises KeyboardInterrupt
        if the user presses Ctrl+C. (The function doesn't explicitly return
        False, cancellation is handled via exception in the caller).
    """
    temp_html_file_path = None
    try:
        logger.info("Preparing local preview...")
        # Create a temporary HTML file that persists after closing the handle
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.html', delete=False, encoding='utf-8'
        ) as tmp_file:
            tmp_file.write(html_content)
            temp_html_file_path = tmp_file.name
            logger.info(f"Temporary preview file created at: {temp_html_file_path}")

        # Convert the file path to a file:// URL
        file_url = Path(temp_html_file_path).resolve().as_uri()

        # Open the file in the default web browser
        logger.info("Opening preview in default browser...")
        opened = webbrowser.open(file_url)
        if not opened:
            logger.warning("Could not automatically open browser. Please open the file manually.")
            print(f"\nPlease open this file manually in your browser:\n{temp_html_file_path}\n")

        time.sleep(1) # Give browser a moment to launch/load

        # Pause script and wait for user confirmation
        input("\n---> Preview should be open in browser.\n---> Press Enter to continue and upload draft to WeChat, or Ctrl+C to cancel...\n")
        logger.info("User pressed Enter to continue.")
        return True # Indicate confirmation

    except Exception as preview_err:
        # Log error but allow continuing, as preview failure shouldn't stop upload
        logger.error(f"Failed to create or open local preview: {preview_err}", exc_info=True)
        # Still prompt the user
        try:
            input("\n---> Could not open local preview (see logs).\n---> Press Enter to continue and upload draft to WeChat, or Ctrl+C to cancel...\n")
            logger.info("User pressed Enter to continue despite preview error.")
            return True # Indicate confirmation despite preview error
        except KeyboardInterrupt:
             raise # Re-raise Ctrl+C immediately
    finally:
        # Clean up the temporary file
        if temp_html_file_path:
            try:
                logger.debug(f"Attempting to clean up temporary file: {temp_html_file_path}")
                # Use os.unlink for better compatibility sometimes
                os.unlink(temp_html_file_path)
                # Path(temp_html_file_path).unlink(missing_ok=True) # Alternative
            except Exception as cleanup_err:
                # Log warning but don't fail the main process
                logger.warning(f"Could not delete temporary preview file {temp_html_file_path}: {cleanup_err}")