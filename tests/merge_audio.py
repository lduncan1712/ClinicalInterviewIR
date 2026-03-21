from pydub import AudioSegment
import os

def mix_audio(patient_path, doctor_path, output_path):
    print("\n[1] Loading Patient Audio...")
    patient = AudioSegment.from_wav(patient_path)
    
    print("[2] Loading Clinician Audio...")
    doctor = AudioSegment.from_wav(doctor_path)
    
    print("[3] Overlaying (Mixing) Both Audio Tracks together natively...")
    # This precisely overlays the two files on top of each other
    mixed = patient.overlay(doctor)
    
    print(f"[4] Exporting Master Mixed Audio file to: {output_path} ...")
    mixed.export(output_path, format="wav")
    print("\nSUCCESS! Your completely merged master file is ready for Section 6!")

if __name__ == "__main__":
    p_path = "tests/test_audio/day1_consultation01_patient.wav"
    d_path = "tests/test_audio/day1_consultation01_doctor.wav"
    out_path = "tests/test_audio/day1_consultation01_mixed.wav"
    
    try:
        mix_audio(p_path, d_path, out_path)
    except Exception as e:
        print("Error during audio merge. Are the file paths completely correct?", e)
