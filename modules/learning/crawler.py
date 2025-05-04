# File: /modules/learning/crawler.py
import feedparser
from urllib.parse import urlparse
from database.firestore import FirestoreClient
from google.cloud import firestore
import logging

logger = logging.getLogger(__name__)
db = FirestoreClient()

def crawl_rss(url: str):
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError("Invalid URL")
        feed = feedparser.parse(url)
        if feed.bozo:
            raise ValueError(f"Error parsing RSS: {feed.bozo_exception}")
        entries = []
        for entry in feed.entries[:10]:  # Giới hạn 10 bài
            entry_data = {
                "title": entry.get("title", "No title"),
                "link": entry.get("link", ""),
                "summary": entry.get("summary", ""),
                "crawled_at": firestore.SERVER_TIMESTAMP
            }
            db.client.collection("rss_feeds").document().set(entry_data)
            entries.append(entry_data)
        logger.info(f"Crawled {len(entries)} entries from {url}")
        return entries
    except Exception as e:
        logger.error(f"Error crawling RSS: {str(e)}")
        return {"error": str(e)}
