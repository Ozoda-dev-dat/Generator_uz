import sqlite3
from datetime import datetime
from typing import List, Dict, Optional
import os

class DatabaseModel:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database tables"""
        pass
    
    def get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)

class TaskModel(DatabaseModel):
    def __init__(self, db_path: str = "tasks.db"):
        super().__init__(db_path)
    
    def init_database(self):
        """Initialize tasks database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vazifa TEXT NOT NULL,
                manzil TEXT NOT NULL,
                xodim TEXT NOT NULL,
                summa REAL NOT NULL,
                telefon TEXT,
                status TEXT DEFAULT 'Davom etmoqda',
                sana TEXT NOT NULL,
                vaqt TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()
    
    def add_task(self, description: str, location: str, employee: str, 
                 amount: float, phone: str = "Telefon yo'q") -> bool:
        """Add new task to database"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            now = datetime.now()
            cursor.execute("""
                INSERT INTO tasks (vazifa, manzil, xodim, summa, telefon, status, sana, vaqt)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (description, location, employee, amount, phone, "⏳ Davom etmoqda", 
                  now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S")))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Task qo'shishda xato: {e}")
            return False
    
    def get_tasks_by_employee(self, employee: str, status: str = None) -> List[Dict]:
        """Get tasks for specific employee"""
        conn = self.get_connection()
        cursor = conn.cursor()
        if status:
            cursor.execute("""
                SELECT id, vazifa, manzil, summa, telefon, status, sana, vaqt 
                FROM tasks WHERE xodim = ? AND status = ?
            """, (employee, status))
        else:
            cursor.execute("""
                SELECT id, vazifa, manzil, summa, telefon, status, sana, vaqt 
                FROM tasks WHERE xodim = ?
            """, (employee,))
        
        rows = cursor.fetchall()
        conn.close()
        
        tasks = []
        for row in rows:
            tasks.append({
                'id': row[0],
                'description': row[1],
                'location': row[2],
                'amount': row[3],
                'phone': row[4],
                'status': row[5],
                'date': row[6],
                'time': row[7]
            })
        return tasks
    
    def update_task_status(self, task_id: int, status: str) -> bool:
        """Update task status"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE tasks SET status = ? WHERE id = ?", (status, task_id))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Status yangilashda xato: {e}")
            return False
    
    def get_tasks_in_date_range(self, employee: str, start_date: str, end_date: str, status: str = "✅ Bajarildi") -> List[Dict]:
        """Get tasks in date range"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT vazifa, manzil, summa, sana FROM tasks
            WHERE xodim = ? AND status = ? AND sana BETWEEN ? AND ?
        """, (employee, status, start_date, end_date))
        rows = cursor.fetchall()
        conn.close()
        
        tasks = []
        for row in rows:
            tasks.append({
                'description': row[0],
                'location': row[1],
                'amount': row[2],
                'date': row[3]
            })
        return tasks

class DebtModel(DatabaseModel):
    def __init__(self, db_path: str = "qarzdorlik.db"):
        super().__init__(db_path)
    
    def init_database(self):
        """Initialize debt database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS debts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_name TEXT NOT NULL,
                amount REAL NOT NULL,
                reason TEXT NOT NULL,
                date TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()
    
    def add_debt(self, employee_name: str, amount: float, reason: str) -> bool:
        """Add debt record"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            date = datetime.now().strftime("%Y-%m-%d")
            cursor.execute("""
                INSERT INTO debts (employee_name, amount, reason, date)
                VALUES (?, ?, ?, ?)
            """, (employee_name, amount, reason, date))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Qarz qo'shishda xato: {e}")
            return False
    
    def get_debts_by_employee(self, employee_name: str) -> List[Dict]:
        """Get debts for specific employee"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT amount, reason, date FROM debts WHERE employee_name = ?
        """, (employee_name,))
        rows = cursor.fetchall()
        conn.close()
        
        debts = []
        for row in rows:
            debts.append({
                'amount': row[0],
                'reason': row[1],
                'date': row[2]
            })
        return debts
    
    def get_total_debt(self, employee_name: str) -> float:
        """Get total debt for employee"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT SUM(amount) FROM debts WHERE employee_name = ?
        """, (employee_name,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result[0] else 0.0
