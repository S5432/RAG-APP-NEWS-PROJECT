# services/query_service.py
from llm.prompts import classification_prompt, greeting_prompt, cypher_prompt, qa_prompt, date_filter_query_prompt
from llm.setup_llm import llm
from data.graph_db import graph
from data.pinecone_index import run_semantic_query
from utils.result_formatter import format_result
from langchain_community.chains.graph_qa.cypher import GraphCypherQAChain
from langchain.chains import LLMChain
from services.memory_service import memory_manager
from typing import Optional

def classify_query(query: str, session_id: Optional[str] = None) -> str:
    """Classify query with conversation context."""
    chat_history = ""
    if session_id:
        chat_history = memory_manager.get_chat_history(session_id)
    
    chat_history_context = f"Conversation History:\n{chat_history}\n" if chat_history else "No previous conversation history."
    
    print(f"🔍 Classifying: '{query}' | Session: {session_id or 'New'} | History: {'Yes' if chat_history else 'No'}")
    
    classification_result = LLMChain(llm=llm, prompt=classification_prompt).run(
        query=query,
        chat_history_context=chat_history_context
    ).strip().upper()
    
    print(f" Category: {classification_result}")
    
    return classification_result

def handle_greeting(query: str, session_id: Optional[str] = None) -> str:
    """Handle greeting with conversation context."""
    chat_history = ""
    if session_id:
        chat_history = memory_manager.get_chat_history(session_id)
    
    chat_history_context = f"Conversation History:\n{chat_history}\n" if chat_history else "No previous conversation history."
    
    return LLMChain(llm=llm, prompt=greeting_prompt).run(
        query=query,
        chat_history_context=chat_history_context
    ).strip()

# def run_rag_query(query: str, session_id: Optional[str] = None) -> str:
#     """Run RAG query with conversation context."""
#     chat_history = ""
#     if session_id:
#         chat_history = memory_manager.get_chat_history(session_id)
    
#     chat_history_context = f"Conversation History:\n{chat_history}\n" if chat_history else "No previous conversation history."
    
#     print(f" Querying with context: {'Yes' if chat_history else 'No'}")
    
#     # Create modified qa_prompt with chat history
#     modified_qa_prompt = qa_prompt.partial(chat_history_context=chat_history_context)
    
#     # Always isolate Cypher query generation from conversation context
#     # This ensures fresh query generation without interference from previous queries
#     modified_cypher_prompt = cypher_prompt.partial(
#         conversation_context="No prior conversation influencing query. Current query only."
#     )
    
#     # Create a custom chain to intercept the Cypher query
#     from langchain.chains import LLMChain
    
#     # First generate the Cypher query separately for logging
#     cypher_gen_chain = LLMChain(llm=llm, prompt=modified_cypher_prompt)
#     cypher_query = cypher_gen_chain.run(
#         question=query,
#         schema=graph.schema,
#         conversation_context="No prior conversation influencing query. Current query only."
#     )
    
#     print(f"🔍 Generated Cypher Query: {cypher_query}")
    
#     # Clean the query if it has markdown formatting
#     clean_query = cypher_query.strip()
#     if clean_query.startswith('```cypher'):
#         clean_query = clean_query.replace('```cypher', '').replace('```', '').strip()
#         print(f"🔍 Cleaned Cypher Query: {clean_query}")
    
#     # Execute the query directly on the graph
#     try:
#         graph_result = graph.query(clean_query)
#         print(f"📊 Neo4j Graph Result: {graph_result}")
        
#         # If we got results, format them for the QA chain
#         if graph_result:
#             context_str = str(graph_result)
#             final_prompt = modified_qa_prompt.format(question=query, context=context_str)
#             final_response = llm.invoke(final_prompt).content.strip()
#             print(f"🤖 Generated response: {len(final_response)} characters")
#             return final_response
#         else:
#             raw_context = "Data Not Available"
#     except Exception as e:
#         print(f"⚠️ Cypher Query Error: {e}")
#         raw_context = "Data Not Available"
    
#     print(f"📊 Neo4j Raw Result: {raw_context}")
    
#     if (raw_context == "Data Not Available" or not raw_context or raw_context == [] or raw_context == "" or 
#         "I am sorry, but I do not have" in str(raw_context) or "I don't have" in str(raw_context) or 
#         "unable to answer" in str(raw_context) or "unable to provide" in str(raw_context) or 
#         "data is not available" in str(raw_context)):
#         print(f"⚠️  Neo4j: No data found, trying Pinecone...")
#         semantic_result = run_semantic_query(query)
#         print(f"📌 Pinecone result: {'Found' if semantic_result else 'Not found'}")
#         return semantic_result
    
#     print(f"✅ Neo4j: Data retrieved successfully")
#     context_str = raw_context if isinstance(raw_context, str) else str(raw_context)
#     final_prompt = modified_qa_prompt.format(question=query, context=context_str)
#     final_response = llm.invoke(final_prompt).content.strip()
#     print(f"🤖 Generated response: {len(final_response)} characters")
#     return final_response
 

