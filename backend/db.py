import sqlite3
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

DB_PATH = "sessions.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create sessions table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    ''')
    
    # Create messages table
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
    cursor = conn.cursor()
    cursor.execute(
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
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sessions ORDER BY created_at DESC")
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
    cursor = conn.cursor()
    
    # Get session details
    cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
    session_row = cursor.fetchone()
    if not session_row:
        conn.close()
        return None
        
    # Get session messages
    cursor.execute(
        "SELECT * FROM messages WHERE session_id = ? ORDER BY id ASC",
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
    cursor = conn.cursor()
    
    # Insert message
    cursor.execute(
        "INSERT INTO messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
        (session_id, role, content, created_at)
    )
    message_id = cursor.lastrowid
    
    # Auto-update title if it's the first user message and title is default
    if role == "user":
        cursor.execute("SELECT COUNT(*) as count FROM messages WHERE session_id = ? AND role = 'user'", (session_id,))
        count_row = cursor.fetchone()
        if count_row["count"] == 1:
            # Generate a short title from the message (first 30 chars)
            short_title = content[:30] + "..." if len(content) > 30 else content
            cursor.execute("UPDATE sessions SET title = ? WHERE id = ? AND title = 'New Cooking Session'", (short_title, session_id))
            
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
    cursor = conn.cursor()
    
    # Check if exists
    cursor.execute("SELECT 1 FROM sessions WHERE id = ?", (session_id,))
    if not cursor.fetchone():
        conn.close()
        return False
        
    # Delete (ON DELETE CASCADE will handle messages, but we delete explicitly just in case)
    cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
    cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    
    conn.commit()
    conn.close()
    return True

def update_session_title(session_id: str, title: str) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT 1 FROM sessions WHERE id = ?", (session_id,))
    if not cursor.fetchone():
        conn.close()
        return False
        
    cursor.execute("UPDATE sessions SET title = ? WHERE id = ?", (title, session_id))
    conn.commit()
    conn.close()
    return True
