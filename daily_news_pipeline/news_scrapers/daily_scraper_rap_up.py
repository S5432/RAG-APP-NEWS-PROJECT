import asyncio
import sys
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import os
import re
import subprocess
import json
import time
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from urllib.parse import urljoin
from pathlib import Path
import traceback
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


# --------------------- Config --------------------- #

DELAY = 1
TIMEOUT = 30
MAX_ARTICLES_PER_SECTION = 15
OUTPUT_FILE = Path(__file__).resolve().parent / "news_articles_data" / "news_articles_scrap_data.json"
DATE_FORMAT_INPUT = "%m.%d.%Y"
DATE_FORMAT_OUTPUT = "%d-%m-%Y"
LOG_FILE = "log/scraperr.log"


# --------------------- Logging Setup --------------------- #

log_dir = os.path.dirname(LOG_FILE)
if log_dir:
    os.makedirs(log_dir, exist_ok=True)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

handler = RotatingFileHandler(LOG_FILE, maxBytes=1024 * 1024, backupCount=5, encoding='utf-8')
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')
handler.setFormatter(formatter)

if not logger.hasHandlers():
    logger.addHandler(handler)

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)



# --------------------- Helpers --------------------- #
filename = OUTPUT_FILE

def format_publication_date(pub_date_str):
    try:
        if not pub_date_str:
            return "Unknown"
        dt = datetime.strptime(pub_date_str.strip(), DATE_FORMAT_INPUT)
        return dt.strftime(DATE_FORMAT_OUTPUT)
    except ValueError:
        logger.warning(f"Could not parse date: {pub_date_str}")
        return "Unknown"
    except Exception as e:
        logger.exception(f"Date formatting error: {pub_date_str}")
        return "Unknown"


# --------------------- Helpers --------------------- #

def save_unique_to_json(data, filename):
    try:
        logger.info("Saving unique articles to JSON...")
        unique = {}
        for item in data:
            url = item.get("source_url")
            if url and url not in unique:
                unique[url] = item

        dir_name = os.path.dirname(filename)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(list(unique.values()), f, ensure_ascii=False, indent=2)
        logger.info(f"Saved {len(unique)} unique articles to {filename}")
    except Exception as e:
        logger.exception("Error saving JSON.")



# --------------------- Scraper Logic --------------------- #

def scrape_section(page, section_url, section_name, results):
    article_count = 0
    logger.info(f"Scraping section: {section_name} | URL: {section_url}")
    try:
        page.goto(section_url, timeout=TIMEOUT * 1000)
        page.wait_for_selector('h3 a', timeout=10000)
        soup = BeautifulSoup(page.content(), 'html.parser')
        article_links = soup.select('h3 a')

        for a_tag in article_links:
            if article_count >= MAX_ARTICLES_PER_SECTION:
                logger.info(f"Reached max article limit ({MAX_ARTICLES_PER_SECTION}) for {section_name}")
                break
            href = a_tag.get('href')
            if not href:
                continue
            full_url = urljoin(section_url, href)
            if any(r.get('source_url') == full_url for r in results):
                logger.debug(f"Skipping duplicate article: {full_url}")
                continue

            try:
                page.goto(full_url, timeout=TIMEOUT * 1000)
                page.wait_for_selector('.default-content-wrapper', timeout=10000)
                article_soup = BeautifulSoup(page.content(), 'html.parser')

                title = article_soup.select_one('h1')
                content_wrapper = article_soup.select_one('.default-content-wrapper')
                description = re.sub(r'\\s+', ' ', " ".join(
                    p.get_text(strip=True) for p in content_wrapper.find_all('p')
                )) if content_wrapper else ""

                by_line = article_soup.select_one('p.by-line')
                pub_date = author = "Unknown"
                if by_line:
                    parts = by_line.get_text(strip=True).split('/')
                    if len(parts) > 1:
                        pub_date = format_publication_date(parts[-1].strip())
                    author_tag = by_line.select_one('a')
                    if author_tag:
                        author = author_tag.get_text(strip=True)

                article_data = {
                    "source_url": full_url,
                    "title": title.get_text(strip=True) if title else "No title",
                    "description": description,
                    "author": author,
                    "publication_date": pub_date
                }

                results.append(article_data)
                article_count += 1
                logger.info(f"[{section_name}] Scraped: {article_data['title'][:60]}")

            except Exception as article_err:
                logger.exception(f"Error scraping article: {full_url}")

            time.sleep(DELAY)

    except Exception as section_err:
        logger.exception(f"Failed to scrape section front page: {section_url}")
    finally:
        logger.info(f"Finished scraping section: {section_name} | Articles scraped: {article_count}")
        time.sleep(DELAY)


# --------------------- Main Entry --------------------- #

def rap_up_scraper():
    logger.info("======== Starting Rap-Up Scraper Pipeline ========")
    results = []
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
                results = json.load(f)
                logger.info(f"Loaded {len(results)} existing articles from JSON.")
        except json.JSONDecodeError:
            logger.warning("JSON file corrupted. Starting with empty results.")
        except Exception as e:
            logger.exception("Failed to load previous JSON data.")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_default_timeout(TIMEOUT * 1000)

            # News Front Page
            scrape_section(page, "https://www.rap-up.com/category/news", "news", results)

            # Other sections
            sections = [
                {"name": "new-music", "url": "https://www.rap-up.com/category/new-music"},
                {"name": "exclusives", "url": "https://www.rap-up.com/category/exclusives"},
                {"name": "music-videos", "url": "https://www.rap-up.com/category/music-videos"}
            ]
            for section in sections:
                scrape_section(page, section["url"], section["name"], results)

            browser.close()
            logger.info("Browser session closed.")

        save_unique_to_json(results, OUTPUT_FILE)
        logger.info(f"Scraping complete. Total articles saved: {len(results)}")
    
    except Exception as final_err:
        logger.exception("Fatal error in the scraping pipeline.")

    logger.info("======== Finished Rap-Up Scraper Pipeline ========")


# --------------------- CLI --------------------- #

# if __name__ == "__main__":
#     rap_up_scraper()