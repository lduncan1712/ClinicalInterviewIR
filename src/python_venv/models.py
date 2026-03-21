#Ensuring Environment Variable Is Loaded
from dotenv import load_dotenv
load_dotenv()

#Pyannote Diarization
import os
from pyannote.audio import Pipeline
huggingface_pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-community-1", token=os.getenv("HUGGINGFACE_TOKEN"))

#BERT Based Embedding Model
from sentence_transformers import SentenceTransformer
"""
Possible Models To Use:
- 'all-MiniLM-L6-v2'
- 'medicalai/ClinicalBERT'
"""
embedding_model = SentenceTransformer('medicalai/ClinicalBERT')

#Groq Model For Transcription + Generation
from groq import Groq
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

#Supabase Client For Database Access
from supabase import create_client
supabase_client = create_client(supabase_url=os.getenv("SUPABASE_URL"), supabase_key=os.getenv("SUPABASE_KEY"))
