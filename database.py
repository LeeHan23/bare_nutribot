import os
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
# --- UPDATED IMPORTS ---
from werkzeug.security import generate_password_hash, check_password_hash

# --- Database Configuration ---
DATABASE_URL = "sqlite:///./data/users.db"
os.makedirs("data", exist_ok=True)

# --- SQLAlchemy Setup ---
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- User Database Model ---
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)

# --- Database Creation ---
def create_db_and_tables():
    Base.metadata.create_all(bind=engine)

# --- User Management Functions ---
def get_user(db_session, username: str):
    return db_session.query(User).filter(User.username == username).first()

def add_user(db_session, username: str, password: str):
    if get_user(db_session, username):
        raise ValueError("Username already exists")
    # --- UPDATED: Use werkzeug to hash password ---
    hashed_password = generate_password_hash(password)
    new_user = User(username=username, hashed_password=hashed_password)
    db_session.add(new_user)
    db_session.commit()
    db_session.refresh(new_user)
    return new_user

def check_login(db_session, username: str, password: str) -> bool:
    user = get_user(db_session, username)
    if not user:
        return False
    # --- UPDATED: Use werkzeug to check password ---
    return check_password_hash(user.hashed_password, password)

# --- Initial Database Creation ---
create_db_and_tables()