import sys
import os

#ensure we can import directly from the src folder
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from python_venv.pipeline import _embed, _retrieve

def evaluate_retrieval(k=5):
    #manually verfied ground truth dataset
    ground_truth = {
        "was the patient vomiting": 31,
        "are they still vomiting?": 32,
        "did they lose appetite": 37,
        "are they on other medications": 61,
        "how long did they say to come back after if not gotten better?": 213,
        "how many tablets per day": 208,
        "is there apossibility of a stool sample?": 215,
        "did the pateint feel shaky?": 122
    }
    
    queries = list(ground_truth.keys())
    print(f"\n--- Grading Information Retrieval (Precision@{k}, Recall@{k}) ---\n")
    
    #3 distinct views:
    rubric_sections = [
        {"name": "a) Overall", "speaker_filter": None},
        {"name": "b) Patient-only retrieval", "speaker_filter": "PATIENT"},
        {"name": "c) Clinician-only retrieval", "speaker_filter": "CLINICIAN"}
    ]
    
    for section in rubric_sections:
        print(f"Testing {section['name']}...")
        total_precision = 0.0
        total_recall = 0.0
        
        for query, target_row_id in ground_truth.items():
            query_vector = _embed.get_embeddings([query])[0]    #others code to mathematically embed question
            
            #Query supabase database seamlessly using Backend logic
            retrieved_rows = _retrieve.get_retrieval(query_vector=query_vector, speaker=section["speaker_filter"], n=k) 
            retrieved_ids = [row["id"] for row in retrieved_rows] #extract just the IDs from the results
            
            # 3. Grade the Retrieval Math!
            if target_row_id in retrieved_ids:
                total_recall += 1.0       # Found 1 out of 1 targets (100% Recall for this query)
                total_precision += 1/k    # Found 1 target out of K returned rows (e.g. 20% Precision)
            else:
                total_recall += 0.0       # Utter failure (0%)
                total_precision += 0.0    # Utter failure (0%)
                
        #average the scores over all q
        avg_precision = total_precision / len(queries)
        avg_recall = total_recall / len(queries)
        
        print(f"   Precision@{k}: {avg_precision:.2%}")
        print(f"   Recall@{k}:    {avg_recall:.2%}")
        print("-" * 45)

if __name__ == "__main__":
    #grading using Top 5 results
    evaluate_retrieval(k=5)
