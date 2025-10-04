import os
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from passlib.context import CryptContext

# --- Database Configuration ---
# This will create a 'users.db' file in your 'data' directory.
DATABASE_URL = "sqlite:///./data/users.db"

# Ensure the data directory exists
os.makedirs("data", exist_ok=True)

# --- SQLAlchemy Setup ---
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- Password Hashing Setup ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- User Database Model ---
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)

# --- Database Creation ---
def create_db_and_tables():
    """Creates the database and the users table if they don't exist."""
    Base.metadata.create_all(bind=engine)

# --- User Management Functions ---
def get_user(db_session, username: str):
    """Fetches a user by their username."""
    return db_session.query(User).filter(User.username == username).first()

def add_user(db_session, username: str, password: str):
    """Adds a new user to the database with a hashed password."""
    if get_user(db_session, username):
        raise ValueError("Username already exists")
    hashed_password = pwd_context.hash(password)
    new_user = User(username=username, hashed_password=hashed_password)
    db_session.add(new_user)
    db_session.commit()
    db_session.refresh(new_user)
    return new_user

def check_login(db_session, username: str, password: str) -> bool:
    """Verifies a user's login credentials."""
    user = get_user(db_session, username)
    if not user:
        return False
    return pwd_context.verify(password, user.hashed_password)

# --- Initial Database Creation ---
# This line ensures that the database file and table are created when the app starts.
create_db_and_tables()