#!/usr/bin/env python3
"""
Enhanced Telegram Task Management Bot - FIXED VERSION
All handlers properly registered with global bot instance
"""

import telebot
from telebot import types
import json
import os
import sys
from datetime import datetime, timedelta

from config import BOT_TOKEN, ADMIN_CODE, ADMIN_CHAT_ID, EMPLOYEES
from database import (
    init_database, add_task, get_employee_tasks, update_task_status, add_debt, get_debts,
    add_message, get_user_state, set_user_state, clear_user_state,
    add_customer_inquiry, get_customer_inquiries, respond_to_inquiry, get_inquiry_by_id, get_task_by_id
)
from utils import (
    save_media_file, generate_employee_report, generate_admin_report,
    format_task_info, parse_json_data, serialize_json_data, ensure_directories
)

# Initialize bot globally
bot = telebot.TeleBot(BOT_TOKEN)
admin_data = {}

# Delete webhook to ensure polling works
try:
    bot.delete_webhook()
except Exception as e:
    print(f"⚠️ Webhook deletion warning: {e}")

# Initialize database and directories
init_database()
ensure_directories()

# START COMMAND
@bot.message_handler(commands=['start'])
def start_message(message):
    """Start message with role detection"""
    if message.chat.id == ADMIN_CHAT_ID:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("🔐 Admin", "🆔 Chat ID")
        
        bot.send_message(
            message.chat.id,
            "👋 Salom! Admin paneliga kirish uchun \"🔐 Admin\" tugmasini bosing.",
            reply_markup=markup
        )
    elif message.chat.id in EMPLOYEES.values():
        # Find employee name
        employee_name = None
        for name, chat_id in EMPLOYEES.items():
            if chat_id == message.chat.id:
                employee_name = name
                break
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("👤 Xodim", "🆔 Chat ID")
        
        bot.send_message(
            message.chat.id,
            f"👋 Salom, {employee_name}!\n\nXodim paneliga kirish uchun \"👤 Xodim\" tugmasini bosing.",
            reply_markup=markup
        )
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("🎯 Mijoz", "🆔 Chat ID")
        
        bot.send_message(
            message.chat.id,
            "👋 Assalomu alaykum!\n\nBiz bilan bog'lanish uchun \"🎯 Mijoz\" tugmasini bosing.",
            reply_markup=markup
        )

@bot.message_handler(func=lambda message: message.text == "🆔 Chat ID")
def send_chat_id(message):
    """Send user's chat ID"""
    bot.reply_to(message, f"🆔 Sizning chat ID'ingiz: `{message.chat.id}`", parse_mode='Markdown')

# ADMIN SECTION
@bot.message_handler(func=lambda message: message.text == "🔐 Admin")
def admin_login(message):
    """Admin login process"""
    set_user_state(message.chat.id, "admin_login")
    
    markup = types.ReplyKeyboardRemove()
    bot.send_message(
        message.chat.id,
        "🔑 Admin kodini kiriting:",
        reply_markup=markup
    )

@bot.message_handler(func=lambda message: get_user_state(message.chat.id)[0] == "admin_login")
def verify_admin_code(message):
    """Verify admin code"""
    if message.text == ADMIN_CODE:
        clear_user_state(message.chat.id)
        bot.send_message(message.chat.id, "✅ Muvaffaqiyatli kirildi!")
        show_admin_panel(message)
    else:
        bot.send_message(message.chat.id, "❌ Noto'g'ri kod. Qaytadan urinib ko'ring:")

