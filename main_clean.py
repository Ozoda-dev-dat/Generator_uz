#!/usr/bin/env python3
"""
Enhanced Telegram Task Management Bot - Production Ready
Optimized for Render.com hosting with simplified structure
"""

import telebot
import sqlite3
import json
import os
from datetime import datetime
import threading
import time
from openpyxl import Workbook
from config import EMPLOYEES

# Environment variables
BOT_TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_CHAT_ID = int(os.environ.get('ADMIN_CHAT_ID', '7792775986'))
ADMIN_CODE = os.environ.get('ADMIN_CODE', '1234')

if not BOT_TOKEN:
    print("❌ BOT_TOKEN environment variable not found!")
    exit(1)

# Initialize bot
bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)

# Database setup
def init_database():
    """Initialize SQLite database"""
    conn = sqlite3.connect('task_management.db', check_same_thread=False)
    c = conn.cursor()
    
    # Tasks table
    c.execute('''CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT,
                    assigned_to TEXT NOT NULL,
                    assigned_by INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'pending',
                    completed_at TIMESTAMP,
                    payment_amount REAL DEFAULT 0,
                    completion_proof TEXT,
                    location_lat REAL,
                    location_lon REAL
                )''')
    
    # Debts table  
    c.execute('''CREATE TABLE IF NOT EXISTS debts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    person_name TEXT NOT NULL,
                    amount REAL NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_paid BOOLEAN DEFAULT FALSE,
                    paid_at TIMESTAMP
                )''')
    
    # User states table
    c.execute('''CREATE TABLE IF NOT EXISTS user_states (
                    chat_id INTEGER PRIMARY KEY,
                    state TEXT,
                    data TEXT
                )''')
    
    conn.commit()
    conn.close()

# Initialize database
init_database()

def get_db():
    """Get database connection"""
    return sqlite3.connect('task_management.db', check_same_thread=False)

# Start command
@bot.message_handler(commands=['start'])
def start_message(message):
    """Handle start command"""
    chat_id = message.chat.id
    
    if chat_id == ADMIN_CHAT_ID:
        bot.send_message(chat_id, "👋 Admin panel", reply_markup=get_admin_keyboard())
    else:
        # Check if user is employee
        employee = next((emp for emp in EMPLOYEES if emp.get('chat_id') == chat_id), None)
        if employee:
            bot.send_message(chat_id, f"👋 Xodim paneli - {employee['name']}", 
                           reply_markup=get_employee_keyboard())
        else:
            bot.send_message(chat_id, "❌ Sizga ruxsat berilmagan")

def get_admin_keyboard():
    """Get admin keyboard markup"""
    from telebot import types
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("📋 Vazifalar", "👥 Xodimlar")
    keyboard.add("💰 Qarzlar", "📊 Hisobotlar") 
    return keyboard

def get_employee_keyboard():
    """Get employee keyboard markup"""
    from telebot import types
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("📋 Mening vazifalarim")
    keyboard.add("✅ Vazifani yakunlash")
    return keyboard

# Message handlers
@bot.message_handler(func=lambda message: message.text == "📋 Vazifalar" and message.chat.id == ADMIN_CHAT_ID)
def admin_tasks(message):
    """Show admin tasks menu"""
    from telebot import types
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("➕ Yangi vazifa", callback_data="new_task"))
    keyboard.add(types.InlineKeyboardButton("📋 Barcha vazifalar", callback_data="all_tasks"))
    keyboard.add(types.InlineKeyboardButton("⏳ Kutilayotgan", callback_data="pending_tasks"))
    keyboard.add(types.InlineKeyboardButton("✅ Yakunlangan", callback_data="completed_tasks"))
    
    bot.send_message(message.chat.id, "📋 Vazifalar bo'limi:", reply_markup=keyboard)

@bot.message_handler(func=lambda message: message.text == "📋 Mening vazifalarim")
def employee_tasks(message):
    """Show employee tasks"""
    chat_id = message.chat.id
    employee = next((emp for emp in EMPLOYEES if emp.get('chat_id') == chat_id), None)
    
    if not employee:
        bot.send_message(chat_id, "❌ Xodim topilmadi")
        return
    
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM tasks WHERE assigned_to = ? AND status != 'completed' ORDER BY created_at DESC", 
              (employee['name'],))
    tasks = c.fetchall()
    conn.close()
    
    if not tasks:
        bot.send_message(chat_id, "📭 Sizga hozircha vazifa berilmagan")
        return
    
    response = "📋 **Sizning vazifalaringiz:**\n\n"
    for task in tasks:
        response += f"🆔 #{task[0]} - {task[1]}\n"
        response += f"📝 {task[2] or 'Tavsif yo\'q'}\n"
        response += f"📅 {task[5]}\n"
        if task[9]:
            response += f"💰 {task[9]} so'm\n"
        response += f"📊 {task[6].upper()}\n\n"
    
    bot.send_message(chat_id, response, parse_mode='Markdown')

