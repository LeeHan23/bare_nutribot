from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
import database as db
import rag

# --- Router Initialization ---
chat_router = APIRouter()

# --- Database Dependency ---
def get_db():
    database = db.SessionLocal()
    try:
        yield database
    finally:
        database.close()

# --- Pydantic Models ---
class ChatRequest(BaseModel):
    username: str
    question: str
    session_id: str

# --- Chat Endpoint ---
@chat_router.post("/get_response")
def get_chat_response(request: ChatRequest, database: Session = Depends(get_db)):
    user = db.get_user(database, request.username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        answer = rag.get_rag_response(
            question=request.question,
            user_id=str(user.id),
            chat_session_id=request.session_id
        )
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))