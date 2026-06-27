import os
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import db
import ai

# Load environment variables
load_dotenv(dotenv_path="../.env")
load_dotenv()

app = FastAPI(title="Chef Assist Backend API")

# Enable CORS so our React frontend can query it
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For local development we allow all
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on startup
@app.on_event("startup")
def startup_event():
    db.init_db()

class MessageRequest(BaseModel):
    content: str

class SessionCreateRequest(BaseModel):
    title: Optional[str] = None

class SessionTitleUpdate(BaseModel):
    title: str

@app.get("/api/health")
def health_check():
    return {"status": "ok", "api_key_configured": "GEMINI_API_KEY" in os.environ}

@app.get("/api/sessions")
def list_sessions():
    return db.get_sessions()

@app.post("/api/sessions")
def create_session(request: SessionCreateRequest):
    return db.create_session(title=request.title)

@app.get("/api/sessions/{session_id}")
def get_session_details(session_id: str):
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@app.delete("/api/sessions/{session_id}")
def delete_session(session_id: str):
    success = db.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "success", "message": f"Session {session_id} deleted"}

@app.put("/api/sessions/{session_id}/title")
def update_title(session_id: str, request: SessionTitleUpdate):
    success = db.update_session_title(session_id, request.title)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "success", "message": "Title updated"}

@app.post("/api/sessions/{session_id}/message")
def send_message(
    session_id: str,
    request: MessageRequest,
    x_gemini_api_key: Optional[str] = Header(None)
):
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    # 1. Add user message to DB
    user_msg = db.add_message(session_id, "user", request.content)
    
    # 2. Get history for context (exclude the newly added user message to avoid duplicate addition)
    # Actually db.get_session(session_id) would now contain the user message.
    # Let's get updated session details to pass history.
    updated_session = db.get_session(session_id)
    history = updated_session["messages"][:-1]  # pass messages before the last user message
    
    # 3. Generate response using AI
    model_response_content = ai.generate_cooking_plan(
        user_message=request.content,
        history=history,
        custom_api_key=x_gemini_api_key
    )
    
    # 4. Add model message to DB
    model_msg = db.add_message(session_id, "model", model_response_content)
    
    # 5. Return updated session details
    final_session = db.get_session(session_id)
    return {
        "user_message": user_msg,
        "model_message": model_msg,
        "session": final_session
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
