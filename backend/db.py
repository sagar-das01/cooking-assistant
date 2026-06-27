import os
import sqlite3
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Load env variables first to ensure they are available
load_dotenv(dotenv_path="../.env")
load_dotenv()

# Try importing psycopg2-binary for PostgreSQL support
try:
    import psycopg2
    import psycopg2.extras
    HAS_POSTGRES = True
except ImportError:
    HAS_POSTGRES = False

DATABASE_URL = os.environ.get("DATABASE_URL")
IS_POSTGRES = HAS_POSTGRES and DATABASE_URL and (DATABASE_URL.startswith("postgres://") or DATABASE_URL.startswith("postgresql://"))
DB_CONNECTION_ERROR = None

print(f"DATABASE CONFIG: Initial preference is {'PostgreSQL' if IS_POSTGRES else 'SQLite'} database.")

def get_db_connection():
    global IS_POSTGRES, DB_CONNECTION_ERROR
    if IS_POSTGRES:
        try:
            # PostgreSQL connection (ensure we handle connection params correctly)
            # Handle the case where database URL starts with postgres:// (which psycopg2 sometimes complains about, requiring postgresql://)
            conn_url = DATABASE_URL
            if conn_url.startswith("postgres://"):
                conn_url = conn_url.replace("postgres://", "postgresql://", 1)
            conn = psycopg2.connect(conn_url)
            DB_CONNECTION_ERROR = None
            return conn
        except Exception as e:
            print(f"PostgreSQL connection error: {e}. Falling back to SQLite.")
            DB_CONNECTION_ERROR = str(e)
            IS_POSTGRES = False
            # Fall through to SQLite connection
            
    # SQLite connection
    conn = sqlite3.connect("sessions.db")
    conn.row_factory = sqlite3.Row
    return conn


def get_cursor(conn):
    if IS_POSTGRES:
        return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    return conn.cursor()

def execute_query(cursor, query: str, params=()):
    if IS_POSTGRES:
        # Convert SQLite's "?" placeholder to PostgreSQL's "%s"
        query = query.replace("?", "%s")
    cursor.execute(query, params)

def init_db():
    conn = get_db_connection()
    cursor = get_cursor(conn)
    
    if IS_POSTGRES:
        # PostgreSQL schema
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id SERIAL PRIMARY KEY,
            session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        ''')
    else:
        # SQLite schema
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
        )
        ''')
    
    conn.commit()
    conn.close()

def create_session(title: Optional[str] = None) -> Dict[str, Any]:
    session_id = str(uuid.uuid4())
    if not title:
        title = "New Cooking Session"
    created_at = datetime.utcnow().isoformat()
    
    conn = get_db_connection()
    cursor = get_cursor(conn)
    execute_query(
        cursor,
        "INSERT INTO sessions (id, title, created_at) VALUES (?, ?, ?)",
        (session_id, title, created_at)
    )
    conn.commit()
    conn.close()
    
    return {
        "id": session_id,
        "title": title,
        "created_at": created_at,
        "messages": []
    }

def get_sessions() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = get_cursor(conn)
    execute_query(cursor, "SELECT id, title, created_at FROM sessions ORDER BY created_at DESC")
    rows = cursor.fetchall()
    
    sessions = []
    for row in rows:
        sessions.append({
            "id": row["id"],
            "title": row["title"],
            "created_at": row["created_at"]
        })
    conn.close()
    return sessions

def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = get_cursor(conn)
    
    # Get session details
    execute_query(cursor, "SELECT id, title, created_at FROM sessions WHERE id = ?", (session_id,))
    session_row = cursor.fetchone()
    if not session_row:
        conn.close()
        return None
        
    # Get session messages
    execute_query(
        cursor,
        "SELECT id, role, content, created_at FROM messages WHERE session_id = ? ORDER BY id ASC",
        (session_id,)
    )
    message_rows = cursor.fetchall()
    
    messages = []
    for msg in message_rows:
        messages.append({
            "id": msg["id"],
            "role": msg["role"],
            "content": msg["content"],
            "created_at": msg["created_at"]
        })
        
    conn.close()
    return {
        "id": session_row["id"],
        "title": session_row["title"],
        "created_at": session_row["created_at"],
        "messages": messages
    }

def add_message(session_id: str, role: str, content: str) -> Dict[str, Any]:
    created_at = datetime.utcnow().isoformat()
    
    conn = get_db_connection()
    cursor = get_cursor(conn)
    
    # Insert message
    execute_query(
        cursor,
        "INSERT INTO messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
        (session_id, role, content, created_at)
    )
    
    # Get message ID depending on connection type
    if IS_POSTGRES:
        cursor.execute("SELECT lastval()")
        message_id = cursor.fetchone()['lastval']
    else:
        message_id = cursor.lastrowid
    
    # Auto-update title if it's the first user message and title is default
    if role == "user":
        execute_query(cursor, "SELECT COUNT(*) as count FROM messages WHERE session_id = ? AND role = 'user'", (session_id,))
        count_row = cursor.fetchone()
        
        # In sqlite count_row is sqlite3.Row, in postgres it is dict-like
        msg_count = count_row["count"] if IS_POSTGRES else count_row[0]
        
        if msg_count == 1:
            # Generate a short title from the message (first 30 chars)
            short_title = content[:30] + "..." if len(content) > 30 else content
            execute_query(cursor, "UPDATE sessions SET title = ? WHERE id = ? AND title = 'New Cooking Session'", (short_title, session_id))
            
    conn.commit()
    conn.close()
    
    return {
        "id": message_id,
        "session_id": session_id,
        "role": role,
        "content": content,
        "created_at": created_at
    }

def delete_session(session_id: str) -> bool:
    conn = get_db_connection()
    cursor = get_cursor(conn)
    
    # Check if exists
    execute_query(cursor, "SELECT 1 FROM sessions WHERE id = ?", (session_id,))
    if not cursor.fetchone():
        conn.close()
        return False
        
    # Delete
    execute_query(cursor, "DELETE FROM messages WHERE session_id = ?", (session_id,))
    execute_query(cursor, "DELETE FROM sessions WHERE id = ?", (session_id,))
    
    conn.commit()
    conn.close()
    return True

def update_session_title(session_id: str, title: str) -> bool:
    conn = get_db_connection()
    cursor = get_cursor(conn)
    
    execute_query(cursor, "SELECT 1 FROM sessions WHERE id = ?", (session_id,))
    if not cursor.fetchone():
        conn.close()
        return False
        
    execute_query(cursor, "UPDATE sessions SET title = ? WHERE id = ?", (title, session_id))
    conn.commit()
    conn.close()
    return True
