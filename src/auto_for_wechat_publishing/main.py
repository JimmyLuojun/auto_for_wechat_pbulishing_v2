"""Main script for WeChat article publishing."""

import logging
from pathlib import Path

from .configuration import SETTINGS
from .content.html_generator import HTMLGenerator
from .content.media_extractor import MediaExtractor
from .content.input_reader import InputReader
from .content.data_models import WeChatArticle
from .wechat.wechat_api_client import WeChatAPIClient
from .wechat.wechat_exceptions import WeChatAPIError


def setup_logging():
    """Configure logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    return logging.getLogger(__name__)


def main():
    """Main workflow for publishing articles to WeChat."""
    logger = setup_logging()
    logger.info("Starting WeChat article publishing process")

    try:
        # Initialize components
        input_reader = InputReader(Path(SETTINGS["paths"]["input_dir"]))
        html_generator = HTMLGenerator(
            Path(SETTINGS["paths"]["templates_dir"]) / SETTINGS["content"]["default_css"]
        )
        media_extractor = MediaExtractor(Path(SETTINGS["paths"]["media_dir"]))
        wechat_client = WeChatAPIClient(
            SETTINGS["wechat"]["app_id"], SETTINGS["wechat"]["secret"]
        )

        # Read input files
        logger.info("Reading input files")
        markdown_content = input_reader.read_markdown()
        metadata = input_reader.read_metadata()
        media_files, cover_image = input_reader.find_media_files()

        # Process content
        logger.info("Processing article content")
        article_content = html_generator.process_article(
            markdown_content, metadata, media_files
        )

        # Upload media files
        logger.info("Uploading media files")
        media_ids = {}
        for media_file in article_content.media_files:
            try:
                media_id = wechat_client.upload_media(media_file)
                media_ids[str(media_file)] = media_id
                logger.info(f"Uploaded media: {media_file}")
            except WeChatAPIError as e:
                logger.error(f"Failed to upload media {media_file}: {e}")

        # Upload cover image if exists
        thumb_media_id = None
        if cover_image:
            try:
                thumb_media_id = wechat_client.upload_media(cover_image)
                logger.info(f"Uploaded cover image: {cover_image}")
            except WeChatAPIError as e:
                logger.error(f"Failed to upload cover image {cover_image}: {e}")

        # Prepare WeChat article
        wechat_article = WeChatArticle(
            title=metadata.title,
            content=article_content.html_content,
            author=metadata.author,
            digest=metadata.summary,
            content_source_url=metadata.original_url,
            thumb_media_id=thumb_media_id,
        )

        # Publish article
        logger.info("Publishing article to WeChat")
        result = wechat_client.publish_article(wechat_article)
        logger.info(f"Article published successfully: {result}")

    except Exception as e:
        logger.error(f"Error during publishing process: {e}")
        raise


if __name__ == "__main__":
    main() 