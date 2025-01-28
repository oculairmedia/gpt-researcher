import json
import os
import time
from typing import Dict, List

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, File, UploadFile, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from backend.server.websocket_manager import WebSocketManager
from backend.server.server_utils import (
    get_config_dict,
    update_environment_variables, handle_file_upload, handle_file_deletion,
    execute_multi_agents, handle_websocket_communication
)


from gpt_researcher.utils.logging_config import setup_research_logging

import logging

# Get logger instance
logger = logging.getLogger(__name__)

# Don't override parent logger settings
logger.propagate = True

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()  # Only log to console
    ]
)

# Models


class ResearchRequest(BaseModel):
    task: str
    report_type: str
    agent: str


class ConfigRequest(BaseModel):
    ANTHROPIC_API_KEY: str
    TAVILY_API_KEY: str
    LANGCHAIN_TRACING_V2: str
    LANGCHAIN_API_KEY: str
    OPENAI_API_KEY: str
    DOC_PATH: str
    RETRIEVER: str
    GOOGLE_API_KEY: str = ''
    GOOGLE_CX_KEY: str = ''
    BING_API_KEY: str = ''
    SEARCHAPI_API_KEY: str = ''
    SERPAPI_API_KEY: str = ''
    SERPER_API_KEY: str = ''
    SEARX_URL: str = ''
    XAI_API_KEY: str
    DEEPSEEK_API_KEY: str


# App initialization
app = FastAPI()

# Static files and templates
app.mount("/site", StaticFiles(directory="./frontend"), name="site")
app.mount("/static", StaticFiles(directory="./frontend/static"), name="static")
templates = Jinja2Templates(directory="./frontend")

# WebSocket manager
manager = WebSocketManager()

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Constants
DOC_PATH = os.getenv("DOC_PATH", "./my-docs")

# Startup event


@app.on_event("startup")
def startup_event():
    os.makedirs("outputs", exist_ok=True)
    app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")
    os.makedirs(DOC_PATH, exist_ok=True)
    

# Routes


@app.get("/")
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "report": None})


@app.get("/files/")
async def list_files():
    files = os.listdir(DOC_PATH)
    print(f"Files in {DOC_PATH}: {files}")
    return {"files": files}


@app.post("/api/multi_agents")
async def run_multi_agents(request: Request):
    try:
        data = await request.json()
        task = data.get("task")
        report_type = data.get("report_type", "research_report")
        
        if not task:
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": "Task is required"}
            )
        
        # Return immediately with a task ID
        task_id = f"task_{int(time.time())}"
        
        # Start research in background
        class ResearchRequest:
            def __init__(self, task, report_type):
                self.task = task
                self.report_type = report_type
        
        req = ResearchRequest(task, report_type)
        
        # Return task accepted response
        return JSONResponse(
            status_code=202,
            content={
                "status": "accepted",
                "message": "Research task started",
                "task_id": task_id,
                "task": task
            }
        )
        
    except Exception as e:
        logger.error(f"Error in run_multi_agents: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )


@app.get("/api/tasks/{task_id}")
async def get_task_status(task_id: str):
    try:
        # Check if task output files exist
        sanitized_filename = task_id.replace("task_", "")
        output_dir = "outputs"
        
        # Look for files with the task ID prefix
        files = []
        if os.path.exists(output_dir):
            files = [f for f in os.listdir(output_dir) if f.startswith(sanitized_filename)]
        
        if not files:
            return JSONResponse(
                status_code=404,
                content={
                    "status": "not_found",
                    "message": "Task not found or still processing"
                }
            )
        
        # Return file paths
        file_paths = {
            os.path.splitext(f)[1][1:]: os.path.join(output_dir, f)
            for f in files
        }
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "completed",
                "files": file_paths
            }
        )
        
    except Exception as e:
        logger.error(f"Error in get_task_status: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )

@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    return await handle_file_upload(file, DOC_PATH)


@app.delete("/files/{filename}")
async def delete_file(filename: str):
    return await handle_file_deletion(filename, DOC_PATH)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        await handle_websocket_communication(websocket, manager)
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
