"""Configuration settings for the application."""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Neo4j Configuration
NEO4J_CONFIG = {
    'uri': os.getenv('NEO4J_URI'),
    'username': os.getenv('NEO4J_USERNAME'),
    'password': os.getenv('NEO4J_PASSWORD'),
    'database': os.getenv('NEO4J_DATABASE')
}

# Pinecone Configuration
PINECONE_CONFIG = {
    'api_key': os.getenv('PINECONE_API_KEY'),
    'environment': os.getenv('PINECONE_ENV'),
    'index_name': os.getenv('PINECONE_INDEX_NAME', 'news-data-index')
}

# Google AI Configuration
GOOGLE_CONFIG = {
    'api_key': os.getenv('GOOGLE_API_KEY')
}
