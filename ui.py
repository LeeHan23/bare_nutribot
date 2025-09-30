import streamlit as st
import requests
import uuid

# --- Configuration ---
API_URL = "http://127.0.0.1:8000" # Replace with your actual API URL if different

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

# --- Main App UI ---
st.title("🤖 AI Nutrition Assistant")
st.sidebar.header("User Account")

# --- Login / Signup Logic ---
if not st.session_state.logged_in:
    username = st.sidebar.text_input("Username", key="login_user")
    password = st.sidebar.text_input("Password", type="password", key="login_pass")
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("Login"):
            # This is a placeholder. Implement actual login logic against your database.
            st.session_state.logged_in = True 
            st.session_state.username = username
            st.rerun()
    with col2:
        if st.button("Sign Up"):
            # Placeholder for signup logic
            st.sidebar.success("Signup functionality to be implemented.")

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
                        answer = response.json().get("answer")
                        st.markdown(answer)
                        st.session_state.messages.append({"role": "assistant", "content": answer})
                    else:
                        st.error("Failed to get a response from the bot.")
                except requests.exceptions.RequestException as e:
                    st.error(f"Could not connect to the API: {e}")
else:
    st.info("Please log in to start chatting.")