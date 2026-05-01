"""
scraper.py — Scrapes HackerRank, Claude, and Visa support sites.
Run this ONCE before building the corpus:  python scraper.py

Saves scraped docs as .txt files in data/corpus/
"""

import os
import time
import requests
from bs4 import BeautifulSoup

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "corpus")
os.makedirs(OUTPUT_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; SupportAgent/1.0)"
}

# ─── SOURCES ────────────────────────────────────────────────────────────────

SOURCES = {
    "hackerrank": {
        "base_url": "https://support.hackerrank.com",
        "start_urls": [
            "https://support.hackerrank.com/hc/en-us",
        ]
    },
    "claude": {
        "base_url": "https://support.claude.com",
        "start_urls": [
            "https://support.claude.com/en/",
        ]
    },
    "visa": {
        "base_url": "https://www.visa.co.in",
        "start_urls": [
            "https://www.visa.co.in/support.html",
        ]
    }
}

def get_links(url, base_url):
    """Extract all article/support links from a page."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        links = set()
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith("/"):
                href = base_url + href
            if base_url in href and href != url:
                links.add(href)
        return links
    except Exception as e:
        print(f"  [!] Failed to get links from {url}: {e}")
        return set()

def scrape_page(url):
    """Scrape text content from a single support page."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")

        # Remove nav, footer, scripts
        for tag in soup(["nav", "footer", "script", "style", "header"]):
            tag.decompose()

        # Try to get article body
        article = (
            soup.find("article") or
            soup.find(class_="article-body") or
            soup.find(class_="content") or
            soup.find("main") or
            soup.find("body")
        )

        title = soup.find("h1")
        title_text = title.get_text(strip=True) if title else "Untitled"
        body_text = article.get_text(separator="\n", strip=True) if article else ""

        if len(body_text) < 100:
            return None  # Skip thin pages

        return f"TITLE: {title_text}\nURL: {url}\n\n{body_text}"

    except Exception as e:
        print(f"  [!] Failed to scrape {url}: {e}")
        return None

def scrape_source(name, config):
    """Scrape all pages for one source."""
    print(f"\n[→] Scraping {name}...")
    base_url = config["base_url"]
    visited = set()
    to_visit = set(config["start_urls"])
    docs = []

    # BFS crawl — limit to 100 pages per source to stay reasonable
    while to_visit and len(visited) < 100:
        url = to_visit.pop()
        if url in visited:
            continue
        visited.add(url)

        print(f"  Scraping: {url}")
        content = scrape_page(url)
        if content:
            docs.append((url, content))

        # Get more links from this page
        new_links = get_links(url, base_url)
        to_visit.update(new_links - visited)

        time.sleep(0.3)  # Be polite to servers

    # Save all docs for this source
    source_dir = os.path.join(OUTPUT_DIR, name)
    os.makedirs(source_dir, exist_ok=True)

    for i, (url, content) in enumerate(docs):
        filename = f"doc_{i:04d}.txt"
        with open(os.path.join(source_dir, filename), "w", encoding="utf-8") as f:
            f.write(content)

    print(f"  [✓] Saved {len(docs)} docs for {name}")
    return len(docs)

def main():
    print("=" * 50)
    print("Support Corpus Scraper")
    print("=" * 50)
    total = 0
    for name, config in SOURCES.items():
        count = scrape_source(name, config)
        total += count
    print(f"\n[✓] Done. Total docs scraped: {total}")
    print(f"[✓] Corpus saved to: {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
