import os
import joblib
import json
import requests
from typing import List, Dict, Any
from core.logger_config import logger

class ValidationService:
    def __init__(self):
        # Determine the project root directory
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # --- 1. LOAD ML MODEL (Phase 2 Upgrade) ---
        # We try to load the new "Full-Body" model first
        new_model_path = os.path.join(BASE_DIR, "comprehensive_model.joblib")
        old_model_path = os.path.join(BASE_DIR, "isolation_forest_model.joblib")
        
        if os.path.exists(new_model_path):
            try:
                self.anomaly_model = joblib.load(new_model_path)
                # Clean log (No Emojis)
                logger.info(f"[SUCCESS] Loaded Comprehensive ML Model from {new_model_path}")
            except Exception as e:
                logger.error(f"[ERROR] Failed to load new model: {e}")
                self.anomaly_model = None
        
        elif os.path.exists(old_model_path):
            try:
                self.anomaly_model = joblib.load(old_model_path)
                logger.warning(f"[WARNING] Comprehensive model not found. Loaded Basic Model from {old_model_path}")
            except Exception as e:
                logger.error(f"[ERROR] Failed to load basic model: {e}")
                self.anomaly_model = None
        
        else:
            logger.warning("[WARNING] No ML models found. Anomaly detection features will be disabled.")
            self.anomaly_model = None

        # --- 2. LOAD JSON SCHEMA (Layer 1) ---
        self.schema_path = os.path.join(BASE_DIR, "schemas", "fhir.schema.json")
        if os.path.exists(self.schema_path):
            try:
                with open(self.schema_path, 'r', encoding='utf-8') as f:
                    self.main_schema = json.load(f)
                logger.info(f"[SUCCESS] Loaded main FHIR R4 schema from: {self.schema_path}")
            except Exception as e:
                logger.error(f"[ERROR] Failed to load main FHIR schema: {e}")
                self.main_schema = None
        else:
            logger.error(f"[ERROR] Schema file not found: {self.schema_path}")
            self.main_schema = None

    def _get_fhir_schema(self, resource_type: str):
        """Returns the JSON schema for a specific resource type."""
        if not self.main_schema:
            raise Exception("Main FHIR schema is not loaded.")
            
        return {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "definitions": self.main_schema.get("definitions", {}),
            "$ref": f"#/definitions/{resource_type}"
        }

    def _run_hl7_profile_validation(self, bundle_data: dict) -> list:
        """
        Layer 2: Sends data to the local Java Validator.
        INCLUDES THE REQUIRED WRAPPER TO FIX 500 ERROR.
        """
        validator_url = "http://localhost:8082/validate"
        
        # --- THE FIX: Restored the wrapper structure ---
        payload = {
            "cliContext": {
                "sv": "4.0.1", 
                "targetVer": "4.0.1",
                "displayWarnings": True
            },
            "filesToValidate": [
                {
                    "fileName": "resource.json",
                    "fileContent": json.dumps(bundle_data)
                }
            ]
        }
        
        try:
            response = requests.post(
                validator_url, 
                json=payload, 
                headers={"Content-Type": "application/json"}, 
                timeout=300
            )
            
            if response.status_code == 200:
                return self._parse_validator_output(response.text)
            else:
                # Log the raw error from Java for debugging
                logger.error(f"[ERROR] Local validator returned status {response.status_code}: {response.text[:200]}")
                return [{"severity": "High", "title": "Validator Server Error", "explanation": f"Java Server returned {response.status_code}. Check Java terminal for NPE."}]

        except requests.exceptions.ConnectionError:
            logger.error("[ERROR] Could not connect to Java Validator at http://localhost:8082.")
            return [{"severity": "High", "title": "Validator Offline", "explanation": "The Java validation engine is not reachable."}]
        except Exception as e:
            logger.error(f"[ERROR] Validation request failed: {e}")
            return [{"severity": "Medium", "title": "System Error", "explanation": str(e)}]

    def _parse_validator_output(self, output_json: str) -> list:
        """
        Parses the OperationOutcome returned by the Java Validator.
        """
        issues = []
        try:
            response_data = json.loads(output_json)
            # Handle "outcomes" wrapper if present
            outcomes = response_data.get("outcomes", [response_data])
            
            for outcome in outcomes:
                for issue in outcome.get("issue", []):
                    severity = issue.get("severity", "error").capitalize()
                    
                    # Skip purely informational success messages
                    if severity in ["Information", "Warning"] and "validation success" in issue.get("diagnostics", "").lower():
                        continue
                        
                    issues.append({
                        "severity": "High" if severity in ["Error", "Fatal"] else "Low",
                        "title": f"Profile Violation ({severity})",
                        "explanation": issue.get("diagnostics", "No details provided.")
                    })
        except json.JSONDecodeError:
            logger.error("[ERROR] Failed to parse Java Validator response as JSON.")
        
        return issues