def show_admin_panel(message):
    """Show admin panel with quick action floating buttons"""
    # Main admin panel buttons
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("➕ Yangi xodim qo'shish", "📤 Vazifa berish")
    markup.add("📍 Xodimlarni kuzatish", "👥 Mijozlar so'rovlari")
    markup.add("💸 Qarzlar", "📊 Ma'lumotlar")
    markup.add("🔙 Ortga")
    
    bot.send_message(
        message.chat.id,
        "🛠 Admin paneli\n\nKerakli bo'limni tanlang:",
        reply_markup=markup
    )
    
    # Send quick action floating buttons as inline keyboard
    quick_markup = types.InlineKeyboardMarkup(row_width=4)
    quick_markup.add(
        types.InlineKeyboardButton("⚡ Tezkor vazifa", callback_data="quick_task"),
        types.InlineKeyboardButton("📊 Tezkor hisobot", callback_data="quick_report"), 
        types.InlineKeyboardButton("🔍 Tezkor qidiruv", callback_data="quick_search"),
        types.InlineKeyboardButton("📢 Umumiy xabar", callback_data="broadcast_message")
    )
    
    bot.send_message(
        message.chat.id,
        "⚡ **Tezkor Harakatlar**\n\nEng ko'p ishlatiladigan funksiyalar:",
        reply_markup=quick_markup,
        parse_mode='Markdown'
    )

@bot.message_handler(func=lambda message: message.text == "📤 Vazifa berish")
def start_task_assignment(message):
    """Start task assignment process"""
    if message.chat.id != ADMIN_CHAT_ID:
        bot.send_message(message.chat.id, "❌ Bu funksiya faqat admin uchun!")
        return
        
    if len(EMPLOYEES) == 0:
        bot.send_message(message.chat.id, "❌ Hech qanday xodim topilmadi!")
        return
    
    set_user_state(message.chat.id, "assign_task_description")
    admin_data[message.chat.id] = {}
    
    markup = types.ReplyKeyboardRemove()
    bot.send_message(
        message.chat.id,
        "📝 Vazifa tavsifini kiriting:",
        reply_markup=markup
    )

@bot.message_handler(func=lambda message: get_user_state(message.chat.id)[0] == "assign_task_description")
def get_task_description(message):
    """Get task description"""
    if message.chat.id not in admin_data:
        admin_data[message.chat.id] = {}
        
    admin_data[message.chat.id]["description"] = message.text
    set_user_state(message.chat.id, "assign_task_payment")
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("💰 To'lov miqdorini kiriting")
    markup.add("⏭ To'lov belgilanmagan")
    markup.add("🔙 Bekor qilish")
    
    bot.send_message(
        message.chat.id,
        "💰 To'lov miqdorini tanlang:",
        reply_markup=markup
    )

@bot.message_handler(func=lambda message: get_user_state(message.chat.id)[0] == "assign_task_payment")
def get_task_payment(message):
    """Handle task payment selection"""
    if message.text == "🔙 Bekor qilish":
        clear_user_state(message.chat.id)
        show_admin_panel(message)
        return
    
    if message.text == "💰 To'lov miqdorini kiriting":
        set_user_state(message.chat.id, "assign_task_payment_amount")
        markup = types.ReplyKeyboardRemove()
        bot.send_message(
            message.chat.id,
            "💰 To'lov miqdorini kiriting (so'mda):",
            reply_markup=markup
        )
    elif message.text == "⏭ To'lov belgilanmagan":
        if message.chat.id not in admin_data:
            admin_data[message.chat.id] = {}
        admin_data[message.chat.id]["payment"] = None
        proceed_to_employee_selection(message)
    else:
        bot.send_message(message.chat.id, "❌ Iltimos, tugmalardan birini tanlang!")

@bot.message_handler(func=lambda message: get_user_state(message.chat.id)[0] == "assign_task_payment_amount")
def get_task_payment_amount(message):
    """Get specific payment amount"""
    try:
        payment = float(message.text.replace(" ", "").replace(",", ""))
        
        if message.chat.id not in admin_data:
            admin_data[message.chat.id] = {}
        admin_data[message.chat.id]["payment"] = payment
        proceed_to_employee_selection(message)
        
    except ValueError:
        bot.send_message(message.chat.id, "❌ Noto'g'ri format. Raqam kiriting (masalan: 50000):")

