import json
import io
import zipfile
import time
import requests 
import numpy as np
from datetime import datetime
from typing import List, Dict, Any
from celery import Celery
from services.validation_service import ValidationService
from core.logger_config import logger

# 1. Initialize
celery_app = Celery(
    'fhirguard_worker',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0'
)

# 2. Initialize ValidationService
try:
    validation_service = ValidationService()
    logger.info("Celery worker has successfully initialized the ValidationService.")
except Exception as e:
    logger.critical(f"FATAL: Celery worker FAILED to initialize ValidationService: {e}")
    validation_service = None

# --- CONSTANTS: FULL-BODY LOINC MAP ---
LOINC_MAP = {
    "8480-6": "sys_bp", "8462-4": "dia_bp",   # Blood Pressure
    "8867-4": "hr",                           # Heart Rate
    "9279-1": "resp",                         # Respiratory Rate
    "8310-5": "temp",                         # Body Temperature
    "2708-6": "o2", "59408-5": "o2",          # Oxygen Saturation (SpO2)
    "39156-5": "bmi",                         # Body Mass Index
    "2339-0": "gluc", "2345-7": "gluc",       # Blood Glucose
    "72514-3": "pain", "38214-3": "pain",     # Pain Score (0-10)
    "9269-2": "gcs"                           # Glasgow Coma Scale
}

# --- HELPER: ID Normalization ---
def normalize_id(ref: str) -> str:
    """
    Strips 'urn:uuid:', 'Patient/', etc. to get the raw ID.
    """
    if not ref: return ""
    return ref.replace("urn:uuid:", "").replace("Patient/", "").strip()

# --- HELPER: NEWS2 Calculator (New Feature) ---
def calculate_news2(v: Dict) -> Dict:
    """
    Calculates National Early Warning Score 2 (NEWS2).
    Returns {score: int, risk: str}
    """
    score = 0
    
    # 1. Respiration Rate
    rr = v.get('resp')
    if rr is not None:
        if rr <= 8 or rr >= 25: score += 3
        elif rr >= 21: score += 2
        elif rr <= 11: score += 1

    # 2. Oxygen Saturation
    o2 = v.get('o2')
    if o2 is not None:
        if o2 <= 91: score += 3
        elif o2 <= 93: score += 2
        elif o2 <= 95: score += 1

    # 3. Systolic Blood Pressure
    sys = v.get('sys_bp')
    if sys is not None:
        if sys <= 90: score += 3
        elif sys <= 100: score += 2
        elif sys <= 110: score += 1
        elif sys >= 220: score += 3 # Clinical addition for Hypertensive Urgency

    # 4. Pulse (Heart Rate)
    hr = v.get('hr')
    if hr is not None:
        if hr <= 40 or hr >= 131: score += 3
        elif hr >= 111: score += 2
        elif hr <= 50 or hr >= 91: score += 1

    # 5. Consciousness (Mapped from GCS)
    gcs = v.get('gcs')
    if gcs is not None:
        if gcs < 15: score += 3 # Any confusion/unresponsiveness is max score

    # 6. Temperature
    temp = v.get('temp')
    if temp is not None:
        if temp <= 35.0: score += 3
        elif temp >= 39.1: score += 2
        elif temp <= 36.0 or temp >= 38.1: score += 1

    # Risk Stratification
    risk = "Low"
    if score >= 7: risk = "CRITICAL (Emergency Response)"
    elif score >= 5: risk = "High (Urgent Review)"
    elif score >= 1: risk = "Medium (Monitor)"

    return {"score": score, "risk": risk}

# --- HELPER: Clinical Rules Engine ---
def check_clinical_rules(patient: Dict, vitals: Dict) -> List[Dict]:
    issues = []
    
    # Rule 1: NEWS2 Critical Alert
    news = calculate_news2(vitals)
    if news['score'] >= 5:
        issues.append({
            "title": f"NEWS2 Score Alert: {news['score']}",
            "severity": "High",
            "explanation": f"Patient deterioration risk is {news['risk']}. Immediate clinical review required."
        })

    # Rule 2: Metabolic/Pain Checks
    if vitals.get('gluc') is not None:
        if vitals['gluc'] < 70:
            issues.append({"title": "Hypoglycemia", "severity": "High", "explanation": f"Blood glucose {vitals['gluc']} mg/dL is dangerously low."})
        elif vitals['gluc'] > 300:
            issues.append({"title": "Hyperglycemic Crisis", "severity": "High", "explanation": f"Blood glucose {vitals['gluc']} mg/dL indicates diabetic ketoacidosis risk."})
        
    if vitals.get('pain') is not None and vitals['pain'] >= 7:
        issues.append({"title": "Severe Pain", "severity": "Medium", "explanation": f"Pain score {vitals['pain']}/10 requires management."})

    return issues

