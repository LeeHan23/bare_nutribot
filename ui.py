import streamlit as st
import requests
import uuid
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
import database as db # Import your database module

# --- Configuration ---
API_URL = "http://127.0.0.1:8000"

# --- Page Configuration ---
st.set_page_config(page_title="AI Nutrition Assistant", layout="wide")

# --- Session State Initialization ---
if 'session_id' not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = ""
if 'view' not in st.session_state:
    st.session_state.view = "login"

# --- Main App UI ---
st.title("🤖 AI Nutrition Assistant")
st.sidebar.header("User Account")

if not st.session_state.logged_in:
    db_session = db.SessionLocal()
    try:
        if st.session_state.view == "login":
            username = st.sidebar.text_input("Username", key="login_user")
            password = st.sidebar.text_input("Password", type="password", key="login_pass")
            
            if st.sidebar.button("Login"):
                if db.check_login(db_session, username, password):
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.rerun()
                else:
                    st.sidebar.error("Invalid username or password.")

            if st.sidebar.button("Go to Sign Up"):
                st.session_state.view = "signup"
                st.rerun()

        elif st.session_state.view == "signup":
            st.sidebar.header("Create New Account")
            new_username = st.sidebar.text_input("New Username", key="signup_user")
            new_password = st.sidebar.text_input("New Password", type="password", key="signup_pass")
            confirm_password = st.sidebar.text_input("Confirm Password", type="password", key="signup_confirm")

            if st.sidebar.button("Create Account"):
                if not new_username or not new_password:
                    st.sidebar.warning("Please enter all fields.")
                elif new_password != confirm_password:
                    st.sidebar.error("Passwords do not match.")
                else:
                    try:
                        db.add_user(db_session, new_username, new_password)
                        st.sidebar.success("Account created successfully! Please log in.")
                        st.session_state.view = "login"
                        st.rerun()
                    except ValueError as e:
                        st.sidebar.error(f"Error: {e}")

            if st.sidebar.button("Back to Login"):
                st.session_state.view = "login"
                st.rerun()
    finally:
        db_session.close()

else:
    st.sidebar.success(f"Logged in as: **{st.session_state.username}**")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.messages = []
        st.rerun()

    # --- NEW: Document Uploader for Logged-in Users ---
    st.sidebar.markdown("---")
    st.sidebar.header("Train Your Personal Bot")
    st.sidebar.info("Upload your personal .pdf or .docx files to give your bot custom knowledge.")
    
    uploaded_file = st.sidebar.file_uploader(
        "Upload a document", 
        type=['pdf', 'docx'],
        label_visibility="collapsed"
    )

    if uploaded_file is not None:
        with st.spinner(f"Processing {uploaded_file.name}..."):
            try:
                files = {'file': (uploaded_file.name, uploaded_file, uploaded_file.type)}
                payload = {'user_id': st.session_state.username} # Using username as user_id
                
                response = requests.post(
                    f"{API_URL}/upload_document/",
                    files=files,
                    data=payload
                )
                
                if response.status_code == 200:
                    st.sidebar.success(f"✅ Successfully trained on {uploaded_file.name}!")
                else:
                    st.sidebar.error(f"Error: {response.text}")
            except Exception as e:
                st.sidebar.error(f"An error occurred: {e}")

# --- Chat Interface ---
if st.session_state.logged_in:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Ask me about your nutrition..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    response = requests.post(
                        f"{API_URL}/chat/get_response",
                        json={
                            "username": st.session_state.username,
                            "question": prompt,
                            "session_id": st.session_state.session_id
                        }
                    )
                    if response.status_code == 200:
                        response_data = response.json()
                        answer = response_data.get("answer")
                        image_url = response_data.get("image_url") # <-- Get the image URL

                        st.markdown(answer) # Display the text
                        if image_url: # <-- If an image URL was sent
                            st.image(image_url) # <-- Display the image!
                    
                        st.session_state.messages.append({"role": "assistant", "content": answer})
                    else:
                        st.error("Failed to get a response from the bot.")
                except requests.exceptions.RequestException as e:
                    st.error(f"Could not connect to the API: {e}")