# data/graph_db.py
from langchain_community.graphs import Neo4jGraph
import os
from dotenv import load_dotenv

load_dotenv()

def get_graph():
    return Neo4jGraph(
        url=os.getenv("NEO4J_URI"),
        username=os.getenv("NEO4J_USERNAME"),
        password=os.getenv("NEO4J_PASSWORD")
    )

graph = get_graph()