def proceed_to_employee_selection(message):
    """Proceed to employee selection step"""
    set_user_state(message.chat.id, "assign_task_employee")
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    for employee_name in EMPLOYEES.keys():
        markup.add(employee_name)
    markup.add("🔙 Bekor qilish")
    
    bot.send_message(
        message.chat.id,
        "👥 Vazifani bajaradigan xodimni tanlang:",
        reply_markup=markup
    )

@bot.message_handler(func=lambda message: get_user_state(message.chat.id)[0] == "assign_task_employee")
def select_task_employee(message):
    """Select employee for task"""
    if message.text == "🔙 Bekor qilish":
        clear_user_state(message.chat.id)
        show_admin_panel(message)
        return
    
    if message.text in EMPLOYEES:
        if message.chat.id not in admin_data:
            admin_data[message.chat.id] = {}
        admin_data[message.chat.id]["employee"] = message.text
        
        # Create task in database
        data = admin_data[message.chat.id]
        task_id = add_task(
            description=data["description"],
            location_lat=None,
            location_lon=None,
            location_address="Admindan tayinlangan",
            payment_amount=data["payment"],
            assigned_to=data["employee"],
            assigned_by=message.chat.id
        )
        
        # Send task to employee
        employee_chat_id = EMPLOYEES[data["employee"]]
        
        # Format payment info
        if data["payment"] is not None:
            payment_text = f"💰 To'lov: {data['payment']} so'm"
        else:
            payment_text = "💰 To'lov: Belgilanmagan"
        
        task_text = f"""
🔔 Sizga yangi vazifa tayinlandi!

📝 Vazifa: {data['description']}
{payment_text}
📅 Vaqt: {datetime.now().strftime('%d.%m.%Y %H:%M')}

Vazifani boshlash uchun "👤 Xodim" tugmasini bosing va vazifalar ro'yxatini ko'ring.
"""
        
        try:
            bot.send_message(employee_chat_id, task_text)
            
            bot.send_message(
                message.chat.id,
                f"✅ Vazifa muvaffaqiyatli yuborildi!\n\n"
                f"👤 Xodim: {data['employee']}\n"
                f"🆔 Vazifa ID: {task_id}"
            )
            
        except Exception as e:
            bot.send_message(
                message.chat.id,
                f"❌ Xodimga vazifa yetkazib berishda xatolik:\n{str(e)}"
            )
        
        clear_user_state(message.chat.id)
        admin_data.pop(message.chat.id, None)
        show_admin_panel(message)
        
    else:
        bot.send_message(message.chat.id, "❌ Iltimos, ro'yxatdan xodim tanlang!")

# EMPLOYEE SECTION
@bot.message_handler(func=lambda message: message.text == "👤 Xodim")
def employee_login(message):
    """Employee login"""
    # Find employee name
    employee_name = None
    for name, chat_id in EMPLOYEES.items():
        if chat_id == message.chat.id:
            employee_name = name
            break
    
    if not employee_name:
        bot.send_message(
            message.chat.id,
            "❌ Siz xodimlar ro'yxatida yo'qsiz.\n"
            "Admin bilan bog'laning yoki '🎯 Mijoz' bo'limidan foydalaning."
        )
        return
    
    show_employee_panel(message, employee_name)

def show_employee_panel(message, employee_name=None):
    """Show employee panel with quick action floating buttons"""
    if not employee_name:
        for name, chat_id in EMPLOYEES.items():
            if chat_id == message.chat.id:
                employee_name = name
                break
    
    if not employee_name:
        bot.send_message(message.chat.id, "❌ Profil topilmadi.")
        return
    
    # Main employee panel buttons
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📌 Mening vazifalarim", "📂 Vazifalar tarixi")
    markup.add("📊 Hisobotlar")
    markup.add("🔙 Ortga")
    
    bot.send_message(
        message.chat.id,
        f"👤 Xodim paneli\n\nSalom, {employee_name}!\n\nKerakli bo'limni tanlang:",
        reply_markup=markup
    )
    
    # Send employee quick action floating buttons
    quick_markup = types.InlineKeyboardMarkup(row_width=3)
    quick_markup.add(
        types.InlineKeyboardButton("🚀 Faol vazifalar", callback_data="quick_active_tasks"),
        types.InlineKeyboardButton("📍 Joylashuvni yuborish", callback_data="quick_location"),
        types.InlineKeyboardButton("📝 Tezkor hisobot", callback_data="quick_employee_report")
    )
    quick_markup.add(
        types.InlineKeyboardButton("💬 Admin bilan aloqa", callback_data="contact_admin"),
        types.InlineKeyboardButton("📈 Mening statistikam", callback_data="my_stats")
    )
    
    bot.send_message(
        message.chat.id,
        f"⚡ **Tezkor Harakatlar - {employee_name}**\n\nEng muhim funksiyalar:",
        reply_markup=quick_markup,
        parse_mode='Markdown'
    )

