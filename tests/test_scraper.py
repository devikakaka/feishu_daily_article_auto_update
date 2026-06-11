"""Unit tests for the multi-source scraper module."""

import pytest
from unittest.mock import patch, MagicMock

from src.scraper import MultiSourceScraper, Article, BEIJING_TZ
from datetime import datetime


@pytest.fixture
def scraper_config():
    """Create a test scraper config with multi-source setup."""
    return {
        "scraper": {
            "sources": [
                {
                    "name": "Test HTML Source",
                    "type": "html",
                    "url": "https://example.com/articles",
                    "base_url": "https://example.com",
                    "selectors": {
                        "list_items": "ul li",
                        "article_link": "a",
                        "date_selector": "i.gray",
                    },
                    "detail_selectors": {
                        "title": "h1",
                        "content": "div.content",
                    },
                },
            ],
            "request_delay": 0.01,
            "request_timeout": 5,
            "user_agent": "TestBot/1.0",
            "max_content_length": 1000,
        }
    }


@pytest.fixture
def api_scraper_config():
    """Create a test scraper config with API source."""
    return {
        "scraper": {
            "sources": [
                {
                    "name": "Test API Source",
                    "type": "api",
                    "url": "https://api.example.com/search",
                    "params": {"keyword": "test", "page": 1},
                    "api": {
                        "items_path": "data.list",
                        "title_field": "title",
                        "content_field": "post.content",
                        "date_field": "pub_time",
                        "url_field": "url",
                    },
                },
            ],
            "request_delay": 0.01,
            "request_timeout": 5,
            "user_agent": "TestBot/1.0",
            "max_content_length": 1000,
        }
    }


def test_article_dataclass():
    """Test Article dataclass with source_name."""
    article = Article(
        title="Test Title",
        url="https://example.com/test",
        content="Test content",
        source_name="Test Source",
        date="2026-06-11",
    )
    assert article.title == "Test Title"
    assert article.source_name == "Test Source"
    assert article.date == "2026-06-11"


def test_scraper_init(scraper_config):
    """Test MultiSourceScraper initialization."""
    scraper = MultiSourceScraper(scraper_config)
    assert len(scraper.sources) == 1
    assert scraper.sources[0]["name"] == "Test HTML Source"


@patch("src.scraper.requests.Session")
def test_html_source_filters_by_date(mock_session, scraper_config):
    """Test that HTML source only returns today's articles."""
    today = datetime.now(BEIJING_TZ).strftime("%Y-%m-%d")
    yesterday = "2020-01-01"

    # Mock listing page
    listing_resp = MagicMock()
    listing_resp.text = f"""
    <html><body><ul>
        <li><a href="/article/today">Today Article</a><i class="gray">{today}</i></li>
        <li><a href="/article/old">Old Article</a><i class="gray">{yesterday}</i></li>
    </ul></body></html>
    """
    listing_resp.apparent_encoding = "utf-8"
    listing_resp.raise_for_status = MagicMock()

    # Mock detail page
    detail_resp = MagicMock()
    detail_resp.text = """
    <html><body>
        <h1>Today Article Title</h1>
        <div class="content"><p>Content paragraph 1</p><p>Content paragraph 2</p></div>
    </body></html>
    """
    detail_resp.apparent_encoding = "utf-8"
    detail_resp.raise_for_status = MagicMock()

    mock_session_instance = MagicMock()

    def get_side_effect(url, **kwargs):
        if "example.com/articles" in url:
            return listing_resp
        return detail_resp

    mock_session_instance.get.side_effect = get_side_effect
    mock_session.return_value = mock_session_instance

    scraper = MultiSourceScraper(scraper_config)
    articles = scraper.scrape()

    # Only today's article should be returned
    assert len(articles) == 1
    assert "Today Article" in articles[0].title


