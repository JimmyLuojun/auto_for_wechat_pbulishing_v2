"""WeChat API client for publishing articles."""

import json
import time
from pathlib import Path
from typing import Dict, Any, Optional
import requests

from .wechat_endpoints import WeChatEndpoints
from .wechat_exceptions import WeChatAPIError
from ..content.data_models import WeChatArticle


class WeChatAPIClient:
    """Client for interacting with WeChat Official Account API."""

    def __init__(self, app_id: str, secret: str):
        """Initialize with WeChat app credentials."""
        self.app_id = app_id
        self.secret = secret
        self.access_token = None
        self.token_expiry = 0
        self.endpoints = WeChatEndpoints()

    def _get_access_token(self) -> str:
        """Get or refresh access token."""
        if self.access_token and time.time() < self.token_expiry:
            return self.access_token

        response = requests.get(
            self.endpoints.get_access_token,
            params={"grant_type": "client_credential", "appid": self.app_id, "secret": self.secret},
        )
        data = response.json()

        if "access_token" not in data:
            raise WeChatAPIError(f"Failed to get access token: {data}")

        self.access_token = data["access_token"]
        self.token_expiry = time.time() + data.get("expires_in", 7200) - 300  # 5 minutes buffer
        return self.access_token

    def upload_media(self, file_path: Path, media_type: str = "image") -> str:
        """Upload media file and return media_id."""
        token = self._get_access_token()
        url = self.endpoints.upload_media.format(access_token=token)

        with open(file_path, "rb") as f:
            files = {"media": f}
            response = requests.post(
                url,
                files=files,
                params={"type": media_type},
            )

        data = response.json()
        if "media_id" not in data:
            raise WeChatAPIError(f"Failed to upload media: {data}")

        return data["media_id"]

    def publish_article(self, article: WeChatArticle) -> Dict[str, Any]:
        """Publish article to WeChat."""
        token = self._get_access_token()
        url = self.endpoints.publish_article.format(access_token=token)

        # Prepare article data
        article_data = {
            "articles": [
                {
                    "title": article.title,
                    "thumb_media_id": article.thumb_media_id,
                    "author": article.author,
                    "digest": article.digest,
                    "content": article.content,
                    "content_source_url": article.content_source_url,
                    "need_open_comment": 1 if article.need_open_comment else 0,
                    "only_fans_can_comment": 1 if article.only_fans_can_comment else 0,
                }
            ]
        }

        response = requests.post(url, json=article_data)
        data = response.json()

        if data.get("errcode") != 0:
            raise WeChatAPIError(f"Failed to publish article: {data}")

        return data 