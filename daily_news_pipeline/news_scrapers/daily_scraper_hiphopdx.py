import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
import time
import logging
import os 


# ------------------------------- Set up logging --------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# news_articles_scrap_data.json

OUTPUT_FILE = Path(__file__).resolve().parent / "news_articles_data" / "news_articles_scrap_data.json"

#------------------ Utility Function to clean text by removing unwanted phrases and extra whitespace -----------------
def clean_text(text):
    text = re.sub(r'AD LOADING\.\.\.', '', text)  # Remove ad placeholders
    text = re.sub(r'\s+', ' ', text).strip()  # Normalize whitespace
    return text


#------------------------------- Function to convert relative date to MM-DD-YYYY format -----------------------
def parse_relative_date(relative_date, reference_date=None):
    if not reference_date:
        reference_date = datetime.now()
    relative_date = relative_date.lower().strip()
    if 'ago' in relative_date:
        parts = relative_date.split()
        num = int(parts[0]) if parts[0].isdigit() else 1  # Default to 1 if number not specified
        unit = parts[1]
        if 'week' in unit:
            delta = timedelta(weeks=num)
        elif 'day' in unit:
            delta = timedelta(days=num)
        elif 'hour' in unit:
            delta = timedelta(hours=num)
        else:
            return 'Unknown Date'
        return (reference_date - delta).strftime('%d-%m-%Y')
    return 'Unknown Date'

# Function to parse date with multiple formats
def parse_date_string(date_str, article_url):
    date_formats = [
        '%B %d, %Y',          # e.g., July 4, 2025
        '%B %d %Y',           # e.g., July 4 2025
        '%d %B %Y',           # e.g., 4 July 2025
        '%Y-%m-%d',           # e.g., 2025-07-04
        '%B %d, %Y at %I:%M %p'  # e.g., July 5, 2025 at 6:10 PM
    ]
    date_str = clean_text(date_str)
    for date_format in date_formats:
        try:
            parsed_date = datetime.strptime(date_str, date_format)
            return parsed_date.strftime('%d-%m-%Y')
        except ValueError:
            continue
    logging.warning(f"Date parsing failed for {article_url} with string: '{date_str}'")
    return None


#------------------------------- Function to scrape an individual article page -----------------------

