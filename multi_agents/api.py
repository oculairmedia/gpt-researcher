from fastapi import FastAPI, HTTPException, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
from typing import Dict, Any, Optional, List
import sys
import os
import uuid

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from multi_agents.agents import ChiefEditorAgent

api_router = APIRouter()

class ResearchTask(BaseModel):
    query: str
    max_sections: int = 3
    publish_formats: Dict[str, bool] = {
        "markdown": True,
        "pdf": False,
        "docx": False
    }
    include_human_feedback: bool = False
    follow_guidelines: bool = True
    model: str = "gpt-4"
    guidelines: List[str] = [
        "The report MUST be written in APA format",
        "Each sub section MUST include supporting sources using hyperlinks. If none exist, erase the sub section or rewrite it to be a part of the previous section",
        "The report MUST be written in English"
    ]
    verbose: bool = True

@api_router.post("/research")
async def create_research(task: ResearchTask):
    try:
        # Convert the Pydantic model to a dictionary
        task_dict = task.dict()
        
        # Initialize the ChiefEditorAgent with the task
        chief_editor = ChiefEditorAgent(task_dict)
        
        # Run the research task
        research_report = await chief_editor.run_research_task(task_id=uuid.uuid4())
        
        # Return the research report as JSON
        return {
            "status": "success",
            "data": research_report
        }
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error in research task: {error_trace}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/")
async def root():
    return {
        "message": "GPT Researcher API is running",
        "docs": "/docs",
        "openapi": "/openapi.json"
    }

app = FastAPI(title="GPT Researcher API")
app.include_router(api_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