# Callback query handler
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    """Handle callback queries"""
    if call.data == "new_task":
        bot.send_message(call.message.chat.id, "📝 Yangi vazifa yaratish...\nVazifa nomini kiriting:")
        set_user_state(call.message.chat.id, "creating_task", {})
    elif call.data == "all_tasks":
        show_all_tasks(call.message.chat.id)

def show_all_tasks(chat_id):
    """Show all tasks"""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM tasks ORDER BY created_at DESC LIMIT 10")
    tasks = c.fetchall()
    conn.close()
    
    if not tasks:
        bot.send_message(chat_id, "📭 Hozircha vazifa yo'q")
        return
    
    response = "📋 **Barcha vazifalar (oxirgi 10):**\n\n"
    for task in tasks:
        status_emoji = "⏳" if task[6] == "pending" else "✅" if task[6] == "completed" else "🔄"
        response += f"{status_emoji} #{task[0]} - {task[1]}\n"
        response += f"👤 {task[3]}\n"
        response += f"📅 {task[5]}\n\n"
    
    bot.send_message(chat_id, response, parse_mode='Markdown')

def set_user_state(chat_id, state, data):
    """Set user state"""
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO user_states (chat_id, state, data) VALUES (?, ?, ?)",
              (chat_id, state, json.dumps(data)))
    conn.commit()
    conn.close()

def get_user_state(chat_id):
    """Get user state"""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT state, data FROM user_states WHERE chat_id = ?", (chat_id,))
    result = c.fetchone()
    conn.close()
    
    if result:
        return result[0], json.loads(result[1] or '{}')
    return None, {}

# Text message handler
@bot.message_handler(content_types=['text'])
def handle_text(message):
    """Handle text messages"""
    chat_id = message.chat.id
    state, data = get_user_state(chat_id)
    
    if state == "creating_task":
        data['title'] = message.text
        set_user_state(chat_id, "task_description", data)
        bot.send_message(chat_id, "📝 Vazifa tavsifini kiriting:")
    elif state == "task_description":
        data['description'] = message.text
        # Show employee selection
        from telebot import types
        keyboard = types.InlineKeyboardMarkup()
        for emp in EMPLOYEES:
            keyboard.add(types.InlineKeyboardButton(emp['name'], 
                        callback_data=f"assign_{emp['name']}"))
        
        set_user_state(chat_id, "selecting_employee", data)
        bot.send_message(chat_id, "👥 Xodimni tanlang:", reply_markup=keyboard)

# Callback for employee selection
@bot.callback_query_handler(func=lambda call: call.data.startswith('assign_'))
def assign_task(call):
    """Assign task to employee"""
    employee_name = call.data.replace('assign_', '')
    state, data = get_user_state(call.message.chat.id)
    
    if state == "selecting_employee":
        # Create task
        conn = get_db()
        c = conn.cursor()
        c.execute("""INSERT INTO tasks (title, description, assigned_to, assigned_by, status) 
                     VALUES (?, ?, ?, ?, 'pending')""",
                  (data['title'], data['description'], employee_name, call.message.chat.id))
        task_id = c.lastrowid
        conn.commit()
        conn.close()
        
        # Clear user state
        set_user_state(call.message.chat.id, None, {})
        
        # Notify admin
        bot.edit_message_text(
            f"✅ Vazifa yaratildi!\n\n"
            f"🆔 #{task_id}\n"
            f"📝 {data['title']}\n"
            f"👤 {employee_name}",
            call.message.chat.id,
            call.message.message_id
        )
        
        # Notify employee
        employee = next((emp for emp in EMPLOYEES if emp['name'] == employee_name), None)
        if employee and employee.get('chat_id'):
            bot.send_message(
                employee['chat_id'],
                f"📬 **Yangi vazifa!**\n\n"
                f"🆔 #{task_id}\n"
                f"📝 {data['title']}\n"
                f"📄 {data['description']}\n\n"
                f"✅ Vazifani bajarish uchun menuni ishlatng!",
                parse_mode='Markdown'
            )

def start_bot():
    """Start the bot with error handling"""
    print("🚀 Enhanced Telegram Task Management Bot ishga tushmoqda...")
    print(f"🔑 Bot Token: {'✅ Mavjud' if BOT_TOKEN else '❌ Mavjud emas'}")
    print(f"👑 Admin chat ID: {ADMIN_CHAT_ID}")
    print(f"👥 Xodimlar soni: {len(EMPLOYEES)}")
    print("📊 Ma'lumotlar bazasi tayyorlandi")
    print("✅ Bot muvaffaqiyatli ishga tushdi!")
    
    while True:
        try:
            bot.infinity_polling(none_stop=True, interval=2, timeout=30, long_polling_timeout=90)
        except Exception as e:
            print(f"⚠️ Bot xatolik: {e}")
            print("🔄 5 soniyadan keyin qayta ulanish...")
            time.sleep(5)

if __name__ == "__main__":
    start_bot()
