import streamlit as st
import uuid
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import necessary functions from your project files
from rag import get_rag_response
import database as db

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
                elif new_password != confirm_password:
                    st.sidebar.error("Passwords do not match.")
                else:
                    try:
                        db.add_user(db_session, new_username, new_password)
                        st.sidebar.success("Account created successfully! Please go back to log in.")
                    except ValueError as e:
                        st.sidebar.error(f"Error: {e}")
                    except Exception as e:
                        st.sidebar.error(f"An unexpected error occurred.")

            if st.sidebar.button("Back to Login"):
                st.session_state.view = "login"
                st.rerun()
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

    # (The rest of your admin UI chat interface code goes here)
    st.header("💬 Test the RAG Chatbot")
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
                response_data = get_rag_response(
                    question=prompt,
                    user_id="admin_test_user",
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

# Initial view for non-logged-in users
if not st.session_state.logged_in and st.session_state.view == "login":
     st.title("Welcome to the Chatbot Admin Panel")
     st.header("Please log in or sign up using the sidebar to continue.")
elif not st.session_state.logged_in and st.session_state.view == "signup":
     st.title("Create an Admin Account")
     st.header("Please fill out the form in the sidebar.")