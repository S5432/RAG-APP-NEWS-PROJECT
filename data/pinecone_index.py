# data/pinecone_index.py
from pinecone import Pinecone
from llm.embeddings import get_embeddings
from utils.result_formatter import format_result
from configuration import PINECONE_CONFIG
import os

pinecone_api_key = PINECONE_CONFIG['api_key']
pinecone_env = PINECONE_CONFIG['environment']
pinecone_index_name = PINECONE_CONFIG['index_name']

def get_index():
    pc = Pinecone(api_key=pinecone_api_key, environment=pinecone_env)
    return pc.Index(pinecone_index_name)

def semantic_search(query, top_k=1):
    index = get_index()
    embeddings = get_embeddings()
    vector = embeddings.embed_query(query)
    results = index.query(vector=vector, top_k=top_k, include_metadata=True)

    articles = []
    for match in results.matches:
        meta = match.metadata
        articles.append(f"**{meta.get('title', 'Untitled')}** by {meta.get('author', 'Unknown')} on {meta.get('publication_date', 'Unknown')}\nURL: {meta.get('url', 'N/A')}\n\n{meta.get('full_text', '')}")
    return articles

def run_semantic_query(query):
    raw = semantic_search(query)
    return format_result(query, "\n\n".join(raw), source="pinecone")
