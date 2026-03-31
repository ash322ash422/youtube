from fastapi import FastAPI

app = FastAPI()

# 1) ---------------- ROUTES ----------------

# HOME
@app.get("/")
def home():
    return {"message": "FastAPI is working! I am happy"}


# 2) ---------------- DATABASE ----------------
import sqlite3

def get_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


# create table automatically
conn = get_connection()
conn.execute("""
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    price REAL,
    quantity INTEGER
)
""")
conn.close()


# 3) ---------------- DATA VALIDATION ----------------
from pydantic import BaseModel, Field

class Item(BaseModel):
    name: str     = Field(..., min_length=2)
    price: float  = Field(..., gt=0) # user has to enter number > 0
    quantity: int = Field(..., ge=0) # user has to enter number >= 0



# ---------------- POST (CREATE) ----------------
# POST Request: Add data to DB
@app.post("/items")
def create_item(item: Item):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO items (name, price, quantity) VALUES (?, ?, ?)",
        (item.name, item.price, item.quantity),
    )

    conn.commit()
    conn.close()

    return {"message": "Item added successfully"}

# GOTO: http://127.0.0.1:8000/docs and create a 2 record


# 4) ---------------- GET ALL ----------------
# GET Request: Fetch data
@app.get("/items")  
def get_items():
    conn = get_connection()
    cursor = conn.cursor()

    rows = cursor.execute("SELECT * FROM items").fetchall()
    conn.close()

    return [dict(row) for row in rows]

# You can view all the items using http://127.0.0.1:8000/items
# or use swaggerUI: http://127.0.0.1:8000/docs

# 5) ---------------- GET ONE ----------------
from fastapi import HTTPException

@app.get("/items/{item_id}")
def get_item(item_id: int):

    conn = get_connection()
    cursor = conn.cursor()

    row = cursor.execute(
        "SELECT * FROM items WHERE id=?",
        (item_id,)
    ).fetchone()

    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Item not found")

    return dict(row)

# You can view the items using http://127.0.0.1:8000/items/2
# or use swaggerUI: http://127.0.0.1:8000/docs


# 6) ---------------- PUT (FULL UPDATE) ----------------
# PUT Request (Full Update): Replace entire record.
@app.put("/items/{item_id}")
def update_item(item_id: int, item: Item):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE items
        SET name=?, price=?, quantity=?
        WHERE id=?
    """, (item.name, item.price, item.quantity, item_id))

    conn.commit()
    conn.close()

    return {"message": "Item fully updated"}

# You can update items using swaggerUI: http://127.0.0.1:8000/docs


# 7) ---------------- DELETE ----------------
# DELETE Request: Remove record.
@app.delete("/items/{item_id}")
def delete_item(item_id: int):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM items WHERE id=?", (item_id,))

    conn.commit()
    conn.close()

    return {"message": "Item deleted"}

# You can delete items by using swaggerUI: http://127.0.0.1:8000/docs
