from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from api.endpoints import router as api_router
import os
import celery_worker # <-- Make sure this import is here

# --- Setup Project Directory ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

app = FastAPI(
    title="FHIRGuard Backend API",
    description="A validation engine for FHIR R4 resources.",
    version="1.0.0"
)

# --- 1. Add CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 2. Include Your API Router ---
app.include_router(api_router)

# --- 3. Mount the Static Files Directory ---
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# --- 4. Serve Index.html as the Homepage ---
@app.get("/", response_class=HTMLResponse)
async def read_root():
    """
    Serves the main Index.html file as the homepage.
    """
    html_file_path = os.path.join(STATIC_DIR, "Index.html")
    try:
        with open(html_file_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read(), status_code=200)
    except FileNotFoundError:
        return HTMLResponse(
            content="<h1>Homepage not found</h1><p>Please create an 'Index.html' file in the 'static' directory.</p>",
            status_code=404
        )