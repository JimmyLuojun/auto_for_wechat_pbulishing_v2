# tests/core/test_payload_builder.py
import pytest
from src.auto_for_wechat_publishing.core.payload_builder import build_draft_payload

def test_build_payload_minimal():
    """Test payload with minimal required metadata."""
    metadata = {"title": "Test Title"}
    html_content = "<p>Hello</p>"
    thumb_media_id = "thumb123"
    payload = build_draft_payload(metadata, html_content, thumb_media_id)

    assert "articles" in payload
    assert isinstance(payload["articles"], list)
    assert len(payload["articles"]) == 1
    article = payload["articles"][0]

    assert article["title"] == "Test Title"
    assert article["thumb_media_id"] == thumb_media_id
    assert article["content"] == html_content
    assert article["digest"] == "Hello" # Generated from short content
    assert article["author"] == "" # Default
    assert article["content_source_url"] == "" # Default
    assert article["need_open_comment"] == 0 # Default
    assert article["only_fans_can_comment"] == 0 # Default


def test_build_payload_all_fields():
     """Test payload with all optional fields provided."""
     metadata = {
         "title": "Full Article",
         "author": "Test Author",
         "digest": "Custom Summary", # Should use this instead of generating
         "content_source_url": "http://example.com",
         "need_open_comment": 1,
         "only_fans_can_comment": 1,
         # "cover_image_path" is used upstream, not directly in payload
     }
     html_content = "<p>This is the article body.</p>"
     thumb_media_id = "thumb456"
     payload = build_draft_payload(metadata, html_content, thumb_media_id)
     article = payload["articles"][0]

     assert article["title"] == metadata["title"]
     assert article["author"] == metadata["author"]
     assert article["digest"] == metadata["digest"] # Check custom digest is used
     assert article["content_source_url"] == metadata["content_source_url"]
     assert article["need_open_comment"] == metadata["need_open_comment"]
     assert article["only_fans_can_comment"] == metadata["only_fans_can_comment"]
     assert article["thumb_media_id"] == thumb_media_id
     assert article["content"] == html_content


def test_build_payload_digest_generation_html_stripping():
     """Test auto-generated digest strips HTML and truncates."""
     metadata = {"title": "Long Content"}
     # Content where plain text is > 54 chars
     html_content = "<h1>Heading</h1><p>This is <b>bold</b> text and it continues for a very long time, easily exceeding the fifty-four character limit imposed by WeChat for article digests.</p>"
     thumb_media_id = "thumb789"
     payload = build_draft_payload(metadata, html_content, thumb_media_id)
     article = payload["articles"][0]

     # Expected digest is first 54 chars of *plain text*
     expected_digest = "HeadingThis is bold text and it continues for a very lo"[:54]
     assert len(expected_digest) == 54
     assert article["digest"] == expected_digest


def test_build_payload_digest_provided_long_truncates():
     """Test that a provided digest longer than 54 chars is truncated."""
     long_digest = "This is a custom digest that happens to be much longer than the 54 character limit."
     metadata = {"title": "Long Digest Test", "digest": long_digest}
     payload = build_draft_payload(metadata, "<p>Content</p>", "thumb_abc")
     article = payload["articles"][0]
     assert len(article["digest"]) == 54
     assert article["digest"] == long_digest[:54]


def test_build_payload_empty_content_digest():
     """Test digest generation with empty HTML content."""
     metadata = {"title": "Empty Content"}
     payload = build_draft_payload(metadata, "", "thumb_def")
     article = payload["articles"][0]
     assert article["digest"] == ""


def test_build_payload_missing_title_raises_error():
     """Test KeyError is raised if required 'title' is missing."""
     with pytest.raises(KeyError, match="'title'"):
          build_draft_payload({}, "<p></p>", "thumb1")

def test_build_payload_missing_thumb_id_raises_error():
     """Test ValueError is raised if thumb_media_id is empty."""
     with pytest.raises(ValueError, match="thumb_media_id cannot be empty"):
         build_draft_payload({"title": "T"}, "<p></p>", "")