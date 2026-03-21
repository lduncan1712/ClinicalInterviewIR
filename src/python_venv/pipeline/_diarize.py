from pathlib import Path
import torch
from pyannote.core import Annotation
from typing import Dict, Any
import soundfile as sf

from python_venv.models import huggingface_pipeline

def get_diarization(audio_path: str) -> Annotation:
    """
    Diarizes a selected audio file

    Arguments:
        audio_path: Local audio file path to diarize

    Returns: An Annotation object describing labeled time segments
    """
    data, sample_rate = sf.read(audio_path, dtype='float32')
    if data.ndim == 1:
        waveform = torch.tensor(data).unsqueeze(0)
    else:
        waveform = torch.tensor(data).T
    diarization = huggingface_pipeline({"waveform": waveform, "sample_rate": sample_rate})
    return diarization
