import requests
from bs4 import BeautifulSoup
import json
import os
import time
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin
import traceback

# --------------------- Config --------------------- #

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}
DATE_FORMAT_INPUT = "%B %d, %Y"
DATE_FORMAT_OUTPUT = "%d-%m-%Y"
START_DATE = datetime(2024, 7, 1)
END_DATE = datetime.now()
DELAY = 1
TIMEOUT = 30
OUTPUT_FILE = Path(__file__).resolve().parent / "news_articles_data" / "news_articles_scrap_data.json"
LOG_FILE = "log/scraper.log"

# --------------------- Logging --------------------- #

log_dir = os.path.dirname(LOG_FILE)
if log_dir:
    os.makedirs(log_dir, exist_ok=True)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = RotatingFileHandler(LOG_FILE, maxBytes=1024 * 1024, backupCount=5, encoding='utf-8')
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# --------------------- JSON Helpers --------------------- #

def initialize_json_file():
    try:
        if not os.path.exists(OUTPUT_FILE) or os.stat(OUTPUT_FILE).st_size == 0:
            with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                json.dump([], f, indent=2)
            logger.info(f" Initialized or reset empty JSON file: {OUTPUT_FILE}")
    except Exception as e:
        logger.error(f" Error initializing JSON file: {e}\n{traceback.format_exc()}")

def load_existing_urls():
    existing_urls = set()
    try:
        if os.path.exists(OUTPUT_FILE):
            with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                existing_urls = {item.get("source_url") for item in data if isinstance(item, dict) and item.get("source_url")}
                logger.info(f" Loaded {len(existing_urls)} existing URLs from {OUTPUT_FILE}")
    except Exception as e:
        logger.error(f" Error loading URLs: {e}\n{traceback.format_exc()}")
    return existing_urls

def append_to_json(new_data):
    try:
        if os.path.exists(OUTPUT_FILE):
            with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
                existing = json.load(f)
        else:
            existing = []
        existing.extend(new_data)
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(existing, f, indent=2)
        logger.info(f" Appended {len(new_data)} articles to {OUTPUT_FILE}")
    except Exception as e:
        logger.error(f" Failed to append data to {OUTPUT_FILE}: {e}\n{traceback.format_exc()}")

# --------------------- Date Parser --------------------- #

def parse_date(date_str):
    try:
        if not date_str:
            return "Unknown", None
        dt = datetime.strptime(date_str.strip(), DATE_FORMAT_INPUT)
        return dt.strftime(DATE_FORMAT_OUTPUT), dt
    except Exception as e:
        logger.error(f" Date parsing error: {e} for date string: '{date_str}'\n{traceback.format_exc()}")
        return "Unknown", None

# --------------------- Scraper --------------------- #

def scrape_okayplayer_page_static(base_url):
    existing_urls = load_existing_urls()
    new_articles = []
    try:
        res = requests.get(base_url, headers=HEADERS, timeout=TIMEOUT)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")
        
        
        article_links = [urljoin(base_url, a.get("href")) for a in soup.select("h3 a") if a.get("href")]
        article_links = article_links[:15]  

        article_count = 0  

        for url in article_links:
            if url in existing_urls:
                logger.info(f" Skipping existing: {url}")
                continue

            try:
                res_article = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
                res_article.raise_for_status()
                article_soup = BeautifulSoup(res_article.text, "html.parser")

                title = article_soup.select_one('h1 span')
                desc = article_soup.select('div.body-description p')
                date_tag = article_soup.select_one('div.social-date span')
                author = article_soup.select_one('div.social-author a')

                pub_date_str = date_tag.get_text(strip=True) if date_tag else ""
                formatted_date, date_obj = parse_date(pub_date_str)

                article_data = {
                    "source_url": url,
                    "title": title.get_text(strip=True) if title else "No title",
                    "description": "\n".join(p.get_text(strip=True) for p in desc) if desc else "",
                    "author": author.get_text(strip=True) if author else "Unknown",
                    "publication_date": formatted_date
                }

                new_articles.append(article_data)
                existing_urls.add(url)
                article_count += 1
                logger.info(f" Added [{article_count}/15]: {url}")
                time.sleep(DELAY)

            except Exception as e:
                logger.error(f" Failed to process article {url}: {e}")

        if new_articles:
            append_to_json(new_articles)

    except Exception as e:
        logger.error(f" Failed to scrape {base_url}: {e}")


# --------------------- Main --------------------- #

def okayplayer_scraper():
    initialize_json_file()
    logger.info(" Starting OkayPlayer Scraper...")
    scrape_okayplayer_page_static("https://www.okayplayer.com/news")
    logger.info("Scraping section pages...")
    sections = [
        "https://www.okayplayer.com/music",
        "https://www.okayplayer.com/originals",
        "https://www.okayplayer.com/culture",
        "https://www.okayplayer.com/cities"
    ]
    for url in sections:
        logger.info(f"Scraping section: {url}")
        scrape_okayplayer_page_static(url)
    logger.info("Scraping finished successfully.")

# ---------------------------- CLI ----------------------------
# if __name__ == "__main__":
#     okayplayer_scraper()
