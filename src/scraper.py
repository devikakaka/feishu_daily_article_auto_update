"""Multi-source web scraper supporting both static HTML pages and JSON APIs."""

import html
import time
import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict

import requests
from bs4 import BeautifulSoup


# Beijing timezone (UTC+8)
BEIJING_TZ = timezone(timedelta(hours=8))


@dataclass
class Article:
    """Represents a scraped article."""
    title: str
    url: str
    content: str                # Plain text, cleaned
    source_name: str = ""       # Name of the source (e.g. "人民时评")
    content_html: str = ""      # Original HTML snippet
    date: Optional[str] = None
    scraped_at: datetime = field(default_factory=datetime.now)


class MultiSourceScraper:
    """
    Scrapes articles from multiple sources (HTML pages and JSON APIs).
    Filters articles by today's date (Beijing time).
    """

    def __init__(self, config: dict):
        self.cfg = config["scraper"]
        self.sources = self.cfg.get("sources", [])
        self.request_delay = self.cfg.get("request_delay", 2.0)
        self.request_timeout = self.cfg.get("request_timeout", 30)
        self.max_content_length = self.cfg.get("max_content_length", 50000)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": self.cfg.get(
                "user_agent",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            ),
        })

    def scrape(self) -> List[Article]:
        """Main entry: scrape all sources and return today's articles."""
        today = datetime.now(BEIJING_TZ).strftime("%Y-%m-%d")
        print(f"  Target date: {today}")

        all_articles = []
        for source in self.sources:
            source_name = source.get("name", "Unknown")
            source_type = source.get("type", "html")
            print(f"\n  === Source: {source_name} (type: {source_type}) ===")
            try:
                if source_type == "html":
                    articles = self._scrape_html_source(source)
                elif source_type == "api":
                    articles = self._scrape_api_source(source)
                else:
                    print(f"  Unknown source type: {source_type}")
                    continue
                all_articles.extend(articles)
            except Exception as e:
                print(f"  Warning: failed to scrape source {source_name}: {e}")

        print(f"\n  Total articles found for {today}: {len(all_articles)}")
        return all_articles

    # ── HTML Source ─────────────────────────────────────────────────

    def _scrape_html_source(self, source: dict) -> List[Article]:
        """Scrape articles from a static HTML listing page."""
        url = source["url"]
        base_url = source.get("base_url", url)
        selectors = source["selectors"]
        today = datetime.now(BEIJING_TZ).strftime("%Y-%m-%d")

        # Step 1: Fetch listing page
        soup = self._fetch_page(url)
        if not soup:
            return []

        # Step 2: Parse list items
        list_selector = selectors["list_items"]
        items = soup.select(list_selector)
        print(f"  Found {len(items)} items on listing page")

        articles = []
        for item in items:
            # Extract link
            a_tag = item.select_one(selectors.get("article_link", "a"))
            if not a_tag or not a_tag.get("href"):
                continue

            href = a_tag.get("href")
            article_url = urllib.parse.urljoin(base_url, href)
            title = a_tag.get_text(strip=True)

            # Extract date
            date_text = ""
            date_sel = selectors.get("date_selector")
            if date_sel:
                date_tag = item.select_one(date_sel)
                if date_tag:
                    date_text = date_tag.get_text(strip=True)

            # Filter: only today's articles
            # Handle both "2026-06-11" and "2026-06-11 09:33" formats
            if date_text and not date_text.startswith(today):
                continue

            if not date_text:
                # If no date selector, check URL for date pattern /YYYY/MMDD/
                if today.replace("-", "")[:8] not in article_url:
                    continue

            print(f"  Today's article: {title}")

            # Fetch detail page
            time.sleep(self.request_delay)
            article = self._scrape_article_detail(
                article_url, source.get("detail_selectors"),
                source.get("name", ""), title, date_text,
            )
            if article:
                articles.append(article)

        return articles

    def _scrape_article_detail(
        self, url: str, detail_selectors: Optional[dict],
        source_name: str, fallback_title: str, date: str,
    ) -> Optional[Article]:
        """Fetch and parse an article detail page."""
        soup = self._fetch_page(url)
        if not soup:
            return None

        if not detail_selectors:
            detail_selectors = {}

        # Extract title
        title_sel = detail_selectors.get("title", "h1")
        title_tag = soup.select_one(title_sel)
        title = title_tag.get_text(strip=True) if title_tag else fallback_title

        # Extract content
        content_sel = detail_selectors.get("content", "article")
        content_tag = soup.select_one(content_sel)
        if not content_tag:
            print(f"  Warning: content selector not found for {url}")
            return None

        # Remove script/style tags from content
        for tag in content_tag.select("script, style, noscript"):
            tag.decompose()

        # Get paragraphs, filter empty
        paragraphs = content_tag.select("p")
        if paragraphs:
            lines = []
            for p in paragraphs:
                # Skip empty paragraphs and image-only paragraphs
                text = p.get_text(strip=True)
                if text and len(text) > 2:
                    lines.append(text)
            content = "\n\n".join(lines)
        else:
            content = content_tag.get_text(separator="\n", strip=True)

        # Truncate if too long
        if len(content) > self.max_content_length:
            content = content[:self.max_content_length] + "\n... [truncated]"

        return Article(
            title=title,
            url=url,
            content=content,
            source_name=source_name,
            content_html=str(content_tag),
            date=date,
        )

    # ── API Source ──────────────────────────────────────────────────

    def _scrape_api_source(self, source: dict) -> List[Article]:
        """Scrape articles from a JSON API endpoint."""
        url = source["url"]
        params = source.get("params", {})
        api_config = source["api"]
        method = source.get("method", "post").upper()  # Default to POST
        today = datetime.now(BEIJING_TZ).strftime("%Y-%m-%d")

        print(f"  Fetching API ({method}): {url}")
        try:
            if method == "GET":
                resp = self.session.get(
                    url, params=params, timeout=self.request_timeout,
                )
            else:
                resp = self.session.post(
                    url, data=params, timeout=self.request_timeout,
                )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"  Warning: API request failed: {e}")
            return []

        # Navigate to the items list using dot-separated path
        items = data
        for key in api_config["items_path"].split("."):
            if key.isdigit():
                items = items[int(key)]
            else:
                items = items.get(key, [])
            if items is None:
                break

        if not items:
            print("  No items found in API response")
            return []

        print(f"  Found {len(items)} items in API response")

        # Filter by today's date
        date_field = api_config["date_field"]
        title_filter = api_config.get("title_filter", "")  # Optional: must appear in title
        today_items = [
            item for item in items
            if item.get(date_field, "").startswith(today)
        ]
        print(f"  {len(today_items)} items match today's date ({today})")

        articles = []
        for item in today_items:
            # Title may contain HTML tags (<em> for search highlighting)
            raw_title = item.get(api_config["title_field"], "")
            title = BeautifulSoup(raw_title, "lxml").get_text()

            # Apply title filter if configured
            if title_filter and title_filter not in title:
                print(f"  Skipped (title filter): {title[:40]}")
                continue

            # Content: check for nested field (e.g. "post.content")
            content_field = api_config.get("content_field", "content")
            content = item
            for key in content_field.split("."):
                content = content.get(key, "") if isinstance(content, dict) else ""
            content = html.unescape(content) if content else ""

            # Skip articles with no content
            if not content or len(content.strip()) < 10:
                print(f"  Skipped (no content): {title[:40]}")
                continue

            # URL
            article_url = item.get(api_config.get("url_field", "url"), "")

            # Truncate if too long
            if len(content) > self.max_content_length:
                content = content[:self.max_content_length] + "\n... [truncated]"

            article = Article(
                title=title,
                url=article_url,
                content=content,
                source_name=source.get("name", ""),
                date=item.get(date_field, ""),
            )
            articles.append(article)
            print(f"  Today's article: {title}")

        return articles

    # ── Helpers ─────────────────────────────────────────────────────

    def _fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch a URL and return a BeautifulSoup object, or None on error."""
        try:
            resp = self.session.get(url, timeout=self.request_timeout)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding
            return BeautifulSoup(resp.text, "lxml")
        except requests.RequestException as e:
            print(f"  Warning: HTTP error for {url}: {e}")
            return None