@bot.message_handler(func=lambda message: message.text == "📌 Mening vazifalarim")
def show_employee_tasks(message):
    """Show employee's current tasks"""
    employee_name = None
    for name, chat_id in EMPLOYEES.items():
        if chat_id == message.chat.id:
            employee_name = name
            break
    
    if not employee_name:
        bot.send_message(message.chat.id, "❌ Profil topilmadi.")
        return
    
    # Get pending and in-progress tasks
    pending_tasks = get_employee_tasks(employee_name, "pending")
    active_tasks = get_employee_tasks(employee_name, "in_progress")
    
    if not pending_tasks and not active_tasks:
        bot.send_message(message.chat.id, "📭 Sizda hozircha vazifa yo'q.")
        return
    
    # Show pending tasks
    if pending_tasks:
        bot.send_message(message.chat.id, "⏳ Kutilayotgan vazifalar:")
        for task in pending_tasks:
            task_info = format_task_info(task)
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("▶️ Boshlash", callback_data=f"start_task_{task[0]}"))
            
            bot.send_message(message.chat.id, task_info, reply_markup=markup, parse_mode='Markdown')
    
    # Show active tasks
    if active_tasks:
        bot.send_message(message.chat.id, "🔄 Faol vazifalar:")
        for task in active_tasks:
            task_info = format_task_info(task)
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("✅ Tugatish", callback_data=f"complete_task_{task[0]}"))
            
            bot.send_message(message.chat.id, task_info, reply_markup=markup, parse_mode='Markdown')

# CUSTOMER SECTION
@bot.message_handler(func=lambda message: message.text == "🎯 Mijoz")
def customer_start(message):
    """Customer start menu"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📞 Telefon raqamni ulashish", "📍 Joylashuvni ulashish")
    markup.add("💬 So'rov yuborish", "🔙 Bekor qilish")
    
    set_user_state(message.chat.id, "customer_contact_start")
    
    bot.send_message(
        message.chat.id,
        "👋 Assalomu alaykum!\n\n"
        "Biz bilan bog'langaningizdan xursandmiz. So'rovingizni to'liq ko'rib chiqishimiz uchun:\n\n"
        "1️⃣ Telefon raqamingizni ulashing\n"
        "2️⃣ Joylashuvingizni ulashing\n"
        "3️⃣ So'rovingizni yozing\n\n"
        "Qaysi bosqichdan boshlaysiz?",
        reply_markup=markup
    )

@bot.message_handler(func=lambda message: message.text == "💬 So'rov yuborish")
def customer_inquiry_start(message):
    """Start customer inquiry process"""
    set_user_state(message.chat.id, "writing_inquiry")
    
    markup = types.ReplyKeyboardRemove()
    bot.send_message(
        message.chat.id,
        "✍️ So'rovingizni batafsil yozing:",
        reply_markup=markup
    )

@bot.message_handler(func=lambda message: get_user_state(message.chat.id)[0] == "writing_inquiry")
def handle_customer_inquiry(message):
    """Handle customer inquiry submission"""
    # Get customer data if available
    state, data = get_user_state(message.chat.id)
    customer_data = {}
    
    if data:
        try:
            customer_data = json.loads(data)
        except:
            pass
    
    # Default customer info
    if not customer_data:
        last_name = message.from_user.last_name or ''
        full_name = message.from_user.first_name + (' ' + last_name if last_name else '')
        customer_data = {
            'name': full_name,
            'username': message.from_user.username
        }
    
    # Add inquiry to database
    inquiry_id = add_customer_inquiry(
        customer_name=customer_data.get('name', 'Noma\'lum'),
        customer_phone=customer_data.get('phone', ''),
        customer_username=customer_data.get('username', ''),
        location_lat=customer_data.get('location_lat'),
        location_lon=customer_data.get('location_lon'),
        inquiry_text=message.text,
        source='telegram',
        customer_chat_id=message.chat.id
    )
    
    # Send confirmation to customer
    bot.send_message(
        message.chat.id,
        "✅ So'rovingiz qabul qilindi!\n\n"
        f"🔢 So'rov raqami: #{inquiry_id}\n"
        "📞 Tez orada siz bilan bog'lanamiz.\n\n"
        "Rahmat!",
        reply_markup=types.ReplyKeyboardRemove()
    )
    
    # Notify admin
    admin_message = f"""
