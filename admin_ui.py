import streamlit as st
import requests
import os
import asyncio
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
from rag import get_contextual_response
# REMOVED: from agent_tools import get_all_customer_reports
from database import add_user, check_login, verify_user, get_access_logs

API_BASE_URL = "http://localhost:8000/admin"

# --- Helper function for file uploads ---
def upload_file(endpoint: str, file, file_type: str, metadata: dict):
    files = {'file': (file.name, file, file.type)}
    try:
        response = requests.post(f"{API_BASE_URL}/{endpoint}", files=files, data=metadata)
        response.raise_for_status()
        st.success(f"{file_type} file '{file.name}' uploaded successfully!")
    except requests.exceptions.RequestException as e:
        st.error(f"Error uploading file: {e}")
        if e.response: st.error(f"Server responded with: {e.response.text}")

st.set_page_config(page_title="Chatbot Admin Panel", layout="wide")

# (Login and Sign-up logic remains the same)
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.show_verification = False
    st.session_state.verification_key = ""

st.sidebar.title("Admin Access")
if not st.session_state.logged_in:
    # (Login form remains the same)
    pass # Placeholder for existing login UI code
else:
    st.sidebar.success(f"Logged in as **{st.session_state.username}**")
    if st.sidebar.button("Logout"):
        # (Logout logic remains the same)
        st.rerun()

    st.header("Chatbot Management Dashboard")

    # --- Simplified Tabs ---
    tab1, tab3, tab4 = st.tabs(["📚 Knowledge Base", "💬 Chat Testing", "🔐 Security & Access Logs"])

    with tab1:
        st.header("📚 Foundational Knowledge Base Management")
        st.info("Upload .docx files here to build or update the core knowledge for all users.")
        
        uploaded_knowledge_files = st.file_uploader(
            "Upload Foundational Documents",
            accept_multiple_files=True,
            type=['docx'],
            key="knowledge_uploader"
        )
        
        if st.button("Process Foundational Files"):
            if uploaded_knowledge_files:
                with st.spinner("Processing files... This may take a while."):
                    for file in uploaded_knowledge_files:
                        # This assumes an endpoint exists to handle foundational knowledge.
                        # You would build this similar to the user-level upload.
                        upload_file("upload_base_document", file, "Knowledge", {})
            else:
                st.warning("Please upload at least one document.")

    with tab3:
        st.header("💬 Test the RAG Chatbot")
        st.info("Interact with the chatbot as a test user to verify its responses and knowledge.")
        
        # (Chat testing UI remains the same)
        TEST_CUSTOMER_ID = "admin_test_customer"
        test_user_id = st.text_input("Enter a Test User ID (e.g., 'user123')", value="test_user")

        if 'admin_messages' not in st.session_state:
            st.session_state.admin_messages = []

        for message in st.session_state.admin_messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])

        if prompt := st.chat_input("Ask the bot a question..."):
            st.chat_message("user").write(prompt)
            st.session_state.admin_messages.append({"role": "user", "content": prompt})

            with st.chat_message("assistant"):
                with st.spinner("Getting response..."):
                    chat_history = [msg for msg in st.session_state.admin_messages if isinstance(msg, dict)]
                    response_data = asyncio.run(get_contextual_response(prompt, chat_history, test_user_id, TEST_CUSTOMER_ID))
                    response_text = response_data.get("answer", "I'm sorry, an error occurred.")
                    st.write(response_text)
                    sources = response_data.get("sources", [])
                    if sources:
                        with st.expander("View Sources"):
                            for source in sources:
                                source_name = os.path.basename(source.metadata.get('source', 'Unknown'))
                                st.info(f"Source: {source_name}, Page: {source.metadata.get('page', 'N/A')}")
                                st.caption(f"> {source.page_content[:250]}...")
            st.session_state.admin_messages.append({"role": "assistant", "content": response_text})

    with tab4:
        st.header("🔐 Security & Access Logs")
        # (Content remains the same)
        if st.button("Refresh Logs"):
            st.rerun()
        logs = get_access_logs()
        if logs:
            df = pd.DataFrame(logs, columns=["Username", "Timestamp", "Status"])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No access attempts have been logged yet.")

if not st.session_state.logged_in:
    st.title("Welcome to the Chatbot Admin Panel")
    st.header("Please log in or sign up using the sidebar to continue.")