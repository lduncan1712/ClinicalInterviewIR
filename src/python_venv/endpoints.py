from fastapi import FastAPI, UploadFile, File, Form, Body, WebSocket, Request
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv
import time
import tempfile
import json
import os
import asyncio
import wave
from collections import defaultdict

ENV_PATH = Path(__file__).resolve().parents[1] / "docker" / ".env"
load_dotenv(dotenv_path=ENV_PATH)

import httpx
from livekit import api
from livekit.api import LiveKitAPI
from pydantic import BaseModel

from python_venv.pipeline import _diarize, _embed, _generate, _retrieve, _transcribe

PCM_SAMPLE_RATE = 48000
PCM_SAMPLE_WIDTH = 2
PCM_CHANNELS = 1
CHUNK_SECONDS = 10

BYTES_PER_SECOND = PCM_SAMPLE_RATE * PCM_SAMPLE_WIDTH * PCM_CHANNELS
CHUNK_SIZE_BYTES = BYTES_PER_SECOND * CHUNK_SECONDS

speaker_buffers = defaultdict(bytearray)
speaker_chunk_index = defaultdict(int)
speaker_chunk_start = defaultdict(float)
speaker_locks = defaultdict(asyncio.Lock)
class LiveKitTokenRequest(BaseModel):
    room_name: str
    participant_identity: str
    participant_name: str | None = None
    
#The FastAPI App Hosting The Endpoints
app = FastAPI(title="Core Python Code")

#allow requests between different ports
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def reset_speaker_state(speaker: str):
    speaker_buffers[speaker] = bytearray()
    speaker_chunk_index[speaker] = 0
    speaker_chunk_start[speaker] = 0.0
    
    
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
                "start": round(segment.start, 1),
                "end": round(segment.end, 1),
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

@app.post("/livekit-token")
def create_livekit_token(payload: LiveKitTokenRequest) -> dict:
    try:
        api_key = os.getenv("LIVEKIT_API_KEY")
        api_secret = os.getenv("LIVEKIT_API_SECRET")

        print("LIVEKIT_API_KEY:", api_key)
        print("LIVEKIT_API_SECRET exists:", api_secret is not None)

        if not api_key or not api_secret:
            raise ValueError("api_key and api_secret must be set")
        
        token= (
            api.AccessToken(api_key=api_key, api_secret=api_secret)
            .with_identity(payload.participant_identity)
            .with_name(payload.participant_name or payload.participant_identity)
            .with_grants(
                api.VideoGrants(
                    room_join=True,
                    room=payload.room_name,
                    can_publish=True,
                    can_subscribe=True,
                )
            )
            .to_jwt()
        )
        return{
            "server_url": "ws://localhost:7880",
            "participant_token": token,
        }
    except Exception as e:
        return{
            "status": "error",
            "text": f"Error creating LiveKit token: {str(e)}"
        }
        
class StartEgressTrack(BaseModel):
    speaker: str
    track_id: str

class StartEgressRequest(BaseModel):
    room_name: str
    tracks: list[StartEgressTrack]
    
@app.post("/livekit/start-egress")
async def start_livekit_egress(payload: StartEgressRequest):
    try: 
        api_key = os.getenv("LIVEKIT_API_KEY")
        api_secret = os.getenv("LIVEKIT_API_SECRET")
        
        if not api_key or not api_secret:
            raise ValueError("Livekit credential missing")
        
        #Connects to Livekit server
        lkapi = LiveKitAPI(
            url="http://localhost:7880",
            api_key=api_key,
            api_secret=api_secret,
        )
        
        results = []
        
        for track in payload.tracks:
            print(f"Starting egress for {track.speaker}: {track.track_id}")
            
            req = api.TrackEgressRequest(
                room_name = payload.room_name,
                track_id = track.track_id,
                websocket_url = f"ws://host.docker.internal:8000/ws/live-audio/{track.speaker}",
            )
            
            res = await lkapi.egress.start_track_egress(req)

            results.append({
                "speaker": track.speaker,
                "egress_id": res.egress_id
            })
        
        await lkapi.aclose()    
        
        return {"status": "started", "egress": results}
    
    except Exception as e:
        print("Egress error:", repr(e))
        return {"status": "error", "text": str(e)}
    
