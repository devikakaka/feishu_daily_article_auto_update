"""Unit tests for llm_analyzer module."""

import pytest
from unittest.mock import patch, MagicMock

from src.llm_analyzer import LLMAnalyzer
from src.scraper import Article


@pytest.fixture
def analyzer_config():
    """Create a test analyzer config."""
    return {
        "llm": {
            "api_key": "test-api-key",
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "model": "qwen-plus",
            "system_prompt": "You are a content analyst.",
            "user_prompt_template": "Source: {article_source}\nAnalyze: {article_title}\nURL: {article_url}\n{article_content}",
            "batch_size": 2,
            "temperature": 0.3,
            "max_tokens": 1000,
            "max_content_length": 100,
        }
    }


@pytest.fixture
def sample_articles():
    """Create sample articles for testing."""
    return [
        Article(
            title="Article 1",
            url="https://example.com/1",
            content="Content of article 1",
        ),
        Article(
            title="Article 2",
            url="https://example.com/2",
            content="Content of article 2",
        ),
        Article(
            title="Article 3",
            url="https://example.com/3",
            content="Content of article 3",
        ),
    ]


@patch("src.llm_analyzer.OpenAI")
def test_analyzer_init(mock_openai, analyzer_config):
    """Test LLMAnalyzer initialization."""
    analyzer = LLMAnalyzer(analyzer_config)
    assert analyzer.model == "qwen-plus"
    assert analyzer.batch_size == 2
    assert analyzer.max_content_length == 100


@patch("src.llm_analyzer.OpenAI")
def test_analyze_single_batch(mock_openai, analyzer_config, sample_articles):
    """Test analyzing articles in a single batch."""
    # Mock the OpenAI client
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Analysis result"
    mock_response.usage.prompt_tokens = 100
    mock_response.usage.completion_tokens = 50
    mock_response.usage.total_tokens = 150
    mock_client.chat.completions.create.return_value = mock_response
    mock_openai.return_value = mock_client

    analyzer = LLMAnalyzer(analyzer_config)
    # Only take 2 articles (one batch)
    result = analyzer.analyze(sample_articles[:2])

    assert "Analysis result" in result
    mock_client.chat.completions.create.assert_called_once()


@patch("src.llm_analyzer.OpenAI")
def test_analyze_multiple_batches(mock_openai, analyzer_config, sample_articles):
    """Test analyzing articles in multiple batches."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Batch analysis"
    mock_response.usage.prompt_tokens = 100
    mock_response.usage.completion_tokens = 50
    mock_response.usage.total_tokens = 150
    mock_client.chat.completions.create.return_value = mock_response
    mock_openai.return_value = mock_client

    analyzer = LLMAnalyzer(analyzer_config)
    result = analyzer.analyze(sample_articles)

    # 3 articles with batch_size=2 → 2 batches
    assert mock_client.chat.completions.create.call_count == 2


@patch("src.llm_analyzer.OpenAI")
def test_build_user_prompt(mock_openai, analyzer_config, sample_articles):
    """Test building user prompt from articles."""
    mock_client = MagicMock()
    mock_openai.return_value = mock_client

    analyzer = LLMAnalyzer(analyzer_config)
    prompt = analyzer._build_user_prompt(sample_articles[:2])

    assert "Article 1" in prompt
    assert "Article 2" in prompt
    assert "https://example.com/1" in prompt


@patch("src.llm_analyzer.OpenAI")
def test_content_truncation(mock_openai, analyzer_config):
    """Test that long content is truncated."""
    mock_client = MagicMock()
    mock_openai.return_value = mock_client

    analyzer = LLMAnalyzer(analyzer_config)
    long_article = Article(
        title="Long Article",
        url="https://example.com/long",
        content="x" * 200,  # 200 chars, max is 100
    )
    prompt = analyzer._build_user_prompt([long_article])

    # Content (200 chars) should be truncated to max_content_length (100)
    # The prompt includes title + URL + truncated content
    assert "x" * 100 in prompt
    assert "x" * 101 not in prompt


@patch("src.llm_analyzer.OpenAI")
def test_analyze_batch_retry(mock_openai, analyzer_config, sample_articles):
    """Test that failed batch is retried."""
    mock_client = MagicMock()
    # First call fails, second succeeds
    mock_client.chat.completions.create.side_effect = [
        Exception("API error"),
        MagicMock(
            choices=[MagicMock(message=MagicMock(content="Retry success"))],
            usage=MagicMock(prompt_tokens=100, completion_tokens=50, total_tokens=150),
        ),
    ]
    mock_openai.return_value = mock_client

    analyzer = LLMAnalyzer(analyzer_config)
    result = analyzer._analyze_batch_with_retry(sample_articles[:1])

    assert "Retry success" in result
    assert mock_client.chat.completions.create.call_count == 2