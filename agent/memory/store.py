import os
from dotenv import load_dotenv
from supabase import create_client
from agent.memory.embeddings import embed

load_dotenv()

_supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

def save_memory(session_id, content):
    """Embed a completed exchange and store it"""
    vector = embed(content)
    _supabase.table("agent_memories").insert({
        "session_id": session_id,
        "content": content,
        "embedding": vector,
    }).execute()

def recall_memories(query, match_count=5, similarity_threshold=0.5, session_id=None):
    """Embed the query and return teh moset similar stores memories"""
    vector = embed(query)
    response = _supabase.rpc("match_memories", {
        "query_embedding": vector,
        "match_count": match_count,
        "similarity_threshold": similarity_threshold,
        "filter_session": session_id,
    }).execute()
    return response.data