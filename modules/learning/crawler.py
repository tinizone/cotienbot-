import feedparser

def crawl_rss(url: str):
    feed = feedparser.parse(url)
    return [
        {"title": entry.title, "link": entry.link, "summary": entry.summary}
        for entry in feed.entries
    ]
