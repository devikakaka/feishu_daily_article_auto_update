#!/usr/bin/env python3
"""Main entry point: scrape -> analyze -> publish pipeline."""

import argparse
import sys
from datetime import datetime
from pathlib import Path

from src.config_loader import load_config
from src.scraper import MultiSourceScraper
from src.llm_analyzer import LLMAnalyzer
from src.feishu_uploader import FeishuUploader
from src.readme_generator import ReadmeGenerator


def main():
    parser = argparse.ArgumentParser(
        description="Article Scraper + Qwen Analyzer + Feishu Publisher"
    )
    parser.add_argument("--config", default="config/config.yaml", help="Path to config file")
    parser.add_argument("--skip-feishu", action="store_true", help="Skip Feishu upload even if configured")
    parser.add_argument("--dry-run", action="store_true", help="Scrape only, don't analyze or upload")
    args = parser.parse_args()

    # ── Step 1: Load configuration ──────────────────────────────────
    print("📋 Loading configuration...")
    config = load_config(args.config)
    sources = config["scraper"].get("sources", [])
    print(f"   Sources: {len(sources)}")
    for s in sources:
        print(f"     - {s.get('name', 'Unknown')} ({s.get('type', 'html')})")
    print(f"   LLM model: {config['llm']['model']}")

    # ── Step 2: Scrape articles ─────────────────────────────────────
    print("\n🕷️  Scraping articles...")
    scraper = MultiSourceScraper(config)
    articles = scraper.scrape()
    print(f"   Found {len(articles)} articles")

    if not articles:
        print("⚠️  No articles found. Exiting gracefully.")
        sys.exit(0)

    # ── Step 3: Save raw articles (optional) ────────────────────────
    if config["output"].get("save_raw_articles"):
        _save_raw_articles(articles, config)

    if args.dry_run:
        print("\n🏁 Dry run complete. Skipping analysis and upload.")
        return

    # ── Step 4: Analyze with Qwen LLM ───────────────────────────────
    print("\n🤖 Analyzing articles with Qwen...")
    analyzer = LLMAnalyzer(config)
    analysis_markdown = analyzer.analyze(articles)

    # ── Step 5: Save analysis output ────────────────────────────────
    if config["output"].get("save_analysis"):
        analysis_path = Path(config["output"]["analysis_file"])
        analysis_path.parent.mkdir(parents=True, exist_ok=True)
        header = f"# 文章分析 - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        analysis_path.write_text(header + analysis_markdown, encoding="utf-8")
        print(f"   Saved to {analysis_path}")

    # ── Step 6: Upload to Feishu Wiki ───────────────────────────────
    feishu_url = None
    feishu_enabled = (
        not args.skip_feishu
        and config["feishu"].get("upload_enabled", False)
        and config["feishu"].get("wiki_space_id")
    )
    if feishu_enabled:
        print("\n📤 Uploading to Feishu Wiki...")
        try:
            date_str = datetime.now().strftime("%Y-%m-%d")
            title = config["feishu"]["node_title_template"].format(date=date_str)
            uploader = FeishuUploader(config)
            feishu_url = uploader.upload(title, analysis_markdown)
            print(f"   ✅ Uploaded: {feishu_url}")
        except Exception as e:
            print(f"   ⚠️  Feishu upload failed: {e}")
            # Non-fatal — continue to update README
    else:
        print("\n⏭️  Skipping Feishu upload (disabled or not configured)")

    # ── Step 7: Update README.md ────────────────────────────────────
    print("\n📝 Updating README.md...")
    readme_gen = ReadmeGenerator(config)
    readme_gen.generate(articles, analysis_markdown, feishu_url)

    print("\n🎉 Pipeline complete!")


def _save_raw_articles(articles, config):
    """Save each article as a plain text file for reference."""
    articles_dir = Path(config["output"]["raw_articles_dir"])
    articles_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    for i, article in enumerate(articles):
        safe_title = "".join(c if c.isalnum() or c in " _-" else "_" for c in article.title)[:60].strip()
        filename = f"{date_str}_{i:02d}_{safe_title}.txt"
        path = articles_dir / filename
        path.write_text(
            f"Title:  {article.title}\n"
            f"Source: {article.source_name or 'N/A'}\n"
            f"URL:    {article.url}\n"
            f"Date:   {article.date or 'N/A'}\n"
            f"Scraped: {article.scraped_at.isoformat()}\n"
            f"\n{'='*60}\n\n"
            f"{article.content}\n",
            encoding="utf-8",
        )
    print(f"   Saved {len(articles)} raw articles to {articles_dir}")


if __name__ == "__main__":
    main()