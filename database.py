import sqlite3
import os
import json
from datetime import datetime
from typing import List, Tuple, Optional, Dict, Any
from config import DATABASE_PATH

def init_database():
    """Initialize the database with all required tables"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Tasks table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            location_lat REAL,
            location_lon REAL,
            location_address TEXT,
            payment_amount REAL DEFAULT NULL,
            assigned_to TEXT NOT NULL,
            assigned_by INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            started_at TEXT,
            completed_at TEXT,
            completion_report TEXT,
            completion_media TEXT,
            received_amount REAL DEFAULT 0
        )
    """)
    
    # Debts table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS debts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_name TEXT NOT NULL,
            employee_chat_id INTEGER NOT NULL,
            task_id INTEGER,
            amount REAL NOT NULL,
            reason TEXT NOT NULL,
            payment_date TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'unpaid',
            FOREIGN KEY (task_id) REFERENCES tasks (id)
        )
    """)
    
    # Messages table for notifications
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_chat_id INTEGER NOT NULL,
            to_chat_id INTEGER NOT NULL,
            message_text TEXT NOT NULL,
            message_type TEXT DEFAULT 'general',
            task_id INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (task_id) REFERENCES tasks (id)
        )
    """)
    
    # User states table for conversation management
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_states (
            chat_id INTEGER PRIMARY KEY,
            state TEXT NOT NULL,
            state_data TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Customer inquiries table for website and bot requests
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customer_inquiries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            customer_phone TEXT,
            customer_username TEXT,
            chat_id INTEGER,
            inquiry_text TEXT NOT NULL,
            inquiry_type TEXT DEFAULT 'bot',
            location_lat REAL,
            location_lon REAL,
            location_address TEXT,
            status TEXT DEFAULT 'pending',
            admin_response TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            responded_at TEXT,
            source TEXT DEFAULT 'telegram'
        )
    """)
    
    # Employee locations table for tracking
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS employee_locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_name TEXT NOT NULL,
            employee_chat_id INTEGER NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            location_type TEXT DEFAULT 'manual',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            is_live INTEGER DEFAULT 0
        )
    """)
    
    conn.commit()
    conn.close()

def add_task(description: str, location_lat: float, location_lon: float, 
             location_address: Optional[str], payment_amount: Optional[float], 
             assigned_to: str, assigned_by: int) -> int:
    """Add a new task and return task ID"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO tasks (description, location_lat, location_lon, location_address, 
                          payment_amount, assigned_to, assigned_by)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (description, location_lat, location_lon, location_address, 
          payment_amount, assigned_to, assigned_by))
    
    task_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return task_id or 0

def get_employee_tasks(employee_name: str, status: str = None) -> List[Tuple]:
    """Get tasks for a specific employee"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    if status:
        cursor.execute("""
            SELECT * FROM tasks 
            WHERE assigned_to = ? AND status = ?
            ORDER BY created_at DESC
        """, (employee_name, status))
    else:
        cursor.execute("""
            SELECT * FROM tasks 
            WHERE assigned_to = ?
            ORDER BY created_at DESC
        """, (employee_name,))
    
    tasks = cursor.fetchall()
    conn.close()
    return tasks

def update_task_status(task_id: int, status: str, completion_report: str = None,
                      completion_media: str = None, received_amount: float = None):
    """Update task status and completion details"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    update_fields = ["status = ?"]
    values = [status]
    
    if status == "in_progress":
        update_fields.append("started_at = ?")
        values.append(datetime.now().isoformat())
    elif status == "completed":
        update_fields.append("completed_at = ?")
        values.append(datetime.now().isoformat())
        
        if completion_report:
            update_fields.append("completion_report = ?")
            values.append(completion_report)
        
        if completion_media:
            update_fields.append("completion_media = ?")
            values.append(completion_media)
        
        if received_amount is not None:
            update_fields.append("received_amount = ?")
            values.append(received_amount)
    
    values.append(task_id)
    
    query = f"UPDATE tasks SET {', '.join(update_fields)} WHERE id = ?"
    cursor.execute(query, values)
    
    conn.commit()
    conn.close()

def add_debt(employee_name: str, employee_chat_id: int, task_id: Optional[int],
            amount: float, reason: str, payment_date: str):
    """Add a debt record"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO debts (employee_name, employee_chat_id, task_id, amount, reason, payment_date)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (employee_name, employee_chat_id, task_id, amount, reason, payment_date))
    
    conn.commit()
    conn.close()

