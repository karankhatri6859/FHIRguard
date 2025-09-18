import json
import io
import zipfile
from fastapi import APIRouter, UploadFile, File, HTTPException
from services.validation_service import ValidationService
from core.logger_config import logger
from typing import Dict, Any

router = APIRouter()
validation_service = ValidationService()

def process_fhir_resource(fhir_data: Dict[str, Any], source_name: str) -> list:
    """
    Helper function to process a single resource or unpack a Bundle.
    It returns a list of validation reports.
    """
    all_reports = []
    
    # Check if the resource is a Bundle
    if fhir_data.get("resourceType") == "Bundle":
        logger.info(f"Processing a Bundle from '{source_name}'.")
        # Loop through each entry in the Bundle
        for i, entry in enumerate(fhir_data.get("entry", [])):
            resource = entry.get("resource")
            if resource:
                report = validation_service.validate_and_analyze(resource)
                resource_id = resource.get("id", f"entry-{i+1}")
                resource_type = resource.get("resourceType", "Unknown")
                all_reports.append({"resource": f"{source_name} -> {resource_type}/{resource_id}", "issues": report})
    else:
        # Process as a single resource
        report = validation_service.validate_and_analyze(fhir_data)
        all_reports.append({"resource": source_name, "issues": report})
        
    return all_reports


@router.post("/validate-fhir")
async def validate_fhir(file: UploadFile = File(...)):
    logger.info(f"Received request to validate file: {file.filename} (Content-Type: {file.content_type})")
    final_reports = []
    
    if file.filename.endswith('.zip'):
        try:
            zip_content = await file.read()
            with zipfile.ZipFile(io.BytesIO(zip_content), 'r') as z:
                # Look for both .json and .ndjson files
                files_to_process = [f for f in z.infolist() if f.filename.endswith(('.json', '.ndjson')) and not f.is_dir()]
                logger.info(f"Processing ZIP archive containing {len(files_to_process)} files.")

                for file_info in files_to_process:
                    with z.open(file_info) as fhir_file:
                        content_str = fhir_file.read().decode('utf-8')
                        source_name = f"File: {file_info.filename}"

                        # Handle NDJSON files from within the zip
                        if file_info.filename.endswith('.ndjson'):
                            logger.info(f"Processing NDJSON file from zip: {file_info.filename}")
                            lines = content_str.strip().split("\n")
                            for line_number, line in enumerate(lines):
                                if not line.strip(): continue
                                try:
                                    fhir_data = json.loads(line.strip())
                                    report = validation_service.validate_and_analyze(fhir_data)
                                    final_reports.append({"resource": f"{source_name} -> Line {line_number + 1}", "issues": report})
                                except json.JSONDecodeError as e:
                                    logger.error(f"Invalid JSON in '{file_info.filename}' on line {line_number + 1}: {e.msg}")
                                    final_reports.append({
                                        "resource": f"{source_name} -> Line {line_number + 1}",
                                        "issues": [{"id": 99, "title": "Invalid JSON Object", "explanation": f"Error: {e.msg}"}]
                                    })
                        # Handle regular JSON files from within the zip
                        else:
                            try:
                                fhir_data = json.loads(content_str)
                                final_reports.extend(process_fhir_resource(fhir_data, source_name))
                            except json.JSONDecodeError as e:
                                logger.error(f"Invalid JSON in ZIP file '{file_info.filename}': {e.msg}")
                                final_reports.append({
                                    "resource": source_name,
                                    "issues": [{"id": 99, "title": "Invalid JSON in ZIP", "explanation": f"Error: {e.msg}"}]
                                })
            return {"reports": final_reports}
        except Exception as e:
            logger.critical(f"Failed to process ZIP file '{file.filename}': {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to process ZIP file: {e}")
    else:
        # This logic for standalone files remains the same
        content_bytes = await file.read()
        content_str = content_bytes.decode("utf-8")
        try:
            fhir_data = json.loads(content_str)
            final_reports.extend(process_fhir_resource(fhir_data, file.filename))
            return {"reports": final_reports}
        except json.JSONDecodeError:
            logger.info("Processing as NDJSON (newline-delimited JSON).")
            lines = content_str.strip().split("\n")
            for line_number, line in enumerate(lines):
                if not line.strip(): continue
                try:
                    fhir_data = json.loads(line.strip())
                    report = validation_service.validate_and_analyze(fhir_data)
                    final_reports.append({"resource": f"Line {line_number + 1}", "issues": report})
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON on line {line_number + 1}: {e.msg}")
                    final_reports.append({
                        "resource": f"Line {line_number + 1}",
                        "issues": [{"id": 99, "title": "Invalid JSON Object", "explanation": f"Error: {e.msg}"}]
                    })
            return {"reports": final_reports}

