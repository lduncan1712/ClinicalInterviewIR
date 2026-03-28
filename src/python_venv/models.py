#Models In Use
HUGGINGFACE_MODEL = "pyannote/speaker-diarization-community-1"
SENTENCE_TRANSFORMER_MODEL = 'medicalai/ClinicalBERT'      #Alternate: 'all-MiniLM-L6-v2'


# Loading Environment Variables
from dotenv import load_dotenv
load_dotenv()

#Pyannote Diarization
import os
from pyannote.audio import Pipeline
huggingface_pipeline = Pipeline.from_pretrained(HUGGINGFACE_MODEL, token=os.getenv("HUGGINGFACE_TOKEN"))

#Sentence Embedding
from sentence_transformers import SentenceTransformer
embedding_model = SentenceTransformer(SENTENCE_TRANSFORMER_MODEL)

#Groq Model For Transcription + Generation
from groq import Groq
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

#Supabase Client For Database Access
from supabase import create_client
supabase_client = create_client(supabase_url=os.getenv("SUPABASE_URL"), supabase_key=os.getenv("SUPABASE_KEY"))