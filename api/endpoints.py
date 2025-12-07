from fastapi import APIRouter, UploadFile, File, HTTPException
from celery.result import AsyncResult
from celery_worker import process_uploaded_file_task

router = APIRouter()

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Receives file, starts Async task, returns Task ID immediately.
    """
    # 1. Basic File Type Check
    if not file.filename.endswith(('.json', '.ndjson', '.zip')):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload .json, .ndjson, or .zip")
    
    # 2. Read content
    content = await file.read()
    
    # 3. Start the Celery task (Async)
    # .delay() kicks off the task in the background and returns immediately
    task = process_uploaded_file_task.delay(content, file.filename, file.content_type)
    
    # 4. Return the Ticket Number (Task ID)
    return {"task_id": task.id, "message": "File uploaded. Processing started."}

@router.get("/status/{task_id}")
async def get_status(task_id: str):
    """
    Checks the status of a specific task.
    """
    task_result = AsyncResult(task_id)
    
    # CASE 1: Task is waiting in queue
    if task_result.state == 'PENDING':
        return {
            "state": "PENDING", 
            "current": 0, 
            "total": 100, 
            "status": "Pending in queue..."
        }
    
    # CASE 2: Task is currently running (Reporting Progress)
    elif task_result.state == 'PROGRESS':
        return {
            "state": "PROGRESS",
            "current": task_result.info.get('current', 0),
            "total": task_result.info.get('total', 100),
            "status": task_result.info.get('status', "Processing...")
        }
    
    # CASE 3: Task Finished Successfully
    elif task_result.state == 'SUCCESS':
        return {
            "state": "SUCCESS",
            "current": 100,
            "total": 100, 
            "status": "Complete",
            "result": task_result.result
        }
    
    # CASE 4: Task Crashed
    else:
        return {
            "state": task_result.state, 
            "current": 100, 
            "total": 100, 
            "status": "Failed", 
            "error": str(task_result.info)
        }