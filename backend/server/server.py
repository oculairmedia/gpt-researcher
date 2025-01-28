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

from backend.utils import write_md_to_pdf, write_md_to_word, write_text_to_md

async def generate_report_files(report: str, filename: str) -> Dict[str, str]:
    """Generate PDF, DOCX, and MD files from the report"""
    pdf_path = await write_md_to_pdf(report, filename)
    docx_path = await write_md_to_word(report, filename)
    md_path = await write_text_to_md(report, filename)
    return {"pdf": pdf_path, "docx": docx_path, "md": md_path}

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


import asyncio
from gpt_researcher import GPTResearcher

# Store active research tasks
research_tasks = {}

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
        
        # Generate task ID
        task_id = f"task_{int(time.time())}"
        
        # Initialize researcher
        researcher = GPTResearcher(
            query=task,
            report_type=report_type,
            report_format="markdown"
        )
        
        # Store task info
        research_tasks[task_id] = {
            "status": "running",
            "task": task,
            "report": None,
            "files": None,
            "researcher": researcher
        }
        
        # Start research in background
        async def run_research():
            try:
                await researcher.conduct_research()
                report = await researcher.write_report()
                
                # Generate files
                sanitized_filename = f"{task_id}_{task[:50]}"  # Use first 50 chars of task
                file_paths = await generate_report_files(report, sanitized_filename)
                
                # Update task info
                research_tasks[task_id].update({
                    "status": "completed",
                    "report": report,
                    "files": file_paths
                })
            except Exception as e:
                logger.error(f"Error in research task {task_id}: {str(e)}")
                research_tasks[task_id]["status"] = "error"
                research_tasks[task_id]["error"] = str(e)
        
        # Start the research task
        asyncio.create_task(run_research())
        
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
        # Check if task exists
        if task_id not in research_tasks:
            return JSONResponse(
                status_code=404,
                content={
                    "status": "not_found",
                    "message": "Task not found"
                }
            )
        
        task_info = research_tasks[task_id]
        
        # Return task status
        response = {
            "status": task_info["status"],
            "task": task_info["task"]
        }
        
        # Add report and files if completed
        if task_info["status"] == "completed":
            response.update({
                "report": task_info["report"],
                "files": task_info["files"]
            })
        # Add error if failed
        elif task_info["status"] == "error":
            response["error"] = task_info.get("error")
        
        return JSONResponse(
            status_code=200,
            content=response
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
