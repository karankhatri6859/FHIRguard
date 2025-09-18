import sys
import os
import uvicorn

# Add the project root to the Python path to allow for module imports
sys.path.insert(0, os.path.dirname(__file__))

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)