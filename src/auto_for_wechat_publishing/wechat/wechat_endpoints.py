"""WeChat API endpoints."""

class WeChatEndpoints:
    """Stores WeChat API endpoint URLs."""

    def __init__(self, base_url: str = "https://api.weixin.qq.com/cgi-bin"):
        """Initialize with base URL."""
        self.base_url = base_url

    @property
    def get_access_token(self) -> str:
        """Get access token endpoint."""
        return f"{self.base_url}/token"

    @property
    def upload_media(self) -> str:
        """Upload media endpoint."""
        return f"{self.base_url}/media/upload?access_token={{access_token}}"

    @property
    def publish_article(self) -> str:
        """Publish article endpoint."""
        return f"{self.base_url}/draft/add?access_token={{access_token}}"

    @property
    def get_article(self) -> str:
        """Get article endpoint."""
        return f"{self.base_url}/draft/get?access_token={{access_token}}"

    @property
    def delete_article(self) -> str:
        """Delete article endpoint."""
        return f"{self.base_url}/draft/delete?access_token={{access_token}}"

    @property
    def update_article(self) -> str:
        """Update article endpoint."""
        return f"{self.base_url}/draft/update?access_token={{access_token}}" 