# --- HELPER: AI Narrative Summary ---
def generate_ai_summary(extracted_data: List[Dict], error_count: int) -> str:
    """
    Generates a 4-part report with strict 'No Chat' rules.
    """
    logger.info("[AI AGENT] Starting Narrative Analysis...")

    # 1. Format Data for the AI
    patient_text = ""
    for p in extracted_data[:3]: 
        v = p['vitals']
        news = calculate_news2(v) # Calculate score for the summary
        bp = f"{v.get('sys_bp', '?')}/{v.get('dia_bp', '?')}"
        
        patient_text += (
            f"PATIENT: {p['name']} ({p['age']}y {p.get('gender', 'Unknown')}).\n"
            f"  - RISK: NEWS2 Score {news['score']} ({news['risk']})\n"
            f"  - NEURO: GCS {v.get('gcs', 'N/A')} | Pain {v.get('pain', 'N/A')}\n"
            f"  - VITALS: BP {bp} | HR {v.get('hr', 'N/A')} | RR {v.get('resp', 'N/A')} | O2 {v.get('o2', 'N/A')}%\n"
            f"  - METABOLIC: Gluc {v.get('gluc', 'N/A')} | Temp {v.get('temp', 'N/A')}C | BMI {v.get('bmi', 'N/A')}\n"
            f"  - HISTORY: {', '.join(p['conditions']) or 'None'}\n"
            f"  - MEDS: {', '.join(p['medications']) or 'None'}\n\n"
        )

    # 2. The Strict "No Chat" Prompt
    system_prompt = (
        "You are a Senior Medical Case Manager. Analyze this patient data and generate a report.\n"
        "IMPORTANT: Output ONLY the report content. Do NOT say 'Okay' or 'Here is the report'. Start directly with Section 1.\n\n"
        
        "📖 SECTION 1: PATIENT STORY & HISTORY\n"
        "- Write a professional biography connecting history to current vitals.\n"
        "- Mention the NEWS2 Score and what it implies for their stability.\n\n"

        "🛑 SECTION 2: CLINICAL HANDOFF (Target: Doctors)\n"
        "- SBAR format. Focus on acuity. If vitals are 'N/A', state that data is missing.\n\n"
        
        "💚 SECTION 3: PATIENT EXPLANATION (Target: Family)\n"
        "- Simple 6th-grade English explanation.\n\n"
        
        "💰 SECTION 4: AUDIT & CODING (Target: Billers)\n"
        "- Flag vague diagnoses or missing documentation."
    )

    try:
        logger.info("[AI AGENT] Sending Narrative Prompt to Ollama...")
        
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "alibayram/medgemma:4b", 
                "prompt": f"{system_prompt}\n\nCASE DATA:\n{patient_text}", 
                "stream": False,
                "options": {
                    "num_gpu": 99, 
                    "num_ctx": 4096 
                }
            },
            timeout=120 
        )
        
        if response.status_code == 200:
            logger.info("[AI AGENT] Narrative report generated.")
            raw_text = response.json().get("response", "No text.")
            return raw_text.replace("\n", "<br>") 
        else:
            logger.warning(f"[AI AGENT] Failed with status {response.status_code}.")
            return f"**AI Error:** Status {response.status_code}"

    except Exception as e:
        logger.error(f"[AI AGENT] Connection Error - {e}")
        return "**AI Unavailable:** Ensure Ollama is running."

