# UPDATE: /modules/learning/crawler.py
import feedparser
from urllib.parse import urlparse
import re
from database.firestore import FirestoreClient
from google.cloud import firestore
from google.cloud.exceptions import GoogleCloudError
import logging
import html

logger = logging.getLogger(__name__)

def crawl_rss(url: str, db: FirestoreClient = None) -> dict | list:
    """Crawl an RSS feed and store entries in Firestore."""
    db = db or FirestoreClient()
    try:
        # Validate URL
        parsed = urlparse(url)
        if not parsed.scheme in ["http", "https"] or not parsed.netloc or not re.match(r"^[\w\-\.]+$", parsed.netloc):
            raise ValueError("Invalid URL")
        feed = feedparser.parse(url)
        if feed.bozo:
            raise ValueError(f"Error parsing RSS: {feed.bozo_exception}")
        entries = []
        for entry in feed.entries[:10]:  # Limit to 10 entries
            entry_data = {
                "title": html.escape(entry.get("title", "No title")),  # Sanitize
                "link": html.escape(entry.get("link", "")),  # Sanitize
                "summary": html.escape(entry.get("summary", "")),  # Sanitize
                "crawled_at": firestore.SERVER_TIMESTAMP
            }
            db.client.collection("rss_feeds").document().set(entry_data)
            entries.append(entry_data)
        logger.info(f"Crawled {len(entries)} entries from {url}")
        return entries
    except GoogleCloudError as e:
        logger.error(f"Firestore error crawling RSS {url}: {str(e)}")
        return {"error": str(e)}
    except ValueError as e:
        logger.error(f"Validation error crawling RSS {url}: {str(e)}")
        return {"error": str(e)}
    except Exception as e:
        logger.error(f"Unexpected error crawling RSS {url}: {str(e)}")
        return {"error": str(e)}
