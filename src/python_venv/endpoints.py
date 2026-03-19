from python_venv.pipeline import _transcribe
from fastapi import FastAPI, UploadFile, File, Form, Body
from pathlib import Path
from typing import List, Dict, Any
import tempfile
import json
import os

from python_venv.pipeline import _diarize, _embed, _generate, _retrieve, _transcribe

#The FastAPI App Hosting The Endpoints
app = FastAPI(title="Core Python Code")

@app.get("/test-status")
def test_status() -> Dict[str, str]:
    """
    A test endpoints confirming FastAPI status, 
    
    NOTE: This should also implicitly confirm models.py has been setup correctly 
    """
    return {"status": "ok", "message": "FastAPI Endpoint Reached"} 


@app.post("/transcribe-original-audio")
def transcribe_original_audio(audio_file: UploadFile = File(...)) -> List[Dict[str, Any]]:
    """
    An endpoint that transcribes an audio file into a participant labeled and diarized list of transcribed segments 
    
    ARGUMENTS:
        audio_file: The audio file to transcribe

    RETURNS: A list of dictionaries representing conversational segments

    NOTE:To avoid extra N8N nodes or unnecessary data transfer, this method contains the diarization and participant classification
         instead of making them seperate nodes, since they will only be used once (livekit handles these steps for live audio) 

         Also since both diarization and transcription are capable of generating segment timestamps, (diarization through diarized segments, 
         and transcription using pauses in speech), to avoid any differences or inconsistencies, for this method ive elected to treat the
         diarized sections as the segments/segment timestamps, and generate the transcription from within these timestamped segments.
    """
    try:  
        segments = [] 
        system_prompt = (Path(__file__).resolve().parents[2] / "prompts" / "CLASSIFIER.txt").read_text()

        #Save File Locally
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp.write(audio_file.file.read())
            audio_path = str(Path(tmp.name))

        #Load File
        from pydub import AudioSegment
        audio = AudioSegment.from_file(audio_path)

        #Diarize
        diarization = _diarize.get_diarization(audio_path=audio_path)

        #Transcribe Segments
        for segment, speaker in diarization.speaker_diarization:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_segment:
                audio[int(segment.start*1000):int(segment.end*1000)].export(tmp_segment.name, format="wav")
                segment_path = str(Path(tmp_segment.name))

            transcription = _transcribe.get_transcription(audio_path=segment_path)

            segments.append({
                "speaker": speaker,
                "start": segment.start,
                "end": segment.end,
                "text": transcription.text
            })

            os.remove(segment_path)
        os.remove(audio_path)

        #Classify Participants Using Context
        query = "\n".join(f"{segment['speaker']}: {segment['text']}" for segment in segments[:10])
        clinician = _generate.get_generation(query=query, system_prompt=system_prompt)
        for segment in segments:
            if segment['speaker'] == clinician:
                segment['speaker'] = "CLINICIAN" 
            else:
                segment['speaker'] = "PATIENT"

        return [{"transcription": segments}]
    except Exception as e:
        return [{"status": "error", "text": f"Error In Transcribe Original Audio: {str(e)}"}]

#TODO
@app.post("/transcribe-seperated-audio")
def transcribe_seperated_audio():
    #NOTE: This is a method stem for handling livekit audio chunks that are already seperated by participants
    pass

@app.post("/embed-segments")
def embed_segments(metadata: str) -> List[Dict[str, Any]]:
    """
    An endpoint which embeds segments

    ARGUMENTS:
        metadata: string json transcription data

    RETURNS: JSON transcription data with embeddings, etc added
    
    NOTE: For now this method includes no indexing, since supabase can handle
          assigning an id to each segment, however if further ids are required
          at a later point IE: if we want to handle multiple conversations
          the assigning of those IDs should be done within here.
    """
    try: 
        audio_transcriptions = json.loads(metadata)["transcription"]
        texts = [segment["text"] for segment in audio_transcriptions]
        embeddings = _embed.get_embeddings(texts)

        for embedding, transcription in zip(embeddings, audio_transcriptions):
            transcription["embedding"] = embedding

        return audio_transcriptions    
    except Exception as e:
        return [{"status": "error", "text": f"Error In Index Audio: {str(e)}"}]

def get_grounded_response(system_prompt_name: str, query:str = None, speaker:str = None, n:int = 50) -> str:
    """
    A support method for retrieval endpoints that generates a response to a prompt using grounded segments

    ARGUMENTS:
        system_prompt_name: The file name of the system prompt within the prompts folder
        query: An optional query prepending the data
        speaker: An optional speaker that when supplied, only incorporates segments from that speaker
        n: The number of most relevant segments to supply for response insight 

    RETURNS: A generated string response.

    NOTE: To ensure only medically related segments are analyszed, retrieved segments are first filtered
          to exclude the least medically related.
    """
    query_vector = _embed.get_embeddings(["Medical"])[0]

    segments = _retrieve.get_retrieval(query_vector=query_vector, speaker=speaker, n=n)

    segments_str = json.dumps(segments)

    system_prompt = (Path(__file__).resolve().parents[2] / "prompts" / system_prompt_name).read_text()

    return _generate.get_generation(query=f"{query}: {segments_str}", system_prompt=system_prompt)

@app.post("/generate-summary")
def generate_summary(speaker:str = None, n:int = 20) -> str:
    """
    An endpoint which returns a grounded summary

    Please see the wrapped method for details
    """
    try:
        return get_grounded_response(system_prompt_name="SUMMARIZATION.txt", query=None, speaker=speaker, n=n)
    except Exception as e:
            return [{"status": "error", "text": f"Error In Generate Summary: {str(e)}"}]

@app.post("/generate-analysis")
def generate_analysis(speaker:str = None, n:int = 20) -> str:
    """
    An endpoint which returns a grounded analysis

    Please see the wrapped method for details
    """
    try:
        return get_grounded_response(system_prompt_name="ANALYZER.txt", query=None, speaker=speaker, n=n)
    except Exception as e:
            return [{"status": "error", "text": f"Error In Generate Analysis: {str(e)}"}]

@app.post("/generate-answer")
def generate_answer(query:str, speaker:str = None, n:int = 20) -> str:
    """
    An endpoint which returns a grounded answer to a user posed question

    Please see the wrapped method for details
    """
    try:
        return get_grounded_response(system_prompt_name="QUESTIONS.txt", query=query, speaker=speaker, n=n)
    except Exception as e:
            return [{"status": "error", "text": f"Error In Generate Answer: {str(e)}"}]







#OLD/IN PROGRESS

#NOTE: Not Tested, As LiveKit Not Setup And This Is Based On Expected LiveKit Outputs, Subject To Change
#@app.post("/transcribe-seperated-audio")
"""
def transcribe_separated_audio(audio_files: List[UploadFile] = File(...), metadata: str = Form(...)) -> dict:
    try:
        audio_paths = []
        metadata = json.loads(metadata)

        for audio_file in audio_files:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                tmp.write(audio_file.file.read())
                audio_paths.append(str(Path(tmp.name)))

        ret = _transcribe.transcribe_seperated_audio(audio_paths=audio_paths, metadata=metadata)

        #TODO: Clear Temp Files
        
        return [{"transciption:": ret}]
    
    except Exception as e:
        raise RuntimeError(f"Error In Transcribe Separated Audio: {str(e)}")
"""