import os
import json
import time
from dotenv import load_dotenv

# --- Load environment variables from .env file FIRST ---
load_dotenv()

from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain.docstore.document import Document
from unstructured.partition.auto import partition
from unstructured.chunking.title import chunk_by_title

# --- UNIFIED PATH CONFIGURATION ---
APP_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_DATA_PATH = os.path.join(APP_DIR, "data")
PERSISTENT_DISK_PATH = os.environ.get("PERSISTENT_DISK_PATH", LOCAL_DATA_PATH)

# ========= CONFIGURATION =========
BASE_DOCS_DIR = os.path.join(APP_DIR, "data", "base_docs")
BASE_INDEX_DIR = os.path.join(PERSISTENT_DISK_PATH, "vectorstore_base")
FILE_TRACKER_PATH = os.path.join(LOCAL_DATA_PATH, "file_tracker.json")
COLLECTION_NAME = "base_knowledge"
# Use OpenAI's newer, more cost-effective embedding model
EMBEDDING_MODEL = "text-embedding-3-small" 
# =================================

def load_processed_files_tracker():
    """Loads the tracker for already processed files."""
    if os.path.exists(FILE_TRACKER_PATH):
        with open(FILE_TRACKER_PATH, 'r') as f:
            return json.load(f)
    return {}

def save_processed_files_tracker(tracker):
    """Saves the tracker for processed files."""
    with open(FILE_TRACKER_PATH, 'w') as f:
        json.dump(tracker, f, indent=4)

def get_files_to_process():
    """
    Determines which files in the base_docs directory are new or have been modified
    since the last run.
    """
    tracker = load_processed_files_tracker()
    files_to_process = []
    
    if not os.path.exists(BASE_DOCS_DIR):
        print(f"Error: The directory '{BASE_DOCS_DIR}' was not found.")
        return [], tracker

    for filename in os.listdir(BASE_DOCS_DIR):
        filepath = os.path.join(BASE_DOCS_DIR, filename)
        if not os.path.isfile(filepath):
            continue
            
        modification_time = os.path.getmtime(filepath)
        
        if filename not in tracker or tracker[filename] < modification_time:
            files_to_process.append(filepath)
            print(f"Detected new or updated file: {filename}")
            
    return files_to_process, tracker

def build_base_database():
    """
    Builds or updates the vector store using incremental updates, intelligent chunking,
    and metadata enrichment.
    """
    print("--- Starting Knowledge Base Update ---")
    
    files_to_process, tracker = get_files_to_process()

    if not files_to_process:
        print("No new or updated files to process. Knowledge base is up to date.")
        return

    print(f"Processing {len(files_to_process)} new/updated document(s)...")

    embedding_function = OpenAIEmbeddings(model=EMBEDDING_MODEL, max_retries=10)
    
    all_chunks = []
    for filepath in files_to_process:
        try:
            print(f"Partitioning and chunking: {os.path.basename(filepath)}")
            # Use unstructured to partition the document into elements
            elements = partition(filename=filepath)
            # Use unstructured to chunk based on titles and sections
            chunks = chunk_by_title(elements, max_characters=1500, combine_under_n_chars=500)
            
            # Convert unstructured chunks to LangChain Documents with metadata
            for chunk in chunks:
                # Attempt to find a title in the element's metadata
                title = chunk.metadata.get_element_orig_filename() # Fallback to filename
                if hasattr(chunk, 'metadata') and hasattr(chunk.metadata, 'title'):
                    title = chunk.metadata.title

                all_chunks.append(Document(
                    page_content=str(chunk),
                    metadata={
                        "source": os.path.basename(filepath),
                        "title": title
                    }
                ))
            
        except Exception as e:
            print(f"Error processing {os.path.basename(filepath)}: {e}")

    if not all_chunks:
        print("No content was generated from the new files. Aborting update.")
        return

    print(f"Generated {len(all_chunks)} new chunks to be added to the knowledge base.")

    # Initialize ChromaDB client and add the new chunks
    vector_store = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embedding_function,
        persist_directory=BASE_INDEX_DIR
    )
    
    vector_store.add_documents(all_chunks)
    print(f"Successfully added {len(all_chunks)} new chunks to the vector store.")

    # Update the file tracker with the new modification times
    for filepath in files_to_process:
        filename = os.path.basename(filepath)
        tracker[filename] = os.path.getmtime(filepath)
    
    save_processed_files_tracker(tracker)
    
    print("\n✅ Knowledge base update complete!")

if __name__ == "__main__":
    build_base_database()