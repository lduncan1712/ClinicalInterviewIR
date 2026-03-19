from pathlib import Path
from typing import List, Dict, Any
import tempfile
from groq.types.audio import Transcription
import os

from python_venv.models import groq_client


def get_transcription(audio_path: str) -> Transcription:
    """
    Transcribes audio file

    Arguments:
        audio_path: Path to specified audio file

    Returns: A transcription object containing file transcription
    """
    with open(audio_path, "rb") as f:
        result = groq_client.audio.transcriptions.create(
            file=f,
            model="whisper-large-v3-turbo",
            response_format="verbose_json"
        )
        return result
    