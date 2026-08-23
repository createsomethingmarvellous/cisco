import csv
import datetime
import os

LOG_FILE = "logs/responsible_ai_log.csv"

def log_review(case_id, ai_diagnosis, human_decision, human_correction):
    """Module 6: Human Review - Records AI responses and human decisions."""
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    
    file_exists = os.path.exists(LOG_FILE)
    
    with open(LOG_FILE, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['case_id', 'timestamp', 'ai_root_cause', 'human_decision', 'human_correction'])
        
        # We assume ai_diagnosis is a dict containing root_cause
        root_cause = ai_diagnosis.get('root_cause', 'N/A') if isinstance(ai_diagnosis, dict) else 'N/A'
        
        writer.writerow([
            case_id,
            datetime.datetime.now().isoformat(),
            root_cause,
            human_decision,
            human_correction
        ])
    return True
