from typing import List, Dict, Any
import numpy as np

# NEW: Import the FHIR resources factory and validation error
from fhir.resources.fhirabstractmodel import FHIRAbstractModel
from fhir.resources.core.exceptions import FHIRValidationError

from models.anomaly_model import get_anomaly_model
from core.logger_config import logger

class ValidationService:
    def __init__(self):
        """
        Initializes the service by loading the anomaly model.
        The fhir.resources library handles schema definitions automatically.
        """
        self.anomaly_model = get_anomaly_model()
        logger.info("ValidationService initialized for FHIR-aware validation.")
        
    def validate_and_analyze(self, fhir_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Validates a single FHIR resource by attempting to parse it into a
        fhir.resources object. It also runs custom anomaly detection.
        """
        issues = []
        resource_type = fhir_data.get("resourceType")

        if not resource_type:
            issues.append({
                "id": 101, "title": "Missing 'resourceType' field", "type": "Structural",
                "severity": "High", "explanation": "The JSON object is missing the mandatory 'resourceType' field.",
            })
            return issues

        # --- NEW: FHIR-aware Structural Validation ---
        try:
            # This is the new validation step. If this line succeeds, the resource is valid.
            FHIRAbstractModel.from_resource(fhir_data)
            logger.info(f"Successfully validated resource type: '{resource_type}'")
        except FHIRValidationError as e:
            logger.warning(f"FHIR validation failed for '{resource_type}': {e}")
            # The error object 'e' contains details about what went wrong.
            for error in e.errors:
                issues.append({
                    "id": 1, "title": "Structural Validation Error", "type": "Structural",
                    "severity": "High", "explanation": f"Validation failed for '{resource_type}': {error['msg']} at path '{'.'.join(error['loc'])}'",
                })
            # Return early if there are structural errors
            return issues

        # --- Anomaly Detection (Existing Logic) ---
        if resource_type == "Observation" and fhir_data.get("code", {}).get("coding", [{}])[0].get("code") == "8480-6":
            value_quantity = fhir_data.get("valueQuantity", {}).get("value")
            if value_quantity is not None:
                prediction = self.anomaly_model.predict(np.array([[value_quantity]]))
                if prediction == -1:
                    issues.append({
                        "id": 2, "title": "Abnormal Blood Pressure Detected", "type": "Contextual Anomaly",
                        "severity": "High", "explanation": f"The systolic blood pressure value of '{value_quantity}' is a statistical outlier.",
                    })

        # --- Self-Healing Logic (Existing Logic) ---
        if resource_type == "Patient" and isinstance(fhir_data.get("deceasedBoolean"), str):
            issues.append({
                "id": 201, "title": "Invalid Data Type", "type": "Data Integrity",
                "severity": "Medium", "explanation": "The field 'deceasedBoolean' is a string but should be a boolean (true/false).",
                "isRepairable": True,
                "repair": {
                    "op": "replace", "path": "/deceasedBoolean",
                    "value": bool(fhir_data.get("deceasedBoolean").lower() == 'true')
                }
            })
            
        return issues