# pipelines/daily_pipeline.py

import os
import json
import logging
from datetime import datetime

from daily_news_pipeline import (
    all_hiphop_scraper,
    hiphopdx_scraper,
    okayplayer_scraper,
    rapradar_scraper,
    hotnew_hiphop,
    hiphop_1987_scraper,
    hiphophero_scraper,
    rap_up_scraper
)
from daily_news_pipeline.data_uploder.articles_uploder import upload_to_neo4j, embed_and_upsert

logger = logging.getLogger(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.normpath(os.path.join(
    BASE_DIR,
    "..",
    "daily_news_pipeline",
    "news_scrapers",
    "news_articles_data",
    "news_articles_scrap_data.json"
))

def run_full_pipeline():
    """
    Executes the daily pipeline:
    - Scrapes news articles from multiple hip-hop news sites.
    - Uploads data to Neo4j.
    - Embeds and stores in Pinecone.
    """

    try:
        logger.info("Starting daily scraping and upload pipeline")

        # Run all scrapers
        all_hiphop_scraper()
        hiphopdx_scraper()
        okayplayer_scraper()
        rapradar_scraper()
        hotnew_hiphop()
        hiphop_1987_scraper()
        hiphophero_scraper()
        rap_up_scraper()

        logger.info("All scrapers completed successfully.")

        # Load scraped data
        if not os.path.exists(OUTPUT_FILE):
            logger.error(f"Data file not found: {OUTPUT_FILE}")
            return {"status": "error", "message": "Data file not found."}

        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            all_articles = json.load(f)

        logger.info(f"Loaded {len(all_articles)} total articles from {OUTPUT_FILE}")

        # Filter today's articles
        today_str = datetime.today().strftime("%d-%m-%Y")
        today_articles = [
            article for article in all_articles
            if article.get("publication_date", "").strip() == today_str
        ]

        if not today_articles:
            logger.warning("No articles found for today's date.")
            return {"status": "no articles", "count": 0}

        logger.info(f"Found {len(today_articles)} articles for {today_str}")

        # Upload to Neo4j
        upload_to_neo4j(today_articles)
        logger.info("Uploaded articles to Neo4j successfully.")

        # Upload to Pinecone
        embed_and_upsert(today_articles)
        logger.info("Embedded and upserted articles to Pinecone successfully.")

        return {"status": "success", "count": len(today_articles)}

    except Exception as e:
        logger.exception("Pipeline execution failed")
        return {"status": "error", "message": str(e)}
