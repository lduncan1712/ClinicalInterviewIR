from pathlib import Path
from typing import List, Dict, Any
import os 

from python_venv.models import supabase_client

def get_retrieval(query_vector:list[float], speaker: str = None, n:int = 5) -> List[dict[str, Any]]:
    """
    Retrieves a subset of the most semantically similar transcripts segments from Supabase database
    
    Arguments:
        query_vector: The vector to compare similarity against
        speaker: An optional speaker filter
        n: The number of most similar segments to return

    Returns: A list of dictionaries each representing a relevant transcript segment
    """
    response = supabase_client.rpc("match_segments", {
        "query_embedding": query_vector,
        "speaker_filter": speaker,
        "match_count": n
    }).execute()
    return response.data