def get_debts(employee_name: str = None) -> List[Tuple]:
    """Get debt records"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    if employee_name:
        cursor.execute("""
            SELECT * FROM debts 
            WHERE employee_name = ? AND status = 'unpaid'
            ORDER BY created_at DESC
        """, (employee_name,))
    else:
        cursor.execute("""
            SELECT * FROM debts 
            WHERE status = 'unpaid'
            ORDER BY created_at DESC
        """)
    
    debts = cursor.fetchall()
    conn.close()
    return debts

def add_message(from_chat_id: int, to_chat_id: int, message_text: str,
               message_type: str = "general", task_id: Optional[int] = None):
    """Add a message record"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO messages (from_chat_id, to_chat_id, message_text, message_type, task_id)
        VALUES (?, ?, ?, ?, ?)
    """, (from_chat_id, to_chat_id, message_text, message_type, task_id))
    
    conn.commit()
    conn.close()

def set_user_state(chat_id: int, state: str, state_data: str = None):
    """Set user conversation state"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT OR REPLACE INTO user_states (chat_id, state, state_data, updated_at)
        VALUES (?, ?, ?, ?)
    """, (chat_id, state, state_data, datetime.now().isoformat()))
    
    conn.commit()
    conn.close()

def get_user_state(chat_id: int) -> Tuple[str, str]:
    """Get user conversation state"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT state, state_data FROM user_states WHERE chat_id = ?
    """, (chat_id,))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return result[0], result[1] or ""
    return "", ""

def clear_user_state(chat_id: int):
    """Clear user conversation state"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM user_states WHERE chat_id = ?", (chat_id,))
    
    conn.commit()
    conn.close()

def get_task_statistics() -> Dict[str, Any]:
    """Get task statistics for reporting"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Total tasks
    cursor.execute("SELECT COUNT(*) FROM tasks")
    total_tasks = cursor.fetchone()[0]
    
    # Tasks by status
    cursor.execute("""
        SELECT status, COUNT(*) FROM tasks GROUP BY status
    """)
    status_counts = dict(cursor.fetchall())
    
    # Total payments
    cursor.execute("SELECT SUM(received_amount) FROM tasks WHERE status = 'completed'")
    total_payments = cursor.fetchone()[0] or 0
    
    # Total debts
    cursor.execute("SELECT SUM(amount) FROM debts WHERE status = 'unpaid'")
    total_debts = cursor.fetchone()[0] or 0
    
    conn.close()
    
    return {
        "total_tasks": total_tasks,
        "status_counts": status_counts,
        "total_payments": total_payments,
        "total_debts": total_debts
    }

def add_customer_inquiry(customer_name: str, inquiry_text: str, customer_phone: str = None, 
                        customer_username: str = None, chat_id: int = None, location_lat: float = None, 
                        location_lon: float = None, location_address: str = None, 
                        inquiry_type: str = 'bot', source: str = 'telegram') -> int:
    """Add a new customer inquiry"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO customer_inquiries 
        (customer_name, customer_phone, customer_username, chat_id, inquiry_text, 
         inquiry_type, location_lat, location_lon, location_address, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (customer_name, customer_phone, customer_username, chat_id, inquiry_text,
          inquiry_type, location_lat, location_lon, location_address, source))
    inquiry_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return inquiry_id

def get_customer_inquiries(status: str = None, source: str = None) -> List[Tuple]:
    """Get customer inquiries with optional filtering"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    query = "SELECT * FROM customer_inquiries"
    params = []
    conditions = []
    
    if status:
        conditions.append("status = ?")
        params.append(status)
    
    if source:
        conditions.append("source = ?")
        params.append(source)
    
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    query += " ORDER BY created_at DESC"
    
    cursor.execute(query, params)
    inquiries = cursor.fetchall()
    conn.close()
    return inquiries

def respond_to_inquiry(inquiry_id: int, admin_response: str) -> Optional[Tuple]:
    """Add admin response to customer inquiry"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE customer_inquiries 
        SET admin_response = ?, status = 'responded', responded_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (admin_response, inquiry_id))
    conn.commit()
    
    # Get inquiry details for notification
    cursor.execute("""
        SELECT customer_name, chat_id, inquiry_text, customer_phone, source
        FROM customer_inquiries WHERE id = ?
    """, (inquiry_id,))
    inquiry_details = cursor.fetchone()
    conn.close()
    return inquiry_details

def get_inquiry_by_id(inquiry_id: int) -> Optional[Tuple]:
    """Get specific inquiry by ID"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM customer_inquiries WHERE id = ?", (inquiry_id,))
    inquiry = cursor.fetchone()
    conn.close()
    return inquiry

def get_task_by_id(task_id: int) -> Optional[Tuple]:
    """Get specific task by ID"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    task = cursor.fetchone()
    conn.close()
    return task

# Initialize database on import
if not os.path.exists(DATABASE_PATH):
    init_database()