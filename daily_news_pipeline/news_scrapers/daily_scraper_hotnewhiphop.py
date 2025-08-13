
import requests
from bs4 import BeautifulSoup
import json
import time
from datetime import datetime
from pathlib import Path
import re
import os
import logging

# ------------------ Logging Configuration ------------------ #

LOG_DIR = "log"
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOG_DIR, "scraper.log"),
    filemode="a",
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# OUTPUT_FILE = os.path.join(BASE_DIR, "news_articles_data", "news_articles_data.json")

OUTPUT_FILE = Path(__file__).resolve().parent / "news_articles_data" / "news_articles_scrap_data.json"

# ------------------ Constants ------------------ #

BASE_URL = "https://www.hotnewhiphop.com"
HOMEPAGE_URL = BASE_URL
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}


def clean_text(text):
    if text:
        text = re.sub(r'\s+', ' ', text.strip())
        text = re.sub(r'AD\s+LOADING\.\.\.', '', text).strip()
        return text
    return ""


def parse_date(date_str, datetime_attr=None):
    try:
        # If <time datetime="2025-07-16T23:50:00Z"> exists, use it
        if datetime_attr:
            dt = datetime.fromisoformat(datetime_attr.replace('Z', '+00:00'))
            return dt.strftime("%d-%m-%Y")
        
        if "ago" in date_str.lower():
            logging.warning(f"Relative time detected: '{date_str}'. Skipping exact date parsing.")
            return None  # Better to store as None instead of wrong date

        cleaned = re.sub(r"(?i)^Published on\s+", "", date_str.strip())
        parsed = datetime.strptime(cleaned, "%B %d, %Y")
        return parsed.strftime("%d-%m-%Y")

    except Exception as e:
        logging.warning(f"Date parsing failed for '{date_str}': {e}")
        return None



def scrape_article_details(article_url):
    try:
        response = requests.get(article_url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        title_elem = soup.find('h1') or soup.find('h1', class_=re.compile('article-title|title', re.I))
        title = clean_text(title_elem.get_text()) if title_elem else "No title found"

        author_elem =soup.select_one(
                    'body > div:nth-of-type(1) > header > div > span:nth-of-type(1) > span:nth-of-type(1) > a')
        author = clean_text(author_elem.get_text()) if author_elem else "Unknown author"

        # Date
        # date_elem = soup.find('time') or soup.find('span', class_=re.compile('date|published', re.I))
        # publication_date = parse_date(clean_text(date_elem.get_text())) if date_elem else None

        date_elem = soup.find('time') or soup.find('span', class_=re.compile('date|published', re.I))
        datetime_attr = date_elem.get('datetime') if date_elem else None
        publication_date = parse_date(clean_text(date_elem.get_text()), datetime_attr=datetime_attr) if date_elem else None


        # Description
        content_elem = soup.find('div', class_=re.compile('article-content|post-content|content', re.I))
        paragraphs = content_elem.find_all('p') if content_elem else []
        description = " ".join(clean_text(p.get_text()) for p in paragraphs) if paragraphs else "No description found"

        # Skip some unwanted categories
        if "song stream" in title.lower() or "music video" in title.lower() or "new music" in description.lower():
            return None

        return {
            "source_url": article_url,
            "title": title,
            "description": description,
            "author": author,
            "publication_date": publication_date
        }

    except Exception as e:
        logging.error(f"Error scraping article {article_url}: {e}")
        return None


def scrape_homepage():
    articles_data = []
    try:
        response = requests.get(HOMEPAGE_URL, headers=HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        article_links = []

        # Top Story
        top_story = soup.find('div', class_='lg:basis-3/4')
        if top_story:
            link = top_story.find('a', href=True)
            if link and 'href' in link.attrs:
                article_links.append(link['href'])

        # Secondary Stories
        secondary_stories = soup.find('div', class_='flex flex-row lg:flex-col gap-4 lg:basis-1/4')
        if secondary_stories:
            for link in secondary_stories.find_all('a', href=True, class_=re.compile('line-clamp-3')):
                if 'href' in link.attrs:
                    article_links.append(link['href'])

        # Trending Section
        trending = soup.find('div', class_='w-full lg:w-[326px]')
        if trending:
            for link in trending.find_all('a', href=True, class_=re.compile('line-clamp-3')):
                if 'href' in link.attrs:
                    article_links.append(link['href'])

        # Latest News
        latest_news = soup.find('div', class_='w-full lg:w-1/2 mx-0 lg:mr-4 lg:ml-4 mb-0 mt-4 lg:mt-0')
        if latest_news:
            for item in latest_news.find_all('div', class_=re.compile('px-4 mb-.*grid')):
                link = item.find('a', href=True, class_=re.compile('text-base font-semibold'))
                if link and 'href' in link.attrs:
                    article_links.append(link['href'])

        # Category Sections
        category_sections = soup.find_all('div', class_='w-full lg:w-[30%] flex flex-col shrink-0')
        for section in category_sections:
            featured = section.find('div', class_='tag-card-first-item')
            if featured:
                link = featured.find('a', href=True, class_=re.compile('text-lg font-semibold'))
                if link and 'href' in link.attrs:
                    article_links.append(link['href'])
            other_articles = section.find_all('div', class_=re.compile('pl-4 flex relative flex-row'))
            for article in other_articles:
                link = article.find('a', href=True, class_=re.compile('text-base line-clamp-2'))
                if link and 'href' in link.attrs:
                    article_links.append(link['href'])

        # Clean and make full URLs
        article_links = list(set([BASE_URL + link if not link.startswith('http') else link for link in article_links]))

        for article_url in article_links:
            logging.info(f"Scraping article: {article_url}")
            article_data = scrape_article_details(article_url)
            if article_data:
                articles_data.append(article_data)
            time.sleep(1)

        logging.info(f"Total articles scraped: {len(articles_data)}")
        return articles_data

    except Exception as e:
        logging.error(f"Error scraping homepage: {e}")
        return []

    
def load_existing_articles(filename=OUTPUT_FILE):
    if not os.path.exists(filename):
        return []
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Error loading existing JSON: {e}")
        return []



def save_to_json(new_data, filename=OUTPUT_FILE):
    try:
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        existing_data = load_existing_articles(filename)
        existing_urls = set(item['source_url'] for item in existing_data)

        # Filter new unique articles
        unique_new_data = [item for item in new_data if item['source_url'] not in existing_urls]

        all_data = existing_data + unique_new_data

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, indent=4, ensure_ascii=False)

        logging.info(f"{len(unique_new_data)} new unique articles added. Total: {len(all_data)}")
    except Exception as e:
        logging.error(f"Error saving to JSON: {e}")



def hotnew_hiphop():
    logging.info("Starting scraper...")
    new_articles = scrape_homepage()
    if new_articles:
        save_to_json(new_articles)
        logging.info("Scraping completed and data saved.")
    else:
        logging.warning("No articles were scraped.")


#---------------------------- CLI ----------------------------

# if __name__ == "__main__":
#     hotnew_hiphop()
