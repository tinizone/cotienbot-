# File: /modules/learning/crawler.py
import feedparser
from urllib.parse import urlparse

def crawl_rss(url: str):
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError("Invalid URL")
        feed = feedparser.parse(url)
        if feed.bozo:
            raise ValueError(f"Error parsing RSS: {feed.bozo_exception}")
        return [
            {
                "title": entry.get("title", "No title"),
                "link": entry.get("link", ""),
                "summary": entry.get("summary", "")
            }
            for entry in feed.entries
        ]
    except Exception as e:
        return {"error": str(e)}