🔔 Yangi mijoz so'rovi!

🆔 So'rov ID: #{inquiry_id}
👤 Mijoz: {customer_data.get('name', 'Nomalum')}
📞 Telefon: {customer_data.get('phone', 'Berilmagan')}
👤 Username: @{customer_data.get('username', 'Yoq')}
💬 So'rov: {message.text}

📍 Joylashuv: {'✅ Berilgan' if customer_data.get('location_lat') else '❌ Berilmagan'}
"""
    
    bot.send_message(ADMIN_CHAT_ID, admin_message)
    
    clear_user_state(message.chat.id)
    start_message(message)

# QUICK ACTION HANDLERS FOR MESSAGES
@bot.message_handler(func=lambda message: get_user_state(message.chat.id)[0] == "quick_task_description")
def handle_quick_task_description(message):
    """Handle quick task description"""
    if message.chat.id not in admin_data:
        admin_data[message.chat.id] = {"quick_mode": True}
    
    admin_data[message.chat.id]["description"] = message.text
    admin_data[message.chat.id]["payment"] = None  # Quick tasks have no payment
    
    # Proceed directly to employee selection for quick mode
    proceed_to_employee_selection(message)

@bot.message_handler(func=lambda message: get_user_state(message.chat.id)[0] == "quick_search_query")
def handle_quick_search(message):
    """Handle quick search query"""
    query = message.text.strip().lower()
    
    try:
        import sqlite3
        conn = sqlite3.connect('task_management.db')
        cursor = conn.cursor()
        
        results = []
        
        # Search in tasks
        cursor.execute("""
            SELECT 'Vazifa' as type, id, description, assigned_to, status 
            FROM tasks WHERE LOWER(description) LIKE ? OR LOWER(assigned_to) LIKE ?
            LIMIT 10
        """, (f'%{query}%', f'%{query}%'))
        results.extend(cursor.fetchall())
        
        # Search in customer inquiries
        cursor.execute("""
            SELECT 'Mijoz' as type, id, customer_name, inquiry_text, status
            FROM customer_inquiries WHERE LOWER(customer_name) LIKE ? OR LOWER(inquiry_text) LIKE ?
            LIMIT 10
        """, (f'%{query}%', f'%{query}%'))
        results.extend(cursor.fetchall())
        
        conn.close()
        
        if results:
            result_text = f"🔍 **Qidiruv natijalari: '{query}'**\n\n"
            for result in results:
                result_text += f"📋 **{result[0]}** #{result[1]}\n"
                if result[0] == 'Vazifa':
                    result_text += f"📝 {result[2][:50]}...\n"
                    result_text += f"👤 {result[3]} - {result[4]}\n\n"
                else:
                    result_text += f"👤 {result[2]}\n"
                    result_text += f"💬 {result[3][:50]}...\n\n"
        else:
            result_text = f"❌ '{query}' bo'yicha hech narsa topilmadi"
        
        bot.send_message(message.chat.id, result_text, parse_mode='Markdown')
        
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Qidiruv xatoligi: {str(e)}")
    
    clear_user_state(message.chat.id)

@bot.message_handler(func=lambda message: get_user_state(message.chat.id)[0] == "broadcast_message")
def handle_broadcast_message(message):
    """Handle broadcast message to all employees"""
    broadcast_text = f"""
