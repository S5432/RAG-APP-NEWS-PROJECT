import os
import sys
import json
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv
from tqdm import tqdm
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from pinecone import Pinecone, ServerlessSpec
from pathlib import Path
from neo4j import GraphDatabase


# ------------------------------- Load environment variables -------------------------------

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")


# ------------------------------- Load config -------------------------------

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from configuration import NEO4J_CONFIG


# ------------------------------- Logging Setup ------------------------------- 

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(module)s - %(funcName)s - %(lineno)d - %(message)s",
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger(__name__)


# ------------------------------- Load JSON File -------------------------------
# G:\16-07-2025\New_News_Rag_App_V2\daily_news_pipeline\news_scrapers\news_articles_data\news_articles_data.json
# INPUT_JSON = Path("news_scrapers/news_articles_data/news_articles_data.json")

BASE_DIR = Path(__file__).resolve().parent.parent  # Go from data_uploder/ to daily_news_pipeline/
INPUT_JSON = BASE_DIR / "news_scrapers" / "news_articles_data" / "news_articles_scrap_data.json"

print(f"Loading JSON from: {INPUT_JSON}")


def load_json_data(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            articles = json.load(f)
        logger.info(f"Loaded {len(articles)} articles from {file_path}")
        return articles
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from {file_path}: {e}")
        return []
    except Exception as e:
        logger.error(f"An unexpected error occurred while loading JSON from {file_path}: {e}")
        return []

articless = load_json_data(INPUT_JSON)


# ------------------------------- Filter Articles Published Today -------------------------------

def filter_today_articles(articless):
    today_str = datetime.today().strftime("%d-%m-%Y")
    today_articles = []

    for article in articless:
        pub_date = article.get("publication_date", "").strip()
        if pub_date == today_str:
            today_articles.append(article)

    logger.info(f"Filtered {len(today_articles)} articles published today ({today_str}).")
    return today_articles


# Replace articles with filtered articles
articles = filter_today_articles(articless)


# ------------------------------- Upload to Neo4j -------------------------------

def parse_date(date_str):
    try:
        return datetime.strptime(date_str.strip(), "%d-%m-%Y").date().isoformat()
    except ValueError as e:
        logger.warning(f"Failed to parse date '{date_str}'. Error: {e}")
        return "1970-01-01"  
    except Exception as e:
        logger.error(f"Unexpected error parsing date '{date_str}': {e}")
        return "1970-01-01"

def insert_article_neo4j(tx, article):
    try:
        tx.run("""
            MERGE (a:Article {title: $title})
            SET a.description = $description,
                a.publication_date = date($publication_date),
                a.full_text = $full_text

            MERGE (au:Author {name: $author})
            MERGE (u:URL {url: $source_url})

            MERGE (au)-[:WROTE]->(a)
            MERGE (a)-[:HAS_URL]->(u)
        """, {
            "title": article.get("title", "Untitled"),
            "description": article.get("description", ""),
            "publication_date": parse_date(article.get("publication_date", "")),
            "author": article.get("author", "Unknown"),
            "source_url": article.get("source_url", ""),
            "full_text": article.get("description", "")
        })
        logger.debug(f"[Neo4j] Inserted: {article.get('title', 'Untitled')}") # Added debug level
    except Exception as e:
        logger.error(f"[Neo4j] Failed to insert article (Title: {article.get('title', 'Untitled')}).  Error: {e}")
        raise  

def upload_to_neo4j(articles):
    driver = None
    try:
        driver = GraphDatabase.driver(
            NEO4J_CONFIG["uri"],
            auth=(NEO4J_CONFIG["user"], NEO4J_CONFIG["password"])
        )
        with driver.session() as session:
            for article in articles:
                try:
                    session.execute_write(insert_article_neo4j, article)
                except Exception as e:
                    logger.error(f"[Neo4j] Error during Neo4j session: {e}")
                    
    except Exception as e:
        logger.critical(f"[Neo4j] Connection error: {e}")  # Catch connection level errors
    finally:
        if driver:
            driver.close()
        logger.info("Neo4j connection closed.")


# ------------------------------- Chunk + Embed + Upsert to Pinecone -------------------------------

embedding_model = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")
pc = Pinecone(api_key=PINECONE_API_KEY)
index_name = "news-data-index"
MAX_CHARS = 1000
BATCH_SIZE = 100


# ------------------------------- Pinecone Index Handling -------------------------------

def initialize_pinecone_index(index_name, dimension=768, metric="cosine", spec=ServerlessSpec(cloud="aws", region="us-east-1")):
    try:
        if index_name not in [i.name for i in pc.list_indexes()]:
            pc.create_index(name=index_name, dimension=dimension, metric=metric, spec=spec)
            logger.info(f"Created Pinecone index: {index_name}")
        else:
            logger.info(f"Pinecone index already exists: {index_name}")
        return pc.Index(index_name)
    except Exception as e:
        logger.critical(f"Error creating/connecting to Pinecone index: {e}")
        return None  # Indicate failure


index = initialize_pinecone_index(index_name)

def chunk_text(text, max_chars):
    return [text[i:i + max_chars] for i in range(0, len(text), max_chars)]

def embed_and_upsert(articles):
    if index is None:
        logger.warning("Skipping Pinecone upload due to index initialization failure.")
        return

    vectors = []
    for article in tqdm(articles, desc="Embedding & Chunking"):
        description = article.get("description", "").strip()
        if not description:
            continue

        chunks = chunk_text(description, MAX_CHARS)
        for idx, chunk in enumerate(chunks):
            try:
                content = f"Title: {article.get('title', '')}\nAuthor: {article.get('author', '')}\nDate: {article.get('publication_date', '')}\nChunk {idx+1}/{len(chunks)}\n\n{chunk}"
                embedding = embedding_model.embed_query(content)
                doc_id = f"{article.get('source_url', '')}#chunk-{idx+1}"
                metadata = {
                    "title": article.get("title", ""),
                    "author": article.get("author", ""),
                    "publication_date": article.get("publication_date", ""),
                    "url": article.get("source_url", ""),
                    "chunk_index": idx + 1,
                    "chunk_text": chunk
                }
                vectors.append({"id": doc_id, "values": embedding, "metadata": metadata})
            except Exception as e:
                logger.error(f"[Pinecone] Embedding failed for article (Title: {article.get('title', '')}, Chunk {idx+1}): {e}")

    try:
        for i in tqdm(range(0, len(vectors), BATCH_SIZE), desc="Upserting to Pinecone"):
            try:
                batch = vectors[i:i + BATCH_SIZE]
                index.upsert(vectors=batch)
            except Exception as e:
                logger.error(f"[Pinecone] Upsert failed for batch starting at index {i}: {e}")
    except Exception as e:
        logger.error(f"[Pinecone] Failed to upsert vectors: {e}")
    logger.info(f"[Pinecone] Upserted {len(vectors)} vectors.")





if __name__ == "__main__":
    try:
        if articles:
            logger.info(f"Processing {len(articles)} articles published today.")
            upload_to_neo4j(articles)
            embed_and_upsert(articles)
            logger.info("All tasks completed successfully.")
        else:
            logger.warning("No articles published today to process.")
    except Exception as e:
        logger.critical(f"Unhandled exception: {e}")