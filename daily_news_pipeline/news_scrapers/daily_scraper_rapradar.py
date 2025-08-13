
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from pathlib import Path
import json
import os
import time
from datetime import datetime
import logging

# ------------------- CONFIGURATION -------------------

OUTPUT_FILE = Path(__file__).resolve().parent / "news_articles_data" / "news_articles_scrap_data.json"
HOME_URL = "https://rapradar.com/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}
DELAY = 1
TIMEOUT = 30

LOG_FILE = 'log/scraper.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# ------------------- UTILITIES -------------------

def initialize_json_file(filepath):
    if not os.path.exists(filepath):
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=2)
        logging.info(f"Initialized JSON file: {filepath}")

def load_existing_articles(filepath):
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            logging.warning(f"Corrupt JSON file: {filepath}, starting with empty list.")
            return []
    return []

def save_articles(filepath, articles):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
    logging.info(f"Saved {len(articles)} total articles to: {filepath}")

def parse_datetime(raw_str):
    try:
        cleaned = raw_str.split('@')[0].strip()
        return datetime.strptime(cleaned, "%B %d, %Y")
    except:
        return None

# ------------------- SCRAPER -------------------

def scrape_homepage_articles(home_url, seen_urls):
    articles = []
    try:
        res = requests.get(home_url, headers=HEADERS, timeout=TIMEOUT)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')
        article_links = soup.select('a.entry_title')

        for tag in article_links:
            href = tag.get('href')
            full_url = urljoin(home_url, href)

            if not href or full_url in seen_urls:
                continue

            try:
                article_res = requests.get(full_url, headers=HEADERS, timeout=TIMEOUT)
                article_res.raise_for_status()
                article_soup = BeautifulSoup(article_res.text, 'html.parser')

                title = article_soup.select_one('header h2')
                title = title.get_text(strip=True) if title else "No title"

                content = article_soup.select_one('#entry_content')
                description = "\n".join(p.get_text(strip=True) for p in content.find_all('p')) if content else ""

                raw_date_tag = article_soup.select_one('span.date')
                raw_date = raw_date_tag.get_text(strip=True) if raw_date_tag else ""
                pub_datetime = parse_datetime(raw_date)

                author_tag = article_soup.select_one('span.author')
                author = author_tag.get_text(strip=True) if author_tag else "Unknown"

                article = {
                    "source_url": full_url,
                    "title": title,
                    "description": description,
                    "author": author,
                    "publication_date": pub_datetime.strftime("%d-%m-%Y") if pub_datetime else "Unknown"
                }

                articles.append(article)
                seen_urls.add(full_url)
                logging.info(f"Added article: {title}")

            except Exception as e:
                logging.warning(f"Error processing article {full_url}: {e}")

            time.sleep(DELAY)

    except Exception as e:
        logging.error(f"Error scraping homepage: {e}")

    return articles

def scrape_rapradar_home(output_file):
    initialize_json_file(output_file)
    existing_articles = load_existing_articles(output_file)
    seen_urls = {article['source_url'] for article in existing_articles}
    
    new_articles = scrape_homepage_articles(HOME_URL, seen_urls)
    
    if new_articles:
        combined = existing_articles + new_articles
        save_articles(output_file, combined)
    else:
        logging.info("No new unique articles found.")



# ------------------- MAIN WRAPPER -------------------

def rapradar_scraper():
    output_file = OUTPUT_FILE
    try:
        scrape_rapradar_home(output_file)
        logging.info("Scraping completed.")
    except Exception as e:
        logging.critical(f"Critical error: {e}")


# ------------------- CLI -------------------

# if __name__ == "__main__":
#     rapradar_scraper()
