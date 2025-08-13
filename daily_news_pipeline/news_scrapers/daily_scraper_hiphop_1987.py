
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import re
import time
import logging
import os

# ------------------ Logging Configuration ------------------ #

LOG_DIR = "log"
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOG_DIR, "scraper.log"),
    filemode="a",
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ------------------ Text Cleaning ------------------ #

def clean_text(text):
    return ' '.join(text.strip().split()).encode('ascii', 'ignore').decode('ascii')


# ------------------ Load Existing Data ------------------ #

def load_existing_articles(filename):
    if not os.path.exists(filename):
        return []
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Failed to load existing data from {filename}: {e}")
        return []

# ------------------ Save Articles to JSON (Avoid Duplicates) ------------------ #

def save_articles(new_articles, filename):
    try:
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        existing_articles = load_existing_articles(filename)
        existing_urls = {article['source_url'] for article in existing_articles}

        unique_articles = [a for a in new_articles if a['source_url'] not in existing_urls]
        combined = existing_articles + unique_articles

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(combined, f, indent=4, ensure_ascii=False)

        logging.info(f"{len(unique_articles)} new unique articles saved. Total: {len(combined)}")
    except Exception as e:
        logging.error(f"Error saving articles to {filename}: {e}")


# ------------------ Scrape Full Article ------------------ #


def scrape_article_content(article_url):
    try:
        response = requests.get(article_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        content_div = soup.find('div', class_='post-entry')  # <- Correct class here
        if not content_div:
            return ""

        paragraphs = content_div.find_all('p')
        description = "\n".join([clean_text(p.get_text()) for p in paragraphs if p.get_text().strip()])
        return description
    except Exception as e:
        logging.error(f"Error scraping full article content {article_url}: {e}")
        return ""



# ------------------ Scrape One Page ------------------ #

def scrape_page(page_url):
    try:
        response = requests.get(page_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        articles = soup.find_all('div', class_='block-item-big')
        article_data = []

        for article in articles:
            title_tag = article.find('h2').find('a') if article.find('h2') else None
            if not title_tag:
                continue
            source_url = title_tag['href']
            title = clean_text(title_tag.get_text())

            author_tag = article.find('span', class_='heading-author')
            author = clean_text(author_tag.get_text()) if author_tag else "Unknown"

            date_tag = article.find('span', class_='heading-date')
            if date_tag:
                date_text = clean_text(date_tag.get_text())
                try:
                    parsed_date = datetime.strptime(date_text, "%B %d, %Y")
                    publication_date = parsed_date.strftime("%d-%m-%Y")
                except ValueError:
                    publication_date = date_text
            else:
                publication_date = "Unknown"
            
            content_wrapper = soup.select_one('.post-entry')
            paragraphs = article.find_all('p') if article else []
            description = "\n".join(p.get_text(strip=True) for p in paragraphs)

           
            full_description = scrape_article_content(source_url)
            if not full_description:
                full_description = description


            article_info = {
                "source_url": source_url,
                "title": title,
                "description": full_description,
                "author": author,
                "publication_date": publication_date
            }
            article_data.append(article_info)
            time.sleep(1)

        return article_data, soup
    except Exception as e:
        logging.error(f"Error scraping page {page_url}: {e}")
        return [], None

# ------------------ Main Scraper ------------------ #
def hiphop_1987_scraper():
    base_url = "https://hiphopsince1987.com/"
    all_articles = []
    page = 1
    max_pages = 3
    file_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "news_articles_data",
        "news_articles_scrap_data.json"
    )

    while page <= max_pages:
        page_url = base_url if page == 1 else f"{base_url}page/{page}/"
        logging.info(f"Scraping page {page}: {page_url}")
        articles, soup = scrape_page(page_url)
        if not articles and not soup:
            break
        all_articles.extend(articles)

        pagination = soup.find('div', class_='pagination')
        if not pagination or not pagination.find('a', href=re.compile(f'page/{page + 1}/')):
            break

        page += 1
        time.sleep(1)

    if all_articles:
        save_articles(all_articles, file_path)
        logging.info(f"Scraping completed. Total new articles scraped: {len(all_articles)}")
    else:
        logging.warning("No articles found on homepage.")


# --------------------- CLI --------------------- #



# if __name__ == "__main__":
#     hiphop_1987_scraper()