📢 **Admin xabari**

{message.text}

📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}
"""
    
    success_count = 0
    failed_count = 0
    
    for employee_name, chat_id in EMPLOYEES.items():
        try:
            bot.send_message(chat_id, broadcast_text, parse_mode='Markdown')
            success_count += 1
        except Exception as e:
            failed_count += 1
            print(f"Broadcast failed for {employee_name}: {e}")
    
    bot.send_message(
        message.chat.id,
        f"📢 **Xabar yuborildi**\n\n"
        f"✅ Muvaffaqiyatli: {success_count} xodim\n"
        f"❌ Xatolik: {failed_count} xodim",
        parse_mode='Markdown'
    )
    
    clear_user_state(message.chat.id)

@bot.message_handler(func=lambda message: get_user_state(message.chat.id)[0] == "contact_admin_message")
def handle_contact_admin_message(message):
    """Handle employee message to admin"""
    # Find employee name
    employee_name = None
    for name, chat_id in EMPLOYEES.items():
        if chat_id == message.chat.id:
            employee_name = name
            break
    
    admin_message = f"""
💬 **Xodimdan xabar**

👤 **Xodim:** {employee_name or "Noma'lum"}
💬 **Xabar:** {message.text}
📅 **Vaqt:** {datetime.now().strftime('%d.%m.%Y %H:%M')}

Javob berish uchun: /reply {message.chat.id} [xabar]
"""
    
    try:
        bot.send_message(ADMIN_CHAT_ID, admin_message, parse_mode='Markdown')
        bot.send_message(
            message.chat.id,
            "✅ Xabaringiz adminga yuborildi!\n📞 Tez orada javob beriladi."
        )
    except Exception as e:
        bot.send_message(
            message.chat.id,
            f"❌ Xabar yuborishda xatolik: {str(e)}"
        )
    
    clear_user_state(message.chat.id)

@bot.message_handler(content_types=['location'], func=lambda message: get_user_state(message.chat.id)[0] == "quick_location_share")
def handle_quick_location_share(message):
    """Handle quick location sharing from employee"""
    # Find employee name
    employee_name = None
    for name, chat_id in EMPLOYEES.items():
        if chat_id == message.chat.id:
            employee_name = name
            break
    
    # Save location to database
    import sqlite3
    try:
        conn = sqlite3.connect('task_management.db')
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO employee_locations (employee_name, employee_chat_id, latitude, longitude, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (employee_name, message.chat.id, message.location.latitude, message.location.longitude, datetime.now()))
        
        conn.commit()
        conn.close()
        
        # Send confirmation to employee
        bot.send_message(
            message.chat.id,
            "✅ **Joylashuv saqlandi!**\n\nAdmin sizning joylashuvingizni ko'rishi mumkin.",
            parse_mode='Markdown',
            reply_markup=types.ReplyKeyboardRemove()
        )
        
        # Notify admin with location
        admin_message = f"""
📍 **Xodim joylashuvi**

