# Import required libraries
from fastapi import FastAPI
import sqlite3

# Create FastAPI app
app = FastAPI()

# Connect to SQLite database (creates file if not exists)
def get_db_connection():
    conn = sqlite3.connect("users.db")
    conn.row_factory = sqlite3.Row  # Allows dict-like access
    return conn

# Create table if it does not exist
def create_table():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT
        )
    """)
    conn.commit()
    conn.close()

# Call table creation on app start
create_table()

# -------------------------------
# API ENDPOINTS
# -------------------------------

# Root endpoint
@app.get("/")
def home():
    return {"message": "FastAPI + SQLite API is running"}

# Create a new user
@app.post("/add-user")
def add_user(name: str, email: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (name, email) VALUES (?, ?)",
        (name, email)
    )
    conn.commit()
    conn.close()

    return {
        "status": "success",
        "name": name,
        "email": email
    }

# Get user by ID
@app.get("/get-user/{user_id}")
def get_user(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM users WHERE id = ?",
        (user_id,)
    )
    user = cursor.fetchone()
    conn.close()

    if user is None:
        return {"error": "User not found"}

    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"]
    }