# --- MAIN TASK ---
@celery_app.task(bind=True, name="tasks.process_uploaded_file")
def process_uploaded_file_task(self, content_bytes: bytes, filename: str, content_type: str) -> Dict[str, Any]:
    start_time = time.time()
    self.update_state(state='PROGRESS', meta={'current': 0, 'total': 100, 'status': 'Initializing Engine...'})

    if validation_service is None:
        return {"summary": {}, "reports": []}

    final_reports = []
    file_size_kb = len(content_bytes) / 1024
    master_bundle = {"resourceType": "Bundle", "type": "collection", "entry": []}
    
    # 1. Parse File
    self.update_state(state='PROGRESS', meta={'current': 10, 'total': 100, 'status': 'Parsing File Structure...'})
    try:
        content_str = ""
        try: content_str = content_bytes.decode("utf-8")
        except: pass 

        if content_type == 'application/zip' or filename.endswith('.zip'):
            with io.BytesIO(content_bytes) as zip_buffer:
                with zipfile.ZipFile(zip_buffer, 'r') as zip_ref:
                    for name in zip_ref.namelist():
                        if (name.endswith('.json') or name.endswith('.ndjson')) and not name.startswith('__'):
                            with zip_ref.open(name) as inner_file:
                                try:
                                    data = json.loads(inner_file.read())
                                    if data.get("resourceType") == "Bundle":
                                        master_bundle["entry"].extend(data.get("entry", []))
                                    else:
                                        master_bundle["entry"].append({"resource": data})
                                except: pass
        else:
            try:
                data = json.loads(content_str)
                if data.get("resourceType") == "Bundle":
                    master_bundle = data
                else:
                    master_bundle["entry"].append({"resource": data})
            except json.JSONDecodeError:
                lines = content_str.strip().split("\n")
                for line in lines:
                    if line.strip():
                        try: master_bundle["entry"].append({"resource": json.loads(line)})
                        except: pass

        # 2. Batch Validate (Java)
        self.update_state(state='PROGRESS', meta={'current': 30, 'total': 100, 'status': 'Running Java Validator...'})
        if master_bundle["entry"]:
            logger.info(f"Sending {len(master_bundle['entry'])} resources to Java Validator...")
            bundle_issues = validation_service._run_hl7_profile_validation(master_bundle)
            if bundle_issues:
                final_reports.append({"resource": f"{filename} (Batch Check)", "issues": bundle_issues})

        # 3. Full-Body Analysis (ML + Rules + NEWS2)
        self.update_state(state='PROGRESS', meta={'current': 60, 'total': 100, 'status': 'Running 11-Point Vitals Analysis...'})

        # Initialize Patients Map with Empty Vitals (No Defaults!)
        patients_map = {}

        # Pass A: Extract Patients
        for entry in master_bundle["entry"]:
            res = entry.get("resource", {})
            if res.get("resourceType") == "Patient":
                pid = normalize_id(res.get("id")) # Normalize ID
                try:
                    bd = res.get("birthDate", "")
                    age = datetime.today().year - datetime.strptime(bd, "%Y-%m-%d").year
                except: age = 30

                patients_map[pid] = {
                    "name": res.get("name", [{}])[0].get("family", "Unknown"), 
                    "age": age, 
                    "gender": res.get("gender", "Unknown"),
                    # Initialize vitals as None so we know if they are missing
                    "vitals": {k: None for k in ['sys_bp', 'dia_bp', 'hr', 'resp', 'temp', 'o2', 'bmi', 'gluc', 'pain', 'gcs']}, 
                    "conditions": [],
                    "medications": []
                }

        # Pass B: Extract Context (Vitals, Meds, Conds)
        for entry in master_bundle["entry"]:
            res = entry.get("resource", {})
            rtype = res.get("resourceType")
            
            # Link based on Subject Reference
            subj_ref = normalize_id(res.get("subject", {}).get("reference", ""))
            if subj_ref not in patients_map: continue
            
            p = patients_map[subj_ref]

            if rtype == "Condition":
                p["conditions"].append(res.get("code", {}).get("text", "Unknown"))
            elif rtype == "MedicationRequest":
                p["medications"].append(res.get("medicationCodeableConcept", {}).get("text", "Unknown"))
            elif rtype == "Observation":
                code = res.get("code", {}).get("coding", [{}])[0].get("code")
                val = res.get("valueQuantity", {}).get("value")
                if code in LOINC_MAP and val is not None:
                    p["vitals"][LOINC_MAP[code]] = val

        # Pass C: Analyze
        for pid, p in patients_map.items():
            v = p['vitals']
            
            # 1. Check Clinical Rules & NEWS2 (Only if data exists)
            for issue in check_clinical_rules(p, v):
                final_reports.append({
                    "resource": f"Patient/{pid}", 
                    "issues": [{"severity": issue['severity'], "title": issue['title'], "explanation": issue['explanation']}]
                })

            # 2. Check ML Anomaly (Only if we have CORE vitals)
            # We need at least BP and HR to run a meaningful prediction
            if v['sys_bp'] is not None and v['hr'] is not None:
                # Fill remaining Nones with safe defaults just for the ML vector (not the report)
                safe_v = {k: (val if val is not None else 0) for k, val in v.items()}
                # Fallback defaults for zeros where 0 is invalid (like BP)
                if safe_v['sys_bp'] == 0: safe_v['sys_bp'] = 120
                if safe_v['dia_bp'] == 0: safe_v['dia_bp'] = 80
                
                vector = [
                    p['age'], safe_v['sys_bp'], safe_v['dia_bp'], 
                    safe_v['hr'], safe_v['resp'], safe_v['temp'], 
                    safe_v['o2'], safe_v['bmi'], safe_v['gluc'], 
                    safe_v['pain'], safe_v['gcs']
                ]
                
                if validation_service.anomaly_model and validation_service.anomaly_model.predict([vector])[0] == -1:
                     final_reports.append({
                         "resource": f"Patient/{pid}", 
                         "issues": [{
                             "severity": "High", 
                             "title": "Complex Clinical Anomaly", 
                             "explanation": "Full-body vital signs pattern is statistically abnormal for this age group."
                         }]
                     })

    except Exception as e:
        logger.error(f"Error: {e}")
        final_reports.append({"resource": "System", "issues": [{"id": 999, "title": "Error", "explanation": str(e)}]})

    # 4. Generate Summary
    self.update_state(state='PROGRESS', meta={'current': 80, 'total': 100, 'status': 'Generating AI Narrative...'})
    
    ai_narrative = "No patient data found."
    if patients_map:
        ai_narrative = generate_ai_summary(list(patients_map.values()), len(final_reports))

    processing_time = round(time.time() - start_time, 2)
    
    summary = {
        "filename": filename,
        "file_size": f"{file_size_kb:.2f} KB",
        "total_resources": len(master_bundle["entry"]),
        "processing_time": f"{processing_time}s",
        "ai_narrative": ai_narrative,
        "timestamp": time.strftime("%H:%M:%S")
    }
    
    return {"summary": summary, "reports": final_reports}