#################For date filtering query ##################################
def run_rag_query_date_related(query: str, session_id: Optional[str] = None) -> str:
    """Run RAG query with conversation context (Neo4j Only)."""
    chat_history = ""
    if session_id:
        chat_history = memory_manager.get_chat_history(session_id)
    
    chat_history_context = f"Conversation History:\n{chat_history}\n" if chat_history else "No previous conversation history."
    
    print(f" Querying with context: {'Yes' if chat_history else 'No'}")
    
    modified_qa_prompt = qa_prompt.partial(chat_history_context=chat_history_context)
    modified_cypher_prompt = date_filter_query_prompt.partial(
        conversation_context="No prior conversation influencing query. Current query only."
    )
    
    # Generate Cypher query
    cypher_gen_chain = LLMChain(llm=llm, prompt=modified_cypher_prompt)
    cypher_query = cypher_gen_chain.run(
        question=query,
        schema=graph.schema,
        conversation_context="No prior conversation influencing query. Current query only."
    )
    
    print(f"🔍 Generated Cypher Query: {cypher_query}")
    
    clean_query = cypher_query.strip()
    if clean_query.startswith('```cypher'):
        clean_query = clean_query.replace('```cypher', '').replace('```', '').strip()
        print(f"🔍 Cleaned Cypher Query: {clean_query}")
    
    try:
        graph_result = graph.query(clean_query)
        print(f"Neo4j Graph Result: {graph_result}")
        
        if graph_result:
            context_str = str(graph_result)
            final_prompt = modified_qa_prompt.format(question=query, context=context_str)
            final_response = llm.invoke(final_prompt).content.strip()
            print(f"Generated response: {len(final_response)} characters")
            return final_response
        else:
            print(f"Neo4j: No data found, returning message.")
            return "I could not find any relevant information in the knowledge graph."
    except Exception as e:
        print(f"Cypher Query Error: {e}")
        return "There was an error processing your request with the knowledge graph."





def run_rag_query_music(query: str, session_id: Optional[str] = None) -> str:
    """Run RAG query with conversation context (Neo4j Only)."""
    chat_history = ""
    if session_id:
        chat_history = memory_manager.get_chat_history(session_id)
    
    chat_history_context = f"Conversation History:\n{chat_history}\n" if chat_history else "No previous conversation history."
    
    print(f" Querying with context: {'Yes' if chat_history else 'No'}")
    
    modified_qa_prompt = qa_prompt.partial(chat_history_context=chat_history_context)
    modified_cypher_prompt = cypher_prompt.partial(
        conversation_context="No prior conversation influencing query. Current query only."
    )
    
    # Generate Cypher query
    cypher_gen_chain = LLMChain(llm=llm, prompt=modified_cypher_prompt)
    cypher_query = cypher_gen_chain.run(
        question=query,
        schema=graph.schema,
        conversation_context="No prior conversation influencing query. Current query only."
    )
    
    print(f"🔍 Generated Cypher Query: {cypher_query}")
    
    clean_query = cypher_query.strip()
    if clean_query.startswith('```cypher'):
        clean_query = clean_query.replace('```cypher', '').replace('```', '').strip()
        print(f"🔍 Cleaned Cypher Query: {clean_query}")
    
    try:
        graph_result = graph.query(clean_query)
        print(f"📊 Neo4j Graph Result: {graph_result}")
        
        if graph_result:
            context_str = str(graph_result)
            final_prompt = modified_qa_prompt.format(question=query, context=context_str)
            final_response = llm.invoke(final_prompt).content.strip()
            print(f"🤖 Generated response: {len(final_response)} characters")
            return final_response
        else:
            print(f"⚠️ Neo4j: No data found, returning message.")
            return "I could not find any relevant information in the knowledge graph."
    except Exception as e:
        print(f"⚠️ Cypher Query Error: {e}")
        return "There was an error processing your request with the knowledge graph."


def run_rag_pipeline(query: str, session_id: Optional[str] = None) -> tuple[str, str]:
    """Run RAG pipeline with conversation memory."""
    print(f"\n🎵 Query: '{query}'")
    
    # Get or create session
    if session_id is None:
        session_id, _ = memory_manager.get_or_create_session()
        print(f" New session: {session_id}")
    else:
        session_id, _ = memory_manager.get_or_create_session(session_id)
        print(f" Existing session: {session_id}")
    
    # Classify query with context
    category = classify_query(query, session_id)
    
    # Generate response based on category
    print(f" Routing to: {category}")
    if category == "GREETING":
        response = handle_greeting(query, session_id)
    elif category == "DATE_RELATED":
        response = run_rag_query_date_related(query, session_id)
    elif category == "MUSIC_RELATED":
        response = run_rag_query_music(query, session_id)
    else:
        response = "Sorry, I can only answer music-related questions."
    
    # Save the conversation to memory
    memory_manager.add_exchange(session_id, query, response)
    print(f" Saved to memory | Session: {session_id}")
    
    return response, session_id


    