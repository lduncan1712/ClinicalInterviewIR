import sys
import os
import requests
#THE MAIN PURPOSE OF THIS FILE WAS TO BYPASS DOCKER< AS MY COMPUTER DOES NOT HAVE VIRTUALIZATION ENABLED< AND EVERYTIME I HAVE GONE INTO MY BIOS TO CHANGE IT, IT WILL LITERALLY NOT LOAD SO I CAN NOT ENABLE VIRTUALIZATION
#Ensure we can import the models directly from your team's code
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from python_venv.models import supabase_client
from python_venv.pipeline import _embed

def upload_audio_to_database(audio_path):
    print(f"\n--- Processing {audio_path} ---")
    
    #Step 1: Use the local FastAPI server to run the AI Transcription & Diarization
    print("Working, may take afew minutes...")
    with open(audio_path, 'rb') as f:
        response = requests.post("http://localhost:8000/transcribe-original-audio", files={"audio_file": f})
        
    if response.status_code != 200:
        print("Error from FastAPI:", response.text)
        return
        
    segments = response.json()[0]['transcription']
    print(f"   -> Successfully extracted {len(segments)} dialogue chunks")
    
    #use embedding pipeline to do the math directly
    print("Generating mathematical ClinicalBERT embeddings for each chunk...")
    texts = [seg["text"] for seg in segments]
    embeddings = _embed.get_embeddings(texts)
    
    #inject it directly into the Supabase database
    print("Injecting data into supabase database...")
    for seg, emb in zip(segments, embeddings):
        supabase_client.table("segment").insert({
            "speaker": seg["speaker"],
            "start": seg["start"],
            "end": seg["end"],
            "text": seg["text"],
            "embedding": emb
        }).execute()
        
    print(f"SUCCESS")

if __name__ == "__main__":
    #name of file to upload
    test_file = "tests/test_audio/day1_consultation01_mixed.wav"
    upload_audio_to_database(test_file)
