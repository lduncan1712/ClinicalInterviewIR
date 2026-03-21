from typing import List, Dict, Any
from pathlib import Path
import json

from python_venv.models import groq_client

def get_generation(query:str, system_prompt:str) -> str:
    """
    Generates A LLM Response For Inputted Query Using Specified Prompt

    Arguments:
        query: The user query a response is generated for
        system_prompt: Instructional prompt instructing response behaviour

    Returns: LLM generated response
    """
    summary = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        temperature=0.3,
        max_tokens=1024,
        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": query
            }
        ]
    )
    return summary.choices[0].message.content