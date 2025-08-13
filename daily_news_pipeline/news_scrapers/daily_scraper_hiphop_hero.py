import logging
import json
import time
import os
import subprocess
import sys
from datetime import datetime
from dateutil import parser
from playwright.sync_api import sync_playwright

OUTPUT_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "news_articles_data",
    "news_articles_scrap_data.json"
)

# ---------------------------- Setup Logging ----------------------------
 
log_filename = "scraper.log"
logging.basicConfig(
    filename=log_filename,
    filemode="a",
    level=logging.INFO,
    format="%(asctime)s — %(levelname)s — %(message)s",
)

console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s — %(levelname)s — %(message)s")
console.setFormatter(formatter)
logging.getLogger().addHandler(console)



# ---------------------------- Scrape Full Article ----------------------------

def scrape_article_details(context, url):
    try:
        article_page = context.new_page()
        article_page.goto(url, wait_until="domcontentloaded", timeout=60000)
        article_page.wait_for_timeout(3000)

        logging.info(f"Loaded article page: {url}")

        title_el = article_page.query_selector("h1")
        author_el = article_page.query_selector("div.post-author a") or article_page.query_selector("span.byline a")
        date_el = article_page.query_selector("time")
        content_els = article_page.query_selector_all("article p") or article_page.query_selector_all("div.entry-content p")

        title = title_el.inner_text().strip() if title_el else "N/A"
        author = author_el.inner_text().strip() if author_el else "Unknown"

        publication_date = "Unknown"
        if date_el:
            raw_date = date_el.get_attribute("datetime") or date_el.inner_text().strip()
            try:
                dt = parser.parse(raw_date)
                publication_date = dt.strftime("%d-%m-%Y")
            except Exception as e:
                logging.warning(f"Failed to parse date: {raw_date} — {e}")
                publication_date = raw_date

        description = "\n".join(p.inner_text().strip() for p in content_els) if content_els else ""

        article_page.close()
        logging.info(f"Scraped article: {title} | {publication_date}")
        return {
            "source_url": url,
            "title": title,
            "description": description,
            "author": author,
            "publication_date": publication_date
        }
    except Exception as e:
        logging.error(f"Failed to scrape article {url}: {e}")
        return None


#---------------------------- Scrape List of Articles ----------------------------

def scrape_recent_articles(base_url, output_file=OUTPUT_FILE):
    all_data = []

    # Load existing data to avoid duplicates
    existing_data = []
    existing_urls = set()
    try:
        with open(output_file, "r", encoding="utf-8") as f:
            existing_data = json.load(f)
            existing_urls = {item["source_url"] for item in existing_data if "source_url" in item}
        logging.info(f"Loaded {len(existing_data)} existing articles.")
    except FileNotFoundError:
        logging.info("No existing file found. Starting fresh.")
    except Exception as e:
        logging.error(f"Error reading existing file: {e}")

    try:
        with sync_playwright() as p:
            logging.info("Launching browser...")
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"]
            )

            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800}
            )

            page = context.new_page()
            logging.info(f"Navigating to: {base_url}")
            page.goto(base_url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(3000)

            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(2000)

            page.wait_for_selector(".post-list article", timeout=20000)
            articles = page.query_selector_all(".post-list article")
            logging.info(f"Found {len(articles)} articles")

            for i, article in enumerate(articles, 1):
                title_el = article.query_selector("h2 a")
                href = title_el.get_attribute("href") if title_el else None

                if not href:
                    logging.info(f"[SKIP] Missing href in article #{i}")
                    continue

                if href in existing_urls:
                    logging.info(f"[SKIP] Duplicate article found: {href}")
                    continue

                logging.info(f"[{i}] Scraping article: {href}")
                article_data = scrape_article_details(context, href)
                if article_data:
                    all_data.append(article_data)
                    existing_urls.add(href)
                time.sleep(1)

            browser.close()
            logging.info("Browser closed.")
    except Exception as e:
        logging.critical(f"Unexpected error in scraping process: {e}")

    try:
        final_data = existing_data + all_data
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(final_data, f, indent=2, ensure_ascii=False)
        logging.info(f" Saved {len(all_data)} new articles. Total: {len(final_data)}")
    except Exception as e:
        logging.error(f"Failed to write output file: {e}")

def hiphophero_scraper():
    url = "https://hiphophero.com/articles/news/"
    try:
        scrape_recent_articles(url)
        logging.info("Scraping completed.")
    except Exception as e:
        logging.critical(f"Critical error: {e}")


# ---------------------------- CLI ----------------------------

# if __name__ == "__main__":
#     hiphophero_scraper()
