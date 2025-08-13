
import requests
import json
import os
import time
import logging
from logging.handlers import RotatingFileHandler
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from urllib.parse import urljoin
from datetime import datetime
import traceback
from bs4 import BeautifulSoup
from pathlib import Path


# --------------------- Config --------------------- #

# E:\New_News_Rag_App_V2\daily_news_pipeline\news_scrapers\news_articles_data\news_articles_scrap_data.json
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(
    BASE_DIR,
    "news_articles_data",
    "news_articles_scrap_data.json"
)

LOG_FILE = "log/scraper.log"
DELAY = 1  # Seconds

SECTIONS = {
    "news": {"url_template": "https://allhiphop.com/news/page/{}/"},
    "rumors": {"url_template": "https://allhiphop.com/rumors/page/{}/"},
    "features": {"url_template": "https://allhiphop.com/features/page/{}/"},
    "music": {"url_template": "https://allhiphop.com/music/page/{}/"},
    "opinion": {"url_template": "https://allhiphop.com/opinion/page/{}/"},
    "exclusives": {"url_template": "https://allhiphop.com/exclusives/page/{}/"}
}

# --------------------- Logging Setup --------------------- #

log_dir = os.path.dirname(LOG_FILE)
if log_dir:
    os.makedirs(log_dir, exist_ok=True)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = RotatingFileHandler(LOG_FILE, maxBytes=1024 * 1024, backupCount=5, encoding='utf-8')
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# --------------------- Helpers --------------------- #

def format_pub_date(raw_date):
    """Formats the publication date string."""
    try:
        if not raw_date:
            return "Unknown"
        dt = datetime.strptime(raw_date, "%B %d, %Y")
        return dt.strftime("%d-%m-%Y")
    except Exception as e:
        logger.warning(f" Could not parse date: {raw_date}")
        return "Unknown"

@retry(
    wait=wait_exponential(multiplier=1, min=1, max=10),
    stop=stop_after_attempt(1),
    retry=retry_if_exception_type((requests.exceptions.Timeout, requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout))
)

def extract_article_data(href):
    """Extracts article data from a given URL."""
    try:
        res = requests.get(href, timeout=30)
        res.raise_for_status()
        soup = BeautifulSoup(res.content, "html.parser")

        title_tag = soup.find("h1", class_="entry-title")
        title = title_tag.text.strip() if title_tag else "Unknown"

        content_div = soup.find("div", class_="entry-content")
        description = "\n".join(p.get_text(strip=True) for p in content_div.find_all("p")) if content_div else ""

        date_tag = soup.find(class_="entry-date published") or soup.find(class_="entry-date published updated")
        raw_date = date_tag.get_text(strip=True) if date_tag else None
        pub_date = format_pub_date(raw_date)

        author_tag = soup.find("span", class_="author vcard")
        author = author_tag.get_text(strip=True) if author_tag else "Unknown"

        return {
            "source_url": href,
            "title": title,
            "description": description,
            "author": author,
            "publication_date": pub_date
        }

    except Exception as e:
        logger.error(f" Error extracting article {href}: {e}\n{traceback.format_exc()}")
        return None



def save_new_results(new_articles, filename: Path):
    """Appends only new articles to the existing JSON file."""
    if not new_articles:
        logger.info(" No new articles to save.")
        return

    try:
        # Ensure parent directory exists
        filename.parent.mkdir(parents=True, exist_ok=True)

        # Load existing data
        if filename.exists():
            with filename.open("r", encoding="utf-8") as f:
                existing = json.load(f)
        else:
            existing = []

        # Append new articles
        updated = existing + new_articles
        with filename.open("w", encoding="utf-8") as f:
            json.dump(updated, f, ensure_ascii=False, indent=2)
        
        logger.info(f" Appended {len(new_articles)} new articles to {filename}")

    except Exception as e:
        logger.error(f" Error saving results: {e}\n{traceback.format_exc()}")



# --------------------- Section Scraper --------------------- #

def scrape_section(section_name, url_template, processed_urls, max_articles=15):
    new_articles = []
    added_count = 0
    page = 1  # Only page 1
    page_url = url_template.format(page)
    logger.info(f" Scraping {section_name} page: {page_url}")

    try:
        res = requests.get(page_url, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.content, "html.parser")
        h2_tags = soup.find_all("h2")[:max_articles]  # First 15 articles only

        for h2 in h2_tags:
            a = h2.find("a")
            if not a or not a.get("href"):
                continue

            href = urljoin(page_url, a["href"])
            if href in processed_urls:
                logger.info(f" Already exists, skipping: {href}")
                continue

            # article_data = extract_article_data(href)
            # if not article_data:
            #     logger.info(f" Skipped (invalid or error): {href}")
            #     continue

            # new_articles.append(article_data)
            # processed_urls.add(href)
            # added_count += 1
            # logger.info(f" Added [{added_count}/{max_articles}] to {section_name}: {article_data['title'][:60]}...")
            
            article_data = extract_article_data(href)

            # Always mark the URL as processed, even if it fails
            processed_urls.add(href)

            if not article_data:
                logger.info(f" Skipped (invalid or error): {href}")
                continue

            new_articles.append(article_data)
            added_count += 1
            logger.info(f" Added [{added_count}/{max_articles}] to {section_name}: {article_data['title'][:60]}...")
        logger.info(f" Done with section: {section_name}, Total new added: {added_count}")

    except Exception as e:
        logger.error(f" Error scraping {section_name}: {e}\n{traceback.format_exc()}")

    return new_articles

# --------------------- Main --------------------- #

def all_hiphop_scraper():
    results = []
    processed_urls = set()

    # Load existing data
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                results = json.load(f)
                processed_urls = {item.get("source_url") for item in results if isinstance(item, dict) and item.get("source_url")}
                logger.info(f" Loaded {len(results)} existing articles.")
        except Exception as e:
            logger.warning(f" Failed to load existing data. Starting fresh.")
            results = []
            processed_urls = set()

    # Scrape each section
    all_new_articles = []
    for section, config in SECTIONS.items():
        section_articles = scrape_section(section, config["url_template"], processed_urls)
        all_new_articles.extend(section_articles)

    # Save only new unique articles
    save_new_results(all_new_articles, Path(OUTPUT_FILE))
    logger.info(f" All scraping complete. Final total: {len(results) + len(all_new_articles)} articles.")


# --------------------- CLI --------------------- #

# if __name__ == "__main__":
#     all_hiphop_scraper()
