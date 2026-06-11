"""Config loader with ${ENV_VAR} interpolation."""

import os
import re
import yaml
from pathlib import Path


def load_config(path: str) -> dict:
    """
    Load a YAML config file and expand ${VAR} references from environment.

    Args:
        path: Path to the YAML config file

    Returns:
        Parsed config dictionary

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If a required env var is missing
    """
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(
            f"Config file not found: {path}\n"
            f"Hint: copy config/config.example.yaml to config/config.yaml"
        )

    with open(config_path, "r", encoding="utf-8") as f:
        raw = f.read()

    # Expand ${VAR_NAME} from environment variables, skipping YAML comment lines
    def _replace_env(match):
        var_name = match.group(1)
        value = os.environ.get(var_name)
        if value is None:
            raise ValueError(
                f"Environment variable '{var_name}' is not set. "
                f"This variable is required by the config file."
            )
        return value

    lines = []
    for line in raw.split("\n"):
        # Skip comment lines (leading whitespace + #)
        stripped = line.lstrip()
        if stripped.startswith("#"):
            lines.append(line)
        else:
            lines.append(re.sub(r'\$\{(\w+)\}', _replace_env, line))

    expanded = "\n".join(lines)

    config = yaml.safe_load(expanded)
    _validate_config(config)
    return config


def _validate_config(config: dict):
    """Basic sanity checks on the config structure."""
    required_sections = ["scraper", "llm", "feishu", "output"]
    for section in required_sections:
        if section not in config:
            raise ValueError(f"Config missing required section: '{section}'")

    if "sources" not in config["scraper"] or not config["scraper"]["sources"]:
        raise ValueError("config.scraper.sources is required and must not be empty")
    for i, source in enumerate(config["scraper"]["sources"]):
        if "url" not in source:
            raise ValueError(f"config.scraper.sources[{i}].url is required")
        if source.get("type", "html") == "html" and "selectors" not in source:
            raise ValueError(f"config.scraper.sources[{i}].selectors is required for HTML sources")
        if source.get("type") == "api" and "api" not in source:
            raise ValueError(f"config.scraper.sources[{i}].api is required for API sources")

    if "model" not in config["llm"]:
        raise ValueError("config.llm.model is required")
    if "base_url" not in config["llm"]:
        raise ValueError("config.llm.base_url is required")