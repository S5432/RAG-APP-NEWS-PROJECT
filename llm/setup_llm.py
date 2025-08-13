# llm/setup_llm.py
from langchain_google_genai import ChatGoogleGenerativeAI
import os
from dotenv import load_dotenv

load_dotenv()

def get_llm():
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        raise ValueError("Missing GOOGLE_API_KEY.")
    
    return ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-lite",
        temperature=0.0,
        google_api_key=google_api_key
    )

llm = get_llm()
