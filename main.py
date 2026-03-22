from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import logging
import httpx
import os
import json
from google import genai
from google.genai import types
from agent import run_agent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Tripletex AI Agent")

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    body = await request.body()
    logger.error(f"Validation Error: {exc.errors()}")
    logger.error(f"Request Body: {body.decode()}")
    return JSONResponse(status_code=422, content={"detail": exc.errors(), "body": body.decode()})

# Schemas
import uuid

class FileAttachment(BaseModel):
    filename: Optional[str] = None
    mime_type: Optional[str] = None
    data: Optional[str] = None  # Base64 encoded data
    content_base64: Optional[str] = None # Added for compatibility with competition payload
    local_path: Optional[str] = None

class TripletexCredentials(BaseModel):
    base_url: str
    session_token: str

class SolveRequest(BaseModel):
    prompt: str
    files: Optional[List[FileAttachment]] = Field(default_factory=list)
    tripletex_credentials: TripletexCredentials

# Initialize Gemini Client
# We read the API key from config.json if not set in env
API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    try:
        config_path = os.path.join(os.path.dirname(__file__), "config", "config.json")
        with open(config_path, "r") as f:
            config = json.load(f)
            API_KEY = config.get("apiKey")
    except Exception as e:
        logger.warning(f"Could not read config.json: {e}")

if API_KEY:
    client = genai.Client(api_key=API_KEY)
else:
    logger.error("No Gemini API key found!")
    client = None

@app.post("/solve")
def solve(request: SolveRequest):
    logger.info(f"main:Received task prompt: {request.prompt}")
    logger.info(f"main:Files attached: {len(request.files) if request.files else 0}")
    
    if client:
        try:
            # Handle files - save them locally to pass paths if needed
            saved_files = []
            if request.files:
                import base64
                if not os.path.exists("temp_uploads"):
                    os.makedirs("temp_uploads")
                for f in request.files:
                    file_data = f.content_base64 if f.content_base64 else f.data
                    if not file_data:
                        logger.warning(f"No data found for file {f.filename}")
                        continue
                        
                    filename = os.path.basename(f.filename) if f.filename else f"file_{uuid.uuid4().hex[:8]}"
                    filepath = os.path.abspath(os.path.join("temp_uploads", filename))
                    
                    try:
                        with open(filepath, "wb") as out_file:
                            out_file.write(base64.b64decode(file_data))
                        # Attach the path so the agent can use it with multipart uploads
                        setattr(f, "local_path", filepath)
                        saved_files.append(f)
                    except Exception as e:
                        logger.error(f"Failed to save file {filename}: {e}")

            # Append the file paths to the prompt to give the LLM context
            final_prompt = request.prompt
            if saved_files:
                final_prompt += "\n\nThe following files are attached and saved locally:\n"
                for sf in saved_files:
                    final_prompt += f"- {sf.local_path}\n"

            # Pass the credentials and the prompt to the agent
            base_url = request.tripletex_credentials.base_url
            session_token = request.tripletex_credentials.session_token
            
            summary = run_agent(
                client=client,
                base_url=base_url,
                session_token=session_token,
                prompt=final_prompt,
                files=saved_files
            )
            logger.info(f"Agent summary: {summary}")
        except Exception as e:
            logger.error(f"Agent execution failed: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))
    else:
        logger.error("No Gemini client configured.")
        raise HTTPException(status_code=500, detail="Gemini client not initialized")
    
    return {"status": "completed"}

@app.get("/health")
def health_check():
    return {"status": "ok"}
