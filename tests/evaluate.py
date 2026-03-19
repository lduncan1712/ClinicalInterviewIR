import textgrid         #library to read textgrid files
import sys              #sys for system variables (ofc)
import os               #os for operating system, helping look at folder paths (ofc)
import re               #re for regular expressions
import jiwer            #jlibrary for calculating WER

#ensure we can import from the src folder
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from python_venv.pipeline._transcribe import get_transcription

def parse_textgrid_transcript(file_path):
    """
    Reads a .TextGrid file and extracts all spoken text into a single string.
    This serves as our 'Ground Truth' Answer Key
    """
    #load the file
    tg = textgrid.TextGrid.fromFile(file_path)
    
    full_transcript = []
    
    #A TextGrid file has "tiers" (like a horizontal track of audio). 
    #we loop through every time interval in the tier to see what was said.
    for tier in tg.tiers:
        for interval in tier:
            #.mark contains the actual text. Let's ignore it if it's empty!
            if interval.mark and interval.mark.strip() != "":
                full_transcript.append(interval.mark.strip())
                
    
    return " ".join(full_transcript)            #stitch all their sentences together with a space in between
#quick test at the bottom
if __name__ == "__main__":
    test_file = "tests/test_audio/day1_consultation01_doctor.TextGrid"  #path to textgrid file of the person
    
    print("Extracting Ground Truth...")
    answer_key = parse_textgrid_transcript(test_file)                      #run parser function for GT
    print(f"Result: {answer_key}")
    print("\nGetting Model Output...")
    audio_file = "tests/test_audio/day1_consultation01_doctor.wav" #path to audio file of the person
    
    model_output = get_transcription(audio_file)                       #run whisper(groq) model made by lucas
    print(f"Model Result: {model_output.text}")

    # ------- Calculating the metrics -------
    
    #Clean the Ground Truth: remove tags like <UNSURE> and <UNIN/> using Regex
    clean_ground_truth = re.sub(r'<[^>]+>', '', answer_key)
    
    #Safety measure to clean up any awkward spaces
    clean_ground_truth = " ".join(clean_ground_truth.split())       
    
    print("\n--- GRADING ---")
    #below you can uncomment if you want to see what the cleaned up version looks like  without the tags
    print(f"Clean Answer Key: {clean_ground_truth}")
    
    #standardize casing and spelling. Model and script were giving different okay and OK
    clean_ground_truth = clean_ground_truth.lower().replace("okay", "ok")
    model_text = model_output.text.lower().replace("okay", "ok")
    
    #Strip out all punctuation so commas/periods don't cause failures
    import string
    for punctuation_mark in string.punctuation:
        clean_ground_truth = clean_ground_truth.replace(punctuation_mark, "")
        model_text = model_text.replace(punctuation_mark, "")

    # Calculate the new, highly-accurate Word Error Rate
    error_rate = jiwer.wer(clean_ground_truth, model_text) #jiwer compares word-by-word, gives back decimal, lower = better, ie 0 = 0 error, 0.2 = 20% error

    #Calculate Word Error Rate
    #WER is (Insertions + Deletions + Substitutions) / Total Words
    
    print(f"Word Error Rate (WER): {error_rate:.2%}")                   #format as 2 decimal
    
