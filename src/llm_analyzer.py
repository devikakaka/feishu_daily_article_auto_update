"""LLM analyzer module using Qwen via DashScope (OpenAI-compatible API)."""

import time
from typing import List

from openai import OpenAI

from src.scraper import Article


class LLMAnalyzer:
    """Analyzes articles using Qwen LLM via DashScope OpenAI-compatible endpoint."""

    def __init__(self, config: dict):
        self.cfg = config["llm"]
        self.client = OpenAI(
            api_key=self.cfg["api_key"],
            base_url=self.cfg["base_url"],
        )
        self.model = self.cfg["model"]
        self.system_prompt = self.cfg["system_prompt"]
        self.batch_size = self.cfg.get("batch_size", 3)
        self.temperature = self.cfg.get("temperature", 0.3)
        self.max_tokens = self.cfg.get("max_tokens", 4000)
        self.max_content_length = self.cfg.get("max_content_length", 8000)

    def analyze(self, articles: List[Article]) -> str:
        """Analyze all articles in batches, return combined markdown."""
        batches = [
            articles[i:i + self.batch_size]
            for i in range(0, len(articles), self.batch_size)
        ]
        all_analyses = []
        for i, batch in enumerate(batches):
            print(f"  Analyzing batch {i + 1}/{len(batches)} ({len(batch)} articles)...")
            analysis = self._analyze_batch_with_retry(batch)
            if analysis:
                all_analyses.append(analysis)
        return "\n\n".join(all_analyses)

    def _analyze_batch_with_retry(self, articles: List[Article], max_retries: int = 3) -> str:
        """Call LLM with exponential backoff retry."""
        for attempt in range(max_retries):
            try:
                return self._analyze_batch(articles)
            except Exception as e:
                wait = 2 ** (attempt + 1)
                print(f"    Attempt {attempt + 1} failed: {e}. Retrying in {wait}s...")
                time.sleep(wait)
        print(f"    ERROR: All {max_retries} attempts failed for batch")
        return "[Analysis failed for this batch]"

    def _analyze_batch(self, articles: List[Article]) -> str:
        """Send a batch of articles to the LLM and return the analysis."""
        user_content = self._build_user_prompt(articles)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

        usage = response.usage
        if usage:
            print(f"    Tokens: prompt={usage.prompt_tokens}, "
                  f"completion={usage.completion_tokens}, total={usage.total_tokens}")
        return response.choices[0].message.content

    def _build_user_prompt(self, articles: List[Article]) -> str:
        """Build the user prompt from a batch of articles."""
        template = self.cfg.get("user_prompt_template", "")
        parts = []
        for article in articles:
            content = article.content[:self.max_content_length]
            prompt = template.format(
                article_title=article.title,
                article_url=article.url,
                article_content=content,
                article_source=article.source_name or "Unknown",
            )
            parts.append(prompt)
        return "\n\n---\n\n".join(parts)