@patch("src.scraper.requests.Session")
def test_api_source_filters_by_date(mock_session, api_scraper_config):
    """Test that API source only returns today's articles."""
    today = datetime.now(BEIJING_TZ).strftime("%Y-%m-%d")

    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "data": {
            "list": [
                {
                    "title": "Today Article",
                    "pub_time": today,
                    "url": "https://example.com/today",
                    "post": {"content": "Today's content"},
                },
                {
                    "title": "Old Article",
                    "pub_time": "2020-01-01",
                    "url": "https://example.com/old",
                    "post": {"content": "Old content"},
                },
            ]
        }
    }
    mock_resp.raise_for_status = MagicMock()

    mock_session_instance = MagicMock()
    mock_session_instance.post.return_value = mock_resp
    mock_session.return_value = mock_session_instance

    scraper = MultiSourceScraper(api_scraper_config)
    articles = scraper.scrape()

    assert len(articles) == 1
    assert articles[0].title == "Today Article"
    assert articles[0].content == "Today's content"


@patch("src.scraper.requests.Session")
def test_api_source_strips_html_from_title(mock_session, api_scraper_config):
    """Test that HTML tags are stripped from API titles."""
    today = datetime.now(BEIJING_TZ).strftime("%Y-%m-%d")

    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "data": {
            "list": [
                {
                    "title": "<em>南方</em><em>日报</em>评论员：标题",
                    "pub_time": today,
                    "url": "https://example.com/test",
                    "post": {"content": "这是一篇南方日报评论员文章的正文内容，足够长了。"},
                },
            ]
        }
    }
    mock_resp.raise_for_status = MagicMock()

    mock_session_instance = MagicMock()
    mock_session_instance.post.return_value = mock_resp
    mock_session.return_value = mock_session_instance

    scraper = MultiSourceScraper(api_scraper_config)
    articles = scraper.scrape()

    assert len(articles) == 1
    assert articles[0].title == "南方日报评论员：标题"


@patch("src.scraper.requests.Session")
def test_html_source_handles_http_error(mock_session, scraper_config):
    """Test graceful handling of HTTP errors."""
    import requests

    mock_session_instance = MagicMock()
    mock_session_instance.get.side_effect = requests.RequestException("Connection error")
    mock_session.return_value = mock_session_instance

    scraper = MultiSourceScraper(scraper_config)
    articles = scraper.scrape()

    # Should return empty list, not raise
    assert articles == []


@patch("src.scraper.requests.Session")
def test_content_extracts_paragraphs(mock_session, scraper_config):
    """Test that content extraction gets paragraphs and filters empty ones."""
    today = datetime.now(BEIJING_TZ).strftime("%Y-%m-%d")

    listing_resp = MagicMock()
    listing_resp.text = f"""
    <html><body><ul>
        <li><a href="/article/1">Article</a><i class="gray">{today}</i></li>
    </ul></body></html>
    """
    listing_resp.apparent_encoding = "utf-8"
    listing_resp.raise_for_status = MagicMock()

    detail_resp = MagicMock()
    detail_resp.text = """
    <html><body>
        <h1>Test Title</h1>
        <div class="content">
            <p>First paragraph.</p>
            <p></p>
            <p>  </p>
            <p>Second paragraph.</p>
            <script>var x = 1;</script>
            <p>Third paragraph.</p>
        </div>
    </body></html>
    """
    detail_resp.apparent_encoding = "utf-8"
    detail_resp.raise_for_status = MagicMock()

    mock_session_instance = MagicMock()

    def get_side_effect(url, **kwargs):
        if "example.com/articles" in url:
            return listing_resp
        return detail_resp

    mock_session_instance.get.side_effect = get_side_effect
    mock_session.return_value = mock_session_instance

    scraper = MultiSourceScraper(scraper_config)
    articles = scraper.scrape()

    assert len(articles) == 1
    # Should have 3 paragraphs, empty ones filtered, script removed
    content = articles[0].content
    assert "First paragraph" in content
    assert "Second paragraph" in content
    assert "Third paragraph" in content
    assert "var x = 1" not in content