👤 **Xodim:** {employee_name}
📅 **Vaqt:** {datetime.now().strftime('%d.%m.%Y %H:%M')}
🎯 **Tezkor ulashish orqali**
"""
        
        bot.send_message(ADMIN_CHAT_ID, admin_message, parse_mode='Markdown')
        bot.send_location(ADMIN_CHAT_ID, message.location.latitude, message.location.longitude)
        
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Xatolik: {str(e)}")
    
    clear_user_state(message.chat.id)

# BACK HANDLERS
@bot.message_handler(func=lambda message: message.text == "🔙 Ortga")
def go_back(message):
    """Go back to main menu"""
    clear_user_state(message.chat.id)
    start_message(message)

# CALLBACK HANDLERS FOR ORIGINAL TASK ACTIONS
@bot.callback_query_handler(func=lambda call: call.data.startswith('start_task_'))
def start_task_callback(call):
    """Handle start task callback"""
    task_id = int(call.data.split('_')[2])
    
    # Update task status to in_progress
    update_task_status(task_id, "in_progress")
    
    bot.answer_callback_query(call.id, "✅ Vazifa boshlandi!")
    bot.edit_message_text(
        "🔄 Vazifa boshlandi!\n\nVazifani tugatgach, \"✅ Tugatish\" tugmasini bosing.",
        call.message.chat.id,
        call.message.message_id
    )
    
    # Notify admin
    bot.send_message(
        ADMIN_CHAT_ID,
        f"🔄 Vazifa #{task_id} boshlandi!\n👤 Xodim tomonidan qabul qilindi."
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('complete_task_'))
def complete_task_callback(call):
    """Handle complete task callback"""
    task_id = int(call.data.split('_')[2])
    
    set_user_state(call.message.chat.id, "task_completion_report", str(task_id))
    
    bot.answer_callback_query(call.id, "📝 Hisobot yozing")
    bot.send_message(
        call.message.chat.id,
        "📝 Vazifa haqida qisqacha hisobot yozing:",
        reply_markup=types.ReplyKeyboardRemove()
    )

@bot.message_handler(func=lambda message: get_user_state(message.chat.id)[0] == "task_completion_report")
def handle_task_completion(message):
    """Handle task completion report"""
    state, task_id_str = get_user_state(message.chat.id)
    task_id = int(task_id_str)
    
    # Update task status
    update_task_status(task_id, "completed", completion_report=message.text)
    
    # Get employee name
    employee_name = None
    for name, chat_id in EMPLOYEES.items():
        if chat_id == message.chat.id:
            employee_name = name
            break
    
    # Success message to employee
    bot.send_message(
        message.chat.id,
        "✅ Vazifa muvaffaqiyatli yakunlandi!\n\nRahmat!"
    )
    
    # Admin notification
    admin_message = f"""
✅ Vazifa yakunlandi!

🆔 Vazifa ID: {task_id}
👤 Xodim: {employee_name or "Nomalum"}
📝 Hisobot: {message.text}
"""
    
    bot.send_message(ADMIN_CHAT_ID, admin_message)
    
    clear_user_state(message.chat.id)
    show_employee_panel(message)

# ERROR HANDLER
@bot.message_handler(func=lambda message: True)
def handle_unknown(message):
    """Handle unknown messages"""
    bot.send_message(
        message.chat.id,
        "❓ Tushunmadim. Iltimos, menyudan tanlang yoki /start bosing."
    )

def main():
    """Start the bot"""
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN mavjud emas.")
        sys.exit(1)
    
    try:
        print("🚀 Enhanced Telegram Task Management Bot ishga tushmoqda...")
        print(f"🔑 Bot Token: {'✅ Mavjud' if BOT_TOKEN else '❌ Mavjud emas'}")
        print(f"👑 Admin chat ID: {ADMIN_CHAT_ID}")
        print(f"👥 Xodimlar soni: {len(EMPLOYEES)}")
        print("📊 Ma'lumotlar bazasi tayyorlandi")
        print("✅ Bot muvaffaqiyatli ishga tushdi!")
        print("📱 Bot Telegram orqali foydalanishga tayyor")
        print("🛑 Botni to'xtatish uchun Ctrl+C bosing")
        
        # Test handlers
        print(f"📝 Message handlers: {len(bot.message_handlers)}")
        print(f"📞 Callback handlers: {len(bot.callback_query_handlers)}")
        
        bot.infinity_polling(none_stop=True, interval=1, timeout=20)
        
    except KeyboardInterrupt:
        print("\n🛑 Bot to'xtatildi.")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Bot xatosi: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()