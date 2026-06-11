"""Unit tests for config_loader module."""

import os
import tempfile
from pathlib import Path

import pytest

from src.config_loader import load_config

# Common valid config snippet using sources array
VALID_SCRAPER_YAML = """
scraper:
  sources:
    - name: "Test Source"
      type: "html"
      url: "https://example.com"
      selectors:
        list_items: "ul li"
        article_link: "a"
        date_selector: "i.gray"
      detail_selectors:
        title: "h1"
        content: "div.content"
"""

VALID_LLM_YAML = """
llm:
  model: "qwen-plus"
  base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
  api_key: "test-key"
"""

VALID_FEISHU_YAML = """
feishu:
  app_id: "test-id"
  app_secret: "test-secret"
"""

VALID_OUTPUT_YAML = """
output:
  readme_path: "README.md"
"""


def test_load_config_success():
    """Test loading a valid config file."""
    config_content = VALID_SCRAPER_YAML + VALID_LLM_YAML + VALID_FEISHU_YAML + VALID_OUTPUT_YAML
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(config_content)
        f.flush()
        config = load_config(f.name)

    assert len(config["scraper"]["sources"]) == 1
    assert config["scraper"]["sources"][0]["name"] == "Test Source"
    assert config["llm"]["model"] == "qwen-plus"
    os.unlink(f.name)


def test_load_config_env_var_expansion():
    """Test that ${ENV_VAR} is expanded from environment."""
    config_content = VALID_SCRAPER_YAML + """
llm:
  model: "qwen-plus"
  base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
  api_key: "${TEST_API_KEY}"
feishu:
  app_id: "${TEST_APP_ID}"
  app_secret: "${TEST_APP_SECRET}"
""" + VALID_OUTPUT_YAML

    os.environ["TEST_API_KEY"] = "test-api-key-123"
    os.environ["TEST_APP_ID"] = "test-app-id-456"
    os.environ["TEST_APP_SECRET"] = "test-secret-789"

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(config_content)
        f.flush()
        config = load_config(f.name)

    assert config["llm"]["api_key"] == "test-api-key-123"
    assert config["feishu"]["app_id"] == "test-app-id-456"
    assert config["feishu"]["app_secret"] == "test-secret-789"
    os.unlink(f.name)


def test_load_config_missing_env_var():
    """Test that missing env var raises ValueError."""
    config_content = VALID_SCRAPER_YAML + """
llm:
  model: "qwen-plus"
  base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
  api_key: "${MISSING_VAR}"
feishu:
  app_id: "test"
  app_secret: "test"
""" + VALID_OUTPUT_YAML

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(config_content)
        f.flush()
        with pytest.raises(ValueError, match="MISSING_VAR"):
            load_config(f.name)
    os.unlink(f.name)


def test_load_config_missing_file():
    """Test that missing file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_config("/nonexistent/config.yaml")


def test_validate_config_missing_section():
    """Test that missing required section raises ValueError."""
    config_content = VALID_SCRAPER_YAML + VALID_LLM_YAML
    # Missing feishu and output sections
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(config_content)
        f.flush()
        with pytest.raises(ValueError, match="missing required section"):
            load_config(f.name)
    os.unlink(f.name)


def test_validate_config_missing_sources():
    """Test that empty sources list raises ValueError."""
    config_content = """
scraper:
  sources: []
""" + VALID_LLM_YAML + VALID_FEISHU_YAML + VALID_OUTPUT_YAML

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(config_content)
        f.flush()
        with pytest.raises(ValueError, match="sources"):
            load_config(f.name)
    os.unlink(f.name)


def test_validate_config_api_source_needs_api_config():
    """Test that API source without api config raises ValueError."""
    config_content = """
scraper:
  sources:
    - name: "Test API"
      type: "api"
      url: "https://api.example.com"
""" + VALID_LLM_YAML + VALID_FEISHU_YAML + VALID_OUTPUT_YAML

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(config_content)
        f.flush()
        with pytest.raises(ValueError, match="api"):
            load_config(f.name)
    os.unlink(f.name)