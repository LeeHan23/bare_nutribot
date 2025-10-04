import streamlit as st
import requests
import uuid
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import necessary functions from your project files
from rag import get_rag_response
import database as db

# --- Configuration ---
API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="Chatbot Admin Panel", layout="wide")

# --- Session State Initialization ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.view = "login"

# --- UI Rendering ---
st.sidebar.title("Admin Access")

if not st.session_state.logged_in:
    db_session = db.SessionLocal()
    try:
        # (Login and Signup logic remains the same)
        if st.session_state.view == "login":
            st.sidebar.header("Login")
            username = st.sidebar.text_input("Username", key="login_user")
            password = st.sidebar.text_input("Password", type="password", key="login_pass")

            if st.sidebar.button("Login"):
                if db.check_login(db_session, username, password):
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.view = "main"
                    st.rerun()
                else:
                    st.sidebar.error("Invalid username or password.")
            
            if st.sidebar.button("Go to Sign Up"):
                st.session_state.view = "signup"
                st.rerun()

        elif st.session_state.view == "signup":
            st.sidebar.header("Create New Admin Account")
            new_username = st.sidebar.text_input("New Username", key="signup_user")
            new_password = st.sidebar.text_input("New Password", type="password", key="signup_pass")
            confirm_password = st.sidebar.text_input("Confirm Password", type="password", key="signup_confirm")

            if st.sidebar.button("Create Account"):
                if not new_username or not new_password:
                    st.sidebar.warning("Please enter a username and password.")
                elif len(new_password) > 72:
                    st.sidebar.error("Password cannot be more than 72 characters long.")
                elif new_password != confirm_password:
                    st.sidebar.error("Passwords do not match.")
                else:
                    try:
                        db.add_user(db_session, new_username, new_password)
                        st.sidebar.success("Account created successfully! Please go back to log in.")
                    except ValueError as e:
                        st.sidebar.error(f"Error: {e}")
    finally:
        db_session.close()

else:
    # --- Main Application View (after login) ---
    st.sidebar.success(f"Logged in as **{st.session_state.username}**")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.view = "login"
        st.rerun()

    st.header("Chatbot Management Dashboard")
    
    tab1, tab2 = st.tabs(["💬 Chat Testing", "🧠 My Specialized Knowledge"])

    with tab1:
        st.header("Test the RAG Chatbot")
        st.info("Interact with the chatbot as a test user to verify its responses and knowledge.")

        # Initialize chat state
        if 'admin_messages' not in st.session_state:
            st.session_state.admin_messages = []
        if 'admin_session_id' not in st.session_state:
            st.session_state.admin_session_id = f"admin_session_{uuid.uuid4()}"

        # Display chat history
        for message in st.session_state.admin_messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])
                if "image_url" in message and message["image_url"]:
                    st.image(message["image_url"])

        # Chat input
        if prompt := st.chat_input("Ask the bot a question..."):
            st.chat_message("user").write(prompt)
            st.session_state.admin_messages.append({"role": "user", "content": prompt})

            with st.chat_message("assistant"):
                with st.spinner("Getting response..."):
                    # Use the admin's username as the user_id to access their specialized knowledge
                    response_data = get_rag_response(
                        question=prompt,
                        user_id=st.session_state.username,
                        chat_session_id=st.session_state.admin_session_id
                    )
                    
                    answer = response_data.get("answer", "I'm sorry, an error occurred.")
                    image_url = response_data.get("image_url")

                    st.write(answer)
                    if image_url:
                        st.image(image_url)
                    
                    st.session_state.admin_messages.append({
                        "role": "assistant", 
                        "content": answer,
                        "image_url": image_url
                    })
    
    with tab2:
        st.header("Train Your Specialized Bot")
        st.info("Upload your personal .pdf or .docx files here to add custom knowledge to your own admin chatbot.")
        
        uploaded_file = st.file_uploader(
            "Upload a document", 
            type=['pdf', 'docx'],
            key="admin_doc_uploader",
            accept_multiple_files=False
        )

        if uploaded_file is not None:
            if st.button(f"Process '{uploaded_file.name}'"):
                with st.spinner(f"Processing {uploaded_file.name}... This may take a moment."):
                    try:
                        files = {'file': (uploaded_file.name, uploaded_file, uploaded_file.type)}
                        # Use the admin's username as the user_id for the upload
                        payload = {'user_id': st.session_state.username}
                        
                        response = requests.post(
                            f"{API_URL}/upload_document/",
                            files=files,
                            data=payload
                        )
                        
                        if response.status_code == 200:
                            st.success(f"✅ Successfully trained on {uploaded_file.name}!")
                        else:
                            st.error(f"Error processing file: {response.text}")
                    except Exception as e:
                        st.error(f"An error occurred: {e}")

# Initial view for non-logged-in users
if not st.session_state.logged_in:
     st.title("Welcome to the Chatbot Admin Panel")
     st.header("Please log in or sign up using the sidebar to continue.")