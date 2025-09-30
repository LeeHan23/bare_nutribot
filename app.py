import os
import uvicorn
import shutil
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import database as db
from website_chat_router import chat_router
from process_user_docs import process_user_document # <-- New Import

# --- Load Environment Variables ---
load_dotenv()

# --- FastAPI App Initialization ---
app = FastAPI()

# --- CORS Middleware ---
origins = [
    "http://localhost",
    "http://localhost:8501", # Streamlit default port
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Database Dependency ---
def get_db():
    database = db.SessionLocal()
    try:
        yield database
    finally:
        database.close()

# --- API Routers ---
app.include_router(chat_router, prefix="/chat", tags=["Chat"])

# --- NEW: File Upload Endpoint ---
@app.post("/upload_document/", tags=["Document Upload"])
async def upload_document(user_id: str = Form(...), file: UploadFile = File(...)):
    """
    Endpoint for clients to upload documents to train their personal bot.
    """
    # Create a temporary directory to store uploaded files
    temp_dir = "temp_uploads"
    os.makedirs(temp_dir, exist_ok=True)
    
    temp_filepath = os.path.join(temp_dir, file.filename)
    
    try:
        # Save the uploaded file temporarily
        with open(temp_filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Process the document and add it to the user's knowledge base
        process_user_document(user_id=user_id, filepath=temp_filepath)
        
        return {"status": "success", "filename": file.filename, "detail": "Document processed successfully."}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
        
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_filepath):
            os.remove(temp_filepath)

# --- Root Endpoint ---
@app.get("/")
def read_root():
    return {"message": "Welcome to the Nutrition Chatbot API"}

# --- Main Entry Point ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)