def scrape_article(article_url, relative_date=None):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(article_url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # Log response details
        logging.debug(f"Response for {article_url}: Status {response.status_code}, Size {len(response.content)} bytes")

        # Extract title
        title = soup.find('h1', class_='entry-title')
        title_text = clean_text(title.get_text(strip=True)) if title else 'Unknown Title'

        # Extract author
        author_tag = soup.find('span', class_='author vcard') or soup.find('meta', {'name': 'author'}) or soup.find('span', class_='authors')
        author = clean_text(author_tag.get_text(strip=True)) if author_tag else 'Unknown Author'

        # Extract publication date
        publication_date = None
        # Priority 1: <time class="post-date published">
        date_tag = soup.find('time', class_='post-date published')
        if date_tag:
            date_str = clean_text(date_tag.get_text(strip=True))
            publication_date = parse_date_string(date_str, article_url)
            if publication_date:
                logging.info(f"Date extracted for {article_url} from post-date published: {publication_date}")
            else:
                logging.warning(f"Failed to parse date from post-date published for {article_url}: {date_str}")
                logging.debug(f"Raw HTML for post-date published: {str(date_tag)}")

        # Priority 2: Any <time> tag
        if not publication_date:
            date_tags = soup.find_all('time')
            for date_tag in date_tags:
                date_str = clean_text(date_tag.get_text(strip=True))
                publication_date = parse_date_string(date_str, article_url)
                if publication_date:
                    logging.info(f"Date extracted for {article_url} from time tag: {publication_date}")
                    break
                else:
                    logging.debug(f"Failed to parse date from time tag for {article_url}: {date_str}")
                    logging.debug(f"Raw HTML for time tag: {str(date_tag)}")

        # Priority 3: <meta property="article:published_time">
        if not publication_date:
            date_tag = soup.find('meta', {'property': 'article:published_time'})
            if date_tag:
                date_str = date_tag.get('content')
                try:
                    parsed_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    publication_date = parsed_date.strftime('%d-%m-%Y')
                    logging.info(f"Date extracted for {article_url} from meta article:published_time: {publication_date}")
                except ValueError as e:
                    logging.warning(f"Date parsing error for {article_url} (meta article:published_time, '{date_str}'): {e}")
                    logging.debug(f"Raw HTML for meta article:published_time: {str(date_tag)}")

        # Priority 4: <meta name="dc.date"> or <meta name="date">
        if not publication_date:
            date_tag = soup.find('meta', {'name': 'dc.date'}) or soup.find('meta', {'name': 'date'})
            if date_tag:
                date_str = date_tag.get('content')
                publication_date = parse_date_string(date_str, article_url)
                if publication_date:
                    logging.info(f"Date extracted for {article_url} from meta dc.date or date: {publication_date}")
                else:
                    logging.warning(f"Failed to parse date from meta dc.date or date for {article_url}: {date_str}")
                    logging.debug(f"Raw HTML for meta dc.date or date: {str(date_tag)}")

        # Priority 5: Fallback to relative date or 'Unknown Date'
        if not publication_date:
            publication_date = parse_relative_date(relative_date) if relative_date else 'Unknown Date'
            logging.warning(f"No valid date found for {article_url}, using: {publication_date}")

        # Extract description (all paragraphs in article body)
        article_body = soup.find('div', class_='entry-content')
        description = ''
        if article_body:
            paragraphs = article_body.find_all('p')
            description = ' '.join(clean_text(p.get_text(strip=True)) for p in paragraphs if p.get_text(strip=True))

        return {
            'source_url': article_url,
            'title': title_text,
            'description': description or 'No description available',
            'author': author,
            'publication_date': publication_date
        }
    except Exception as e:
        logging.error(f"Error scraping {article_url}: {e}")
        return None

# ------------------------------- Function to scrape a single page of the homepage ----------------------------
def scrape_page(url, article_urls):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        # Log response details
        logging.debug(f"Response for {url}: Status {response.status_code}, Size {len(response.content)} bytes")

        # Featured article
        featured = soup.find('div', id='featured')
        if featured:
            link = featured.find('a', href=True, class_='post-thumbnail-inner')
            if link and 'hiphopdx.com/news' in link['href']:
                article_urls[link['href'].split('?')[0]] = None  # No relative date in featured section

        # Today's Headlines (grid-item)
        grid_items = soup.find_all('div', class_='grid-item')
        for item in grid_items:
            link = item.find('a', href=True, class_='post-thumbnail')
            if link and 'hiphopdx.com/news' in link['href']:
                article_urls[link['href'].split('?')[0]] = None  # No relative date in grid-item

        # The Latest (post-item)
        latest_items = soup.find_all('div', class_='post-item')
        for item in latest_items:
            link = item.find('a', href=True, class_='post-thumbnail-inner')
            time_tag = item.find('span', class_='post-time')
            relative_date = time_tag.get_text(strip=True) if time_tag else None
            if link and 'hiphopdx.com/news' in link['href']:
                article_urls[link['href'].split('?')[0]] = relative_date

        # Featured Carousel (slider-item)
        carousel_items = soup.find_all('div', class_='slider-item')
        for item in carousel_items:
            link = item.find('a', href=True, class_='post-thumbnail-inner')
            if link and 'hiphopdx.com/news' in link['href']:
                article_urls[link['href'].split('?')[0]] = None  # No relative date in carousel

        # Neverending Grid (grid-item)
        neverending_items = soup.find('div', id='neverending').find_all('div', class_='grid-item') if soup.find('div', id='neverending') else []
        for item in neverending_items:
            link = item.find('a', href=True, class_='post-thumbnail')
            if link and 'hiphopdx.com/news' in link['href']:
                article_urls[link['href'].split('?')[0]] = None  # No relative date in neverending

        return soup
    except Exception as e:
        logging.error(f"Error scraping page {url}: {e}")
        return None

#------------------------------- Function to scrape article page for additional URLs -------------------------------
def scrape_article_for_urls(soup, article_urls):
    # Latest News sidebar
    latest_news = soup.find('div', class_='widget-latest-posts news')
    if latest_news:
        post_items = latest_news.find_all('div', class_='post-item')
        for item in post_items:
            link = item.find('a', href=True)
            if link and 'hiphopdx.com/news' in link['href']:
                article_urls[link['href'].split('?')[0]] = None  # No relative date in sidebar
    return article_urls



# ------------------------------- Save Function ------------------------

def save_articles(article_data):
    output_dir = os.path.dirname(OUTPUT_FILE)
    os.makedirs(output_dir, exist_ok=True)

    existing_articles = {}
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            try:
                loaded = json.load(f)
                for article in loaded:
                    url = article.get('source_url')
                    if url:
                        existing_articles[url] = article
            except json.JSONDecodeError:
                logging.warning("Existing JSON file is empty or corrupted. Starting fresh.")

    new_articles = {article['source_url']: article for article in article_data}
    combined_articles = {**existing_articles, **new_articles}

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(list(combined_articles.values()), f, indent=4, ensure_ascii=False)

    logging.info(f"Saved {len(new_articles)} new articles. Total: {len(combined_articles)}")


# ------------------------------- Main Scraper Function -------------------------------

def scrape_hiphopdx_homepage(max_pages=1):
    base_url = 'https://hiphopdx.com/now/{}'
    article_urls = {}

    for page in range(1, max_pages + 1):
        url = base_url.format(page) if page > 1 else 'https://hiphopdx.com/'
        logging.info(f"Scraping page {page}: {url}")
        soup = scrape_page(url, article_urls)
        if not soup:
            continue

        load_more = soup.find('div', class_='load-more')
        if not load_more or page == max_pages:
            break
        time.sleep(1)

    article_data = []
    for article_url, relative_date in list(article_urls.items()):
        logging.info(f"Scraping article: {article_url}")
        article_info = scrape_article(article_url, relative_date)
        if article_info:
            article_data.append(article_info)
            try:
                response = requests.get(article_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
                soup = BeautifulSoup(response.content, 'html.parser')
                article_urls = scrape_article_for_urls(soup, article_urls)
            except Exception as e:
                logging.error(f"Error scraping {article_url} for additional URLs: {e}")
        time.sleep(1)

    save_articles(article_data)
    logging.info("Scraping and saving completed.")
    return article_data


# ------------------------------- Entry Point ------------------------

def hiphopdx_scraper():
    max_pages = 1
    try:
        scrape_hiphopdx_homepage(max_pages)
        logging.info("Scraping completed.")
    except Exception as e:
        logging.critical(f"Critical error: {e}")


#------------------------------- Run the scraper -------------------------------
# if __name__ == '__main__':
#     hiphopdx_scraper()  