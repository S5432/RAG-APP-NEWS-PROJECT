# api/routes.py
from fastapi import APIRouter
from pydantic import BaseModel
from services.query_service import run_rag_pipeline
from pipelines.daily_pipeline import run_full_pipeline
from services.memory_service import memory_manager
from typing import Optional

router = APIRouter()

class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None

class SessionRequest(BaseModel):
    session_id: str

@router.post("/ask")
def ask_query(request: QueryRequest):
    """Ask a question with conversation memory support."""
    response, session_id = run_rag_pipeline(request.query, request.session_id)
    return {
        "query": request.query,
        "response": response,
        "session_id": session_id
    }

@router.post("/session/clear")
def clear_session(request: SessionRequest):
    """Clear conversation history for a session."""
    memory_manager.clear_session(request.session_id)
    return {"message": f"Session {request.session_id} cleared successfully"}

@router.post("/session/delete")
def delete_session(request: SessionRequest):
    """Delete a conversation session."""
    memory_manager.delete_session(request.session_id)
    return {"message": f"Session {request.session_id} deleted successfully"}

@router.get("/session/{session_id}/history")
def get_session_history(session_id: str):
    """Get conversation history for a session."""
    history = memory_manager.get_chat_history(session_id)
    return {
        "session_id": session_id,
        "history": history if history else "No conversation history found"
    }

@router.post("/session/new")
def create_new_session():
    """Create a new conversation session."""
    session_id, _ = memory_manager.get_or_create_session()
    return {"session_id": session_id}

@router.get("/run-pipeline")
def run_pipeline():
    return run_full_pipeline()

@router.get("/health")
def health():
    return {"status": "ok"}

@router.get("/latest-articles")
def get_latest_articles():
    """Get latest articles with their source URLs."""
    from data.graph_db import graph
    
    # Query to get latest articles with URLs and authors
    query = """
    MATCH (a:Article)-[:HAS_URL]->(u:URL)
    OPTIONAL MATCH (au:Author)-[:WROTE]->(a)
    RETURN a.title AS title, a.description AS description, au.name AS author, 
           a.publication_date AS publication_date, u.url AS source_url
    ORDER BY a.publication_date DESC
    LIMIT 10
    """
    
    try:
        result = graph.query(query)
        articles = []
        
        for row in result:
            articles.append({
                "title": row.get("title", "Unknown"),
                "description": row.get("description", "No description available"),
                "author": row.get("author", "Unknown"),
                "publication_date": str(row.get("publication_date", "Unknown")),
                "source_url": row.get("source_url", "")
            })
        
        return {
            "articles": articles,
            "count": len(articles)
        }
    except Exception as e:
        return {
            "error": f"Failed to fetch articles: {str(e)}",
            "articles": [],
            "count": 0
        }