#TODO
@app.post("/transcribe-seperated-audio")
async def transcribe_seperated_audio(request: Request):
    try:
        form = await request.form()
        print("TRANSCRIBE FORM KEYS:", list(form.keys()))

        audio_file = form.get("audio_file")
        metadata = form.get("metadata")

        if audio_file is None:
            return {"status": "error", "text": "Missing audio_file"}
        if metadata is None:
            return {"status": "error", "text": "Missing metadata"}

        parsed = json.loads(metadata)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp.write(await audio_file.read())
            audio_path = str(Path(tmp.name))

        transcription = _transcribe.get_transcription(audio_path=audio_path)

        print("TRANSCRIPTION TYPE:", type(transcription))
        print("TRANSCRIPTION VALUE:", transcription)

        if isinstance(transcription, dict):
            segments = transcription.get("segments", transcription)
        elif hasattr(transcription, "segments"):
            segments = transcription.segments
        else:
            segments = transcription

        if isinstance(segments, dict):
            segments = segments.get("segments", [])

        ret = []
        for segment in segments:
            if isinstance(segment, dict):
                seg_start = segment.get("start", 0)
                seg_end = segment.get("end", 0)
                seg_text = segment.get("text", "").strip()
            else:
                seg_start = getattr(segment, "start", 0)
                seg_end = getattr(segment, "end", 0)
                seg_text = getattr(segment, "text", "").strip()

            # Fix 3: clamp timestamps to the chunk length
            seg_start = max(0, min(seg_start, CHUNK_SECONDS))
            seg_end = max(seg_start, min(seg_end, CHUNK_SECONDS))

            # optional cleanup for junk outputs
            if (
                not seg_text or
                seg_text in [".", " "] or
                len(seg_text.strip()) < 3 or
                len(seg_text.split()) < 2
            ):
                continue

            seg_text_lower = seg_text.lower().strip()

            if any(p in seg_text_lower for p in ["thank you", "thanks", "okay"]):
                continue
            
            raw_text = seg_text.strip()
            ret.append({
                "speaker": parsed["speaker"],
                "start": parsed["start"],
                "end": parsed["start"],
                "text": raw_text,
            })

        os.remove(audio_path)
        return [{"transcription": ret}]

    except Exception as e:
        print("TRANSCRIBE ERROR:", repr(e))
        return {"status": "error", "text": f"Error In Transcribe Separated Audio: {str(e)}"}


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



async def send_live_chunk_to_n8n(
    speaker: str,
    audio_bytes: bytes,
    chunk_index: int,
    start_time: float,
    end_time: float,
    room_name: str = "test-room",
):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        wav_path = tmp.name
        
        
    try:
        with wave.open(wav_path, "wb") as wf:
            wf.setnchannels(PCM_CHANNELS)
            wf.setsampwidth(PCM_SAMPLE_WIDTH)
            wf.setframerate(PCM_SAMPLE_RATE)
            wf.writeframes(audio_bytes)

        metadata = {
            "speaker": speaker,
            "room_name": room_name,
            "chunk_index": chunk_index,
            "start": start_time,
            "end": end_time,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            with open(wav_path, "rb") as f:
                files = {
                    "audio_file": ("chunk.wav", f, "audio/wav"),
                }
                data = {
                    "metadata": json.dumps(metadata),
                }

                resp = await client.post(
                    "http://localhost:5678/webhook/2b33e750-870d-4df6-bcb9-c432d8876c1a",
                    files=files,
                    data=data,
                )

        print(f"Sent {speaker} chunk {chunk_index} to n8n: {resp.status_code}")
        try:
            print("n8n response:", resp.text[:300])
        except Exception:
            pass

    finally:
        if os.path.exists(wav_path):
            os.remove(wav_path)
            

@app.websocket("/ws/live-audio/{speaker}")
async def live_audio_ws(websocket: WebSocket, speaker: str):
    await websocket.accept()
    reset_speaker_state(speaker)
    print(f"{speaker} connected to audio stream")

    if speaker_chunk_start[speaker] == 0:
        speaker_chunk_start[speaker] = time.time()

    try:
        while True:
            message = await websocket.receive()

            if "bytes" in message and message["bytes"] is not None:
                data = message["bytes"]

                async with speaker_locks[speaker]:
                    speaker_buffers[speaker].extend(data)

                    while len(speaker_buffers[speaker]) >= CHUNK_SIZE_BYTES:
                        chunk = bytes(speaker_buffers[speaker][:CHUNK_SIZE_BYTES])
                        del speaker_buffers[speaker][:CHUNK_SIZE_BYTES]

                        chunk_index = speaker_chunk_index[speaker]
                        start_time = speaker_chunk_start[speaker]
                        end_time = start_time + CHUNK_SECONDS

                        speaker_chunk_index[speaker] += 1
                        speaker_chunk_start[speaker] = end_time
                        
                        print(
                            f"{speaker} chunk ready: idx={chunk_index}, "
                            f"bytes={len(chunk)}, start={start_time:.2f}, end={end_time:.2f}"
                        )

                        asyncio.create_task(
                            send_live_chunk_to_n8n(
                                speaker=speaker,
                                audio_bytes=chunk,
                                chunk_index=chunk_index,
                                start_time=start_time,
                                end_time=end_time,
                            )
                        )

            elif "text" in message and message["text"] is not None:
                print(f"{speaker} event: {message['text']}")

    except Exception as e:
        print(f"{speaker} disconnected: {e}")
        reset_speaker_state(speaker)
        

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