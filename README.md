FHIRGuard: Advanced Healthcare Data Validation & Clinical Anomaly Detection

FHIRGuard is an enterprise-grade validation engine designed to ensure the structural integrity, semantic correctness, and clinical plausibility of healthcare data. Unlike standard validators, FHIRGuard employs a multi-layered defense strategy that combines official HL7 Java validation, Machine Learning for physiological anomaly detection, and Generative AI for automated clinical summaries.

🧠 System Architecture

The system uses a non-blocking, microservices-inspired architecture to handle complex validation tasks without compromising user experience.

Frontend: A responsive Dashboard (Index.html) for file uploads and real-time visualization.

API Gateway: FastAPI handles requests and offloads heavy processing to a task queue.

Task Engine: Celery & Redis manage asynchronous validation pipelines.

Validation Core (The 4 Layers):

Layer 1 (Syntax): JSON Schema validation.

Layer 2 (Semantics): Official HL7 Java Validator (with US Core & IPS profiles).

Layer 3 (Clinical Logic): NEWS2 (National Early Warning Score) calculation and hard-coded medical rules.

Layer 4 (AI & ML):

Isolation Forest for statistical outlier detection in vitals.

MedGemma LLM (Ollama) for generating human-readable clinical narratives.

🛠️ Prerequisites

Before running the system, ensure you have the following installed:

Python 3.11+

Java JDK 11+ (Required for the Validator Service)

Redis Server (Message Broker for Celery)

Ollama (For the AI Agent)

Required Model: alibayram/medgemma:4b

⚙️ Installation Guide

1. Clone the Repository

git clone [https://github.com/karankhatri6859/FHIRguard.git](https://github.com/karankhatri6859/FHIRguard.git)
cd FHIRguard


2. Set Up Virtual Environment

# Windows
python -m venv venv
venv\Scripts\activate

# Mac/Linux
python3 -m venv venv
source venv/bin/activate


3. Install Python Dependencies

pip install -r requirements.txt


🏗️ Critical Setup: Restoring Missing Assets

To keep the repository lightweight, large models and binaries are not tracked in Git. You must generate or download them manually.

Step A: Generate the ML Model

Run the training script to generate the anomaly detection model (comprehensive_model.joblib).

python train_comprehensive.py


Step B: Prepare the Java Validator

Download the HL7 Validator Wrapper JAR.

Place it inside the validator/ folder.

Rename it to: validator-wrapper.jar.

Step C: Pull the AI Model

Ensure Ollama is installed, then pull the specific medical model used by the worker:

ollama pull alibayram/medgemma:4b


🚀 Running the System (The 5-Terminal Setup)

Since this is a distributed system, you need to run the components in separate terminals.

Terminal 1: Redis Server

Start the message broker.

redis-server


Terminal 2: Java Validation Server

Start the validation engine with the required Implementation Guides (IGs).

cd validator
java -Xmx6g -jar validator-wrapper.jar -port 8082 -ig hl7.fhir.us.core -ig hl7.fhir.uv.ips -ig hl7.fhir.uv.sdc -ig hl7.cda.us.ccda -ig hl7.fhir.us.carin-bb


Note: -Xmx6g allocates 6GB of RAM to Java. Ensure your machine has enough memory.

Terminal 3: AI Inference Engine (Ollama)

Start the local LLM server.

ollama serve


Terminal 4: Celery Worker

Start the background task processor.

# Windows
celery -A celery_worker worker --loglevel=info --pool=solo

# Mac/Linux
celery -A celery_worker worker --loglevel=info


Terminal 5: Main Backend API

Start the FastAPI server using the runner script.

python run.py


The application will be available at https://www.google.com/search?q=http://127.0.0.1:8000

🕵️‍♂️ Usage & Features

1. The Dashboard

Open https://www.google.com/search?q=http://127.0.0.1:8000 in your browser.

Drag & Drop: Upload FHIR JSON bundles (or ZIP files containing them).

Real-time Progress: Watch the validation steps (Parsing -> Java -> ML -> AI).

Interactive Report:

AI Narrative: A generated patient story and clinical handoff (SBAR format).

Visual Charts: Breakdown of error severity and resource types.

Issue Cards: Detailed error logs categorized by their source (Java Validator vs. ML Anomaly).

2. Diagnostic Check

If something isn't working, run the self-diagnostic tool to check ports and files:

python check_env.py


📂 Project Structure

Folder/File

Description

api/

FastAPI route definitions and endpoints.

core/

Configuration files (Logging, Settings).

models/

Logic for the Isolation Forest ML model.

services/

Connectors for the Java Validator and AI Agent.

static/

Frontend assets (Index.html, CSS, JS).

validator/

Directory for the Java JAR file.

celery_worker.py

The main async processing logic and NEWS2 rules.

train_comprehensive.py

Script to train and save the .joblib model.

📜 License & Credits

Developed as a Final Year B.Tech Project.

Author: Karan Khatri

Frameworks: FastAPI, Celery, Scikit-Learn

Standards: HL7 FHIR R4