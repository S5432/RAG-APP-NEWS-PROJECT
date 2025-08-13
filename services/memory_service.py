# services/memory_service.py
from langchain.memory import ConversationBufferWindowMemory
from typing import Dict, Optional
import uuid

class ConversationMemoryManager:
    """Manages conversation memory for multiple chat sessions."""
    
    def __init__(self, window_size: int = 7):
        self.window_size = window_size
        self.sessions: Dict[str, ConversationBufferWindowMemory] = {}
    
    def get_or_create_session(self, session_id: Optional[str] = None) -> tuple[str, ConversationBufferWindowMemory]:
        """Get existing session or create new one."""
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        if session_id not in self.sessions:
            self.sessions[session_id] = ConversationBufferWindowMemory(
                k=self.window_size,  # Keep last 7 exchanges
                memory_key="chat_history",
                return_messages=True
            )
        
        return session_id, self.sessions[session_id]
    
    def add_exchange(self, session_id: str, human_input: str, ai_response: str):
        """Add human-AI exchange to session memory."""
        if session_id in self.sessions:
            memory = self.sessions[session_id]
            memory.save_context(
                {"input": human_input},
                {"output": ai_response}
            )
    
    def get_chat_history(self, session_id: str) -> str:
        """Get formatted chat history for a session."""
        if session_id not in self.sessions:
            return ""
        
        memory = self.sessions[session_id]
        chat_history = memory.load_memory_variables({})
        
        if not chat_history.get("chat_history"):
            return ""
        
        # Format the history for inclusion in prompts
        formatted_history = []
        for message in chat_history["chat_history"]:
            if hasattr(message, 'type'):
                if message.type == "human":
                    formatted_history.append(f"Human: {message.content}")
                elif message.type == "ai":
                    formatted_history.append(f"Assistant: {message.content}")
        
        return "\n".join(formatted_history)
    
    def clear_session(self, session_id: str):
        """Clear conversation history for a session."""
        if session_id in self.sessions:
            self.sessions[session_id].clear()
    
    def delete_session(self, session_id: str):
        """Delete a session entirely."""
        if session_id in self.sessions:
            del self.sessions[session_id]

# Global memory manager instance
memory_manager = ConversationMemoryManager()
