FHIRGuard: Advanced Healthcare Data Validation & Clinical Anomaly Detection

Enterprise-grade validation engine ensuring structural integrity, semantic correctness, and clinical plausibility of healthcare data.

🧠 System Architecture

FHIRGuard employs a multi-layered defense strategy combining official HL7 Java validation, Machine Learning for anomaly detection, and Generative AI for automated clinical summaries.

graph TD
    Client[User / Dashboard] -->|Upload Bundle| API[FastAPI Gateway]
    API -->|Async Task| Redis[Redis Queue]
    Redis -->|Process| Worker[Celery Worker]
    
    subgraph "Validation Core"
    Worker -->|Layer 1| Schema[JSON Schema]
    Worker -->|Layer 2| Java[HL7 Java Validator]
    Worker -->|Layer 3| ML[Isolation Forest (ML)]
    Worker -->|Layer 4| AI[Ollama / MedGemma]
    end
    
    ML -->|Detect| Anomalies[Clinical Outliers]
    AI -->|Generate| Narrative[Clinical Summary]


🚀 Quick Start Guide

1. Prerequisites

Ensure you have the following installed:

Python 3.11+

Java JDK 11+ (Critical for the Validator)

Redis Server

Ollama (Pull model: ollama pull alibayram/medgemma:4b)

2. Installation

# Clone the repository
git clone [https://github.com/karankhatri6859/FHIRguard.git](https://github.com/karankhatri6859/FHIRguard.git)
cd FHIRguard

# Setup Virtual Environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install Dependencies
pip install -r requirements.txt


3. Restore Missing Assets

Large files are excluded from the repository. You must generate or download them:

Generate ML Model: python train_comprehensive.py

Download Validator: Place validator-wrapper.jar in the validator/ folder.

🖥️ Running the Distributed System

This system requires 5 separate terminals to run all microservices.

Terminal

Component

Command

1

Redis

redis-server

2

Java Validator

java -Xmx6g -jar validator/validator-wrapper.jar -port 8082 -ig hl7.fhir.us.core -ig hl7.fhir.uv.ips -ig hl7.fhir.uv.sdc -ig hl7.cda.us.ccda -ig hl7.fhir.us.carin-bb

3

AI Engine

ollama serve

4

Celery Worker

celery -A celery_worker worker --loglevel=info --pool=solo

5

API Server

python run.py

Note: The Java Validator command requires -ig flags for specific Implementation Guides (US Core, IPS, etc.). See full command in validator/README.txt if available.

🕵️‍♂️ Features & Capabilities

1. The Dashboard

Access at: http://127.0.0.1:8000

Drag & Drop UI: Upload .json, .ndjson, or .zip files.

Real-time Status: Live progress tracking via WebSockets/Polling.

2. AI Clinical Narrative

The system uses MedGemma-4b to generate a structured report:

Patient Story: Summarizes history and vitals.

Clinical Handoff: SBAR format for doctors.

Audit & Coding: Flags for billing and compliance.

3. Validation Layers

✅ Syntactic: JSON Schema validation.

✅ Semantic: Official HL7 Java Validator (Profile conformance).

✅ Clinical: NEWS2 Score calculation & Rule-based alerts.

✅ Statistical: ML Isolation Forest for detecting vitals anomalies.

📂 Project Structure

FHIRGuard/
├── api/                 # FastAPI Endpoints
├── core/                # Config & Logging
├── models/              # ML Model Logic
├── services/            # Connectors (Java, AI)
├── static/              # Frontend (HTML/JS/CSS)
├── validator/           # Java Validator JAR
├── celery_worker.py     # Async Task Logic
├── train_comprehensive.py # ML Training Script
└── main.py              # App Entry Point


📜 License

Developed by Karan Khatri