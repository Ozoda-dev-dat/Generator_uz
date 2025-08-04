from models import TaskModel, DebtModel
import os

def init_all_databases():
    """Initialize all databases"""
    # Create directories if they don't exist
    os.makedirs("hisobotlar", exist_ok=True)
    
    # Initialize databases
    task_db = TaskModel()
    debt_db = DebtModel()
    
    return task_db, debt_db

def get_task_db():
    """Get task database instance"""
    return TaskModel()

def get_debt_db():
    """Get debt database instance"""
    return DebtModel()
