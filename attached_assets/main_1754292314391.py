import telebot
from telebot import types
import json
import os
from datetime import datetime, timedelta

from config import BOT_TOKEN, ADMIN_CODE, ADMIN_CHAT_ID, EMPLOYEES
from database import (
    add_task, get_employee_tasks, update_task_status, add_debt, get_debts,
    add_message, get_user_state, set_user_state, clear_user_state
)
from utils import (
    save_media_file, generate_employee_report, generate_admin_report,
    format_task_info, parse_json_data, serialize_json_data
)

# Initialize bot
bot = telebot.TeleBot(BOT_TOKEN)

# Global variables for conversation states
admin_data = {}

@bot.message_handler(commands=['start'])
def start_message(message):
    """Handle /start command"""
    clear_user_state(message.chat.id)
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🔐 Admin", "👤 Xodim")
    
    bot.send_message(
        message.chat.id,
        "🤖 Vazifa boshqaruv botiga xush kelibsiz!\n\n"
        "Iltimos, rolingizni tanlang:",
        reply_markup=markup
    )

@bot.message_handler(commands=['getid'])
def send_chat_id(message):
    """Get user's chat ID"""
    bot.reply_to(message, f"🆔 Sizning chat ID'ingiz: `{message.chat.id}`", parse_mode='Markdown')

# ADMIN SECTION
@bot.message_handler(func=lambda message: message.text == "🔐 Admin")
def admin_login(message):
    """Admin login process"""
    set_user_state(message.chat.id, "admin_login")
    
    markup = types.ReplyKeyboardRemove()
    msg = bot.send_message(
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
    """Show admin panel"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("➕ Yangi xodim qo'shish", "📤 Vazifa berish")
    markup.add("📍 Xodimlarni kuzatish", "📩 Xabarlar")
    markup.add("💸 Qarzlar", "📊 Ma'lumotlar")
    markup.add("🔙 Ortga")
    
    bot.send_message(
        message.chat.id,
        "🛠 Admin panelga xush kelibsiz!\n\nKerakli bo'limni tanlang:",
        reply_markup=markup
    )

@bot.message_handler(func=lambda message: message.text == "📤 Vazifa berish")
def start_task_assignment(message):
    """Start task assignment process"""
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
    admin_data[message.chat.id]["description"] = message.text
    set_user_state(message.chat.id, "assign_task_location")
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    location_btn = types.KeyboardButton("📍 Lokatsiyani yuborish", request_location=True)
    markup.add(location_btn)
    
    bot.send_message(
        message.chat.id,
        "📍 Vazifa uchun lokatsiyani yuboring:",
        reply_markup=markup
    )

@bot.message_handler(content_types=['location'])
def receive_task_location(message):
    """Receive task location"""
    state, _ = get_user_state(message.chat.id)
    
    if state == "assign_task_location":
        admin_data[message.chat.id]["location"] = {
            "latitude": message.location.latitude,
            "longitude": message.location.longitude
        }
        
        set_user_state(message.chat.id, "assign_task_payment")
        
        markup = types.ReplyKeyboardRemove()
        bot.send_message(
            message.chat.id,
            "✅ Lokatsiya qabul qilindi.\n\n💰 To'lov miqdorini kiriting (so'mda):",
            reply_markup=markup
        )

@bot.message_handler(func=lambda message: get_user_state(message.chat.id)[0] == "assign_task_payment")
def get_task_payment(message):
    """Get task payment amount"""
    try:
        payment = float(message.text.replace(" ", "").replace(",", ""))
        admin_data[message.chat.id]["payment"] = payment
        
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
        
    except ValueError:
        bot.send_message(message.chat.id, "❌ Noto'g'ri format. Raqam kiriting (masalan: 50000):")

@bot.message_handler(func=lambda message: get_user_state(message.chat.id)[0] == "assign_task_employee")
def select_task_employee(message):
    """Select employee for task"""
    if message.text == "🔙 Bekor qilish":
        clear_user_state(message.chat.id)
        show_admin_panel(message)
        return
    
    if message.text in EMPLOYEES:
        admin_data[message.chat.id]["employee"] = message.text
        
        # Create task in database
        data = admin_data[message.chat.id]
        task_id = add_task(
            description=data["description"],
            location_lat=data["location"]["latitude"],
            location_lon=data["location"]["longitude"],
            location_address=None,
            payment_amount=data["payment"],
            assigned_to=data["employee"],
            assigned_by=message.chat.id
        )
        
        # Send task to employee
        employee_chat_id = EMPLOYEES[data["employee"]]
        task_text = f"""
🔔 Sizga yangi vazifa tayinlandi!

📝 Vazifa: {data['description']}
💰 To'lov: {data['payment']} so'm
📅 Vaqt: {datetime.now().strftime('%d.%m.%Y %H:%M')}

Vazifani boshlash uchun "👤 Xodim" tugmasini bosing va vazifalar ro'yxatini ko'ring.
"""
        
        try:
            bot.send_message(employee_chat_id, task_text)
            bot.send_location(
                employee_chat_id,
                data["location"]["latitude"],
                data["location"]["longitude"]
            )
            
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

@bot.message_handler(func=lambda message: message.text == "📊 Ma'lumotlar")
def show_data_menu(message):
    """Show data/reports menu"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📈 Umumiy hisobot", "📋 Xodimlar hisoboti")
    markup.add("📥 Excel yuklab olish", "🔙 Ortga")
    
    bot.send_message(
        message.chat.id,
        "📊 Ma'lumotlar bo'limi:\n\nKerakli variantni tanlang:",
        reply_markup=markup
    )

@bot.message_handler(func=lambda message: message.text == "📥 Excel yuklab olish")
def generate_excel_report(message):
    """Generate and send Excel report"""
    bot.send_message(message.chat.id, "📊 Hisobot tayyorlanmoqda...")
    
    try:
        filepath = generate_admin_report()
        if filepath and os.path.exists(filepath):
            with open(filepath, 'rb') as f:
                bot.send_document(
                    message.chat.id,
                    f,
                    caption="📊 Umumiy hisobot Excel fayli"
                )
            # Clean up file
            os.remove(filepath)
        else:
            bot.send_message(message.chat.id, "❌ Hisobot yaratishda xatolik yuz berdi.")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Xatolik: {str(e)}")

@bot.message_handler(func=lambda message: message.text == "💸 Qarzlar")
def show_debts_menu(message):
    """Show debts menu"""
    if message.chat.id != ADMIN_CHAT_ID:
        return
        
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("👁 Qarzlarni ko'rish", "➕ Qarz qo'shish")
    markup.add("❌ Qarzni o'chirish", "🔙 Ortga")
    
    bot.send_message(
        message.chat.id,
        "💸 Qarzlar bo'limi:\n\nKerakli amalni tanlang:",
        reply_markup=markup
    )

@bot.message_handler(func=lambda message: message.text == "➕ Qarz qo'shish")
def start_manual_debt_addition(message):
    """Start manual debt addition process"""
    if message.chat.id != ADMIN_CHAT_ID:
        return
        
    set_user_state(message.chat.id, "manual_debt_employee")
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    for employee_name in EMPLOYEES.keys():
        markup.add(employee_name)
    markup.add("🔙 Bekor qilish")
    
    bot.send_message(
        message.chat.id,
        "👥 Qarz qo'shiladigan xodimni tanlang:",
        reply_markup=markup
    )

@bot.message_handler(func=lambda message: get_user_state(message.chat.id)[0] == "manual_debt_employee")
def get_manual_debt_employee(message):
    """Get employee for manual debt addition"""
    if message.text == "🔙 Bekor qilish":
        clear_user_state(message.chat.id)
        show_admin_panel(message)
        return
        
    if message.text in EMPLOYEES:
        admin_data[message.chat.id] = {"debt_employee": message.text}
        set_user_state(message.chat.id, "manual_debt_amount")
        
        markup = types.ReplyKeyboardRemove()
        bot.send_message(
            message.chat.id,
            f"💰 {message.text} uchun qarz miqdorini kiriting (so'mda):",
            reply_markup=markup
        )
    else:
        bot.send_message(message.chat.id, "❌ Iltimos, ro'yxatdan xodim tanlang!")

@bot.message_handler(func=lambda message: get_user_state(message.chat.id)[0] == "manual_debt_amount")
def get_manual_debt_amount(message):
    """Get manual debt amount"""
    try:
        amount = float(message.text.replace(" ", "").replace(",", ""))
        admin_data[message.chat.id]["debt_amount"] = amount
        set_user_state(message.chat.id, "manual_debt_reason")
        
        bot.send_message(message.chat.id, "📝 Qarz sababini kiriting:")
        
    except ValueError:
        bot.send_message(message.chat.id, "❌ Noto'g'ri format. Raqam kiriting:")

@bot.message_handler(func=lambda message: get_user_state(message.chat.id)[0] == "manual_debt_reason")
def get_manual_debt_reason(message):
    """Get manual debt reason"""
    admin_data[message.chat.id]["debt_reason"] = message.text
    set_user_state(message.chat.id, "manual_debt_date")
    
    bot.send_message(
        message.chat.id,
        "📅 Qachon to'lanishi kerak? (masalan: 2025-02-15):"
    )

@bot.message_handler(func=lambda message: get_user_state(message.chat.id)[0] == "manual_debt_date")
def finalize_manual_debt(message):
    """Finalize manual debt addition"""
    data = admin_data.get(message.chat.id, {})
    employee_name = data.get("debt_employee")
    employee_chat_id = EMPLOYEES.get(employee_name)
    
    # Add debt record
    add_debt(
        employee_name=employee_name,
        employee_chat_id=employee_chat_id,
        task_id=None,
        amount=data["debt_amount"],
        reason=data["debt_reason"],
        payment_date=message.text
    )
    
    bot.send_message(
        message.chat.id,
        f"✅ Qarz qo'shildi!\n\n"
        f"👤 Xodim: {employee_name}\n"
        f"💰 Miqdor: {data['debt_amount']} so'm\n"
        f"📝 Sabab: {data['debt_reason']}\n"
        f"📅 To'lov sanasi: {message.text}"
    )
    
    # Notify employee
    try:
        bot.send_message(
            employee_chat_id,
            f"⚠️ Sizga yangi qarz qo'shildi:\n\n"
            f"💰 Miqdor: {data['debt_amount']} so'm\n"
            f"📝 Sabab: {data['debt_reason']}\n"
            f"📅 To'lov sanasi: {message.text}"
        )
    except:
        pass
    
    clear_user_state(message.chat.id)
    admin_data.pop(message.chat.id, None)
    show_admin_panel(message)

@bot.message_handler(func=lambda message: message.text == "👁 Qarzlarni ko'rish")
def view_all_debts(message):
    """View all debts"""
    if message.chat.id != ADMIN_CHAT_ID:
        return
        
    try:
        debts = get_debts()
        
        if not debts:
            bot.send_message(message.chat.id, "✅ Hech qanday qarz mavjud emas!")
            return
        
        debt_text = "💸 Barcha qarzlar:\n\n"
        total_debt = 0
        
        for i, debt in enumerate(debts, 1):
            debt_id, employee_name, amount, reason, payment_date, created_at, status = debt
            total_debt += amount
            
            debt_text += f"{i}. 👤 {employee_name} (ID: {debt_id})\n"
            debt_text += f"   💰 {amount:,.0f} so'm\n"
            debt_text += f"   📝 {reason}\n"
            debt_text += f"   📅 To'lov sanasi: {payment_date}\n"
            status_text = "To'lanmagan" if status == 'unpaid' else "To'langan"
            debt_text += f"   📊 Holat: {status_text}\n\n"
        
        debt_text += f"💸 Jami qarz: {total_debt} so'm"
        
        # Split long messages
        if len(debt_text) > 4000:
            parts = [debt_text[i:i+4000] for i in range(0, len(debt_text), 4000)]
            for part in parts:
                bot.send_message(message.chat.id, part)
        else:
            bot.send_message(message.chat.id, debt_text)
            
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Xatolik: {str(e)}")

@bot.message_handler(func=lambda message: message.text == "📩 Xabarlar")
def show_messages_menu(message):
    """Show admin messages and notifications"""
    if message.chat.id != ADMIN_CHAT_ID:
        return
    
    try:
        from database import DATABASE_PATH
        import sqlite3
        
        # Get recent task completions (last 24 hours)
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        yesterday = (datetime.now() - timedelta(days=1)).isoformat()
        
        cursor.execute("""
            SELECT t.id, t.assigned_to, t.description, t.completed_at, t.received_amount
            FROM tasks t
            WHERE t.status = 'completed' AND t.completed_at > ?
            ORDER BY t.completed_at DESC
        """, (yesterday,))
        
        recent_completions = cursor.fetchall()
        conn.close()
        
        if not recent_completions:
            bot.send_message(
                message.chat.id,
                "📭 So'nggi 24 soatda bajarilgan vazifalar yo'q."
            )
            return
        
        message_text = "📩 So'nggi 24 soat ichidagi bajarilgan vazifalar:\n\n"
        
        for task_id, employee, description, completed_at, amount in recent_completions:
            try:
                completion_time = datetime.fromisoformat(completed_at).strftime("%d.%m.%Y %H:%M")
            except:
                completion_time = completed_at
            
            message_text += f"✅ Vazifa #{task_id}\n"
            message_text += f"👤 {employee}\n"
            message_text += f"📝 {description[:50]}{'...' if len(description) > 50 else ''}\n"
            message_text += f"💰 {amount or 0} so'm\n"
            message_text += f"🕐 {completion_time}\n\n"
        
        # Split long messages
        if len(message_text) > 4000:
            parts = [message_text[i:i+4000] for i in range(0, len(message_text), 4000)]
            for part in parts:
                bot.send_message(message.chat.id, part)
        else:
            bot.send_message(message.chat.id, message_text)
            
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Xatolik: {str(e)}")

@bot.message_handler(func=lambda message: message.text == "➕ Yangi xodim qo'shish")  
def add_new_employee_info(message):
    """Show information about adding new employees"""
    if message.chat.id != ADMIN_CHAT_ID:
        return
        
    info_text = """
ℹ️ **Yangi xodim qo'shish**

Hozirda yangi xodim qo'shish config.py faylida qo'lda amalga oshiriladi.

**Qadamlar:**
1. Xodimdan Telegram username yoki chat ID olish
2. config.py faylidagi EMPLOYEES ro'yxatiga qo'shish
3. Botni qayta ishga tushirish

**Joriy xodimlar:**
"""
    
    for i, (name, chat_id) in enumerate(EMPLOYEES.items(), 1):
        info_text += f"{i}. {name} - {chat_id}\n"
    
    info_text += "\n💡 Yangi xodim qo'shish uchun admin bilan bog'laning."
    
    bot.send_message(message.chat.id, info_text, parse_mode='Markdown')

# EMPLOYEE SECTION
@bot.message_handler(func=lambda message: message.text == "👤 Xodim")
def employee_login(message):
    """Employee panel access"""
    # Check if user is in employee list
    employee_name = None
    for name, chat_id in EMPLOYEES.items():
        if chat_id == message.chat.id:
            employee_name = name
            break
    
    if not employee_name:
        bot.send_message(
            message.chat.id,
            "❌ Sizning profilingiz topilmadi.\n"
            "Admin bilan bog'laning."
        )
        return
    
    show_employee_panel(message, employee_name)

def show_employee_panel(message, employee_name=None):
    """Show employee panel"""
    if not employee_name:
        for name, chat_id in EMPLOYEES.items():
            if chat_id == message.chat.id:
                employee_name = name
                break
    
    if not employee_name:
        bot.send_message(message.chat.id, "❌ Profil topilmadi.")
        return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📌 Mening vazifalarim", "📂 Vazifalar tarixi")
    markup.add("📊 Hisobotlar", "🔙 Ortga")
    
    bot.send_message(
        message.chat.id,
        f"👤 Xodim paneli\n\nSalom, {employee_name}!\n\nKerakli bo'limni tanlang:",
        reply_markup=markup
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
            
            bot.send_message(message.chat.id, task_info, reply_markup=markup)
    
    # Show active tasks
    if active_tasks:
        bot.send_message(message.chat.id, "🔄 Bajarilayotgan vazifalar:")
        for task in active_tasks:
            task_info = format_task_info(task)
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("✅ Yakunlash", callback_data=f"complete_task_{task[0]}"))
            
            bot.send_message(message.chat.id, task_info, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("start_task_"))
def start_task(call):
    """Start a task"""
    task_id = int(call.data.split("_")[-1])
    
    try:
        update_task_status(task_id, "in_progress")
        
        bot.edit_message_reply_markup(
            call.message.chat.id,
            call.message.message_id,
            reply_markup=None
        )
        
        bot.send_message(
            call.message.chat.id,
            "✅ Vazifa boshlandi!\n\n"
            "Vazifani yakunlash uchun '📌 Mening vazifalarim' bo'limiga o'ting."
        )
        
        # Notify admin
        add_message(
            call.from_user.id,
            ADMIN_CHAT_ID,
            f"Vazifa #{task_id} boshlandi",
            "task_started",
            task_id
        )
        
        user_name = call.from_user.first_name or "Noma'lum"
        bot.send_message(
            ADMIN_CHAT_ID,
            f"🔔 Vazifa #{task_id} boshlandi\n"
            f"👤 Xodim: {user_name}"
        )
        
    except Exception as e:
        bot.send_message(call.message.chat.id, f"❌ Xatolik: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("complete_task_"))
def complete_task_start(call):
    """Start task completion process"""
    task_id = int(call.data.split("_")[-1])
    
    set_user_state(call.message.chat.id, "complete_task_report", str(task_id))
    
    markup = types.ReplyKeyboardRemove()
    bot.send_message(
        call.message.chat.id,
        "📝 Vazifa qanday bajarilganini tavsiflab bering:\n\n"
        "(Matn yoki ovozli xabar yuborishingiz mumkin)",
        reply_markup=markup
    )

@bot.message_handler(func=lambda message: get_user_state(message.chat.id)[0] == "complete_task_report")
def get_completion_report(message):
    """Get task completion report"""
    state, task_id = get_user_state(message.chat.id)
    
    # Save report (text or voice)
    report_text = ""
    if message.content_type == 'text':
        report_text = message.text
    elif message.content_type == 'voice':
        # Save voice file
        file_info = bot.get_file(message.voice.file_id)
        voice_path = save_media_file(file_info, bot, "voice")
        report_text = f"Ovozli hisobot: {voice_path}"
    
    # Store report temporarily
    temp_data = {
        "task_id": int(task_id) if task_id else 0,
        "report": report_text
    }
    set_user_state(message.chat.id, "complete_task_media", serialize_json_data(temp_data))
    
    bot.send_message(
        message.chat.id,
        "📸 Endi vazifa bajarilganligini tasdiqlovchi rasm yoki video yuboring:"
    )

@bot.message_handler(func=lambda message: get_user_state(message.chat.id)[0] == "complete_task_media", 
                    content_types=['photo', 'video'])
def get_completion_media(message):
    """Get task completion media"""
    state, data_str = get_user_state(message.chat.id)
    temp_data = parse_json_data(data_str)
    
    # Save media file
    media_path = None
    if message.content_type == 'photo':
        file_info = bot.get_file(message.photo[-1].file_id)
        media_path = save_media_file(file_info, bot, "photo")
    elif message.content_type == 'video':
        file_info = bot.get_file(message.video.file_id)
        media_path = save_media_file(file_info, bot, "video")
    
    temp_data["media"] = media_path
    set_user_state(message.chat.id, "complete_task_payment", serialize_json_data(temp_data))
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("❌ To'lov olinmadi (qarzga qo'shish)")
    
    bot.send_message(
        message.chat.id,
        "💰 Qancha pul oldingiz? (so'mda kiriting)\n\n"
        "Agar to'lov olinmagan bo'lsa, pastdagi tugmani bosing:",
        reply_markup=markup
    )

@bot.message_handler(func=lambda message: get_user_state(message.chat.id)[0] == "complete_task_payment")
def get_completion_payment(message):
    """Get payment information"""
    state, data_str = get_user_state(message.chat.id)
    temp_data = parse_json_data(data_str)
    
    if message.text == "❌ To'lov olinmadi (qarzga qo'shish)":
        # Start debt process
        set_user_state(message.chat.id, "add_debt_amount", serialize_json_data(temp_data))
        
        markup = types.ReplyKeyboardRemove()
        bot.send_message(
            message.chat.id,
            "💸 Qarz miqdorini kiriting (so'mda):",
            reply_markup=markup
        )
        return
    
    # Regular payment
    try:
        received_amount = float(message.text.replace(" ", "").replace(",", ""))
        
        # Complete the task
        update_task_status(
            temp_data["task_id"],
            "completed",
            completion_report=temp_data["report"],
            completion_media=temp_data.get("media"),
            received_amount=received_amount
        )
        
        # Send completion notification to admin
        employee_name = None
        for name, chat_id in EMPLOYEES.items():
            if chat_id == message.chat.id:
                employee_name = name
                break
        
        admin_message = f"""
✅ Vazifa yakunlandi!

🆔 Vazifa ID: {temp_data["task_id"]}
👤 Xodim: {employee_name or "Noma'lum"}
💰 Olingan to'lov: {received_amount} so'm

📝 Hisobot: {temp_data["report"]}
"""
        
        bot.send_message(ADMIN_CHAT_ID, admin_message)
        
        # Send media if available
        if temp_data.get("media") and os.path.exists(temp_data["media"]):
            try:
                with open(temp_data["media"], 'rb') as f:
                    if "photo" in temp_data["media"]:
                        bot.send_photo(ADMIN_CHAT_ID, f, caption="📸 Vazifa rasmi")
                    elif "video" in temp_data["media"]:
                        bot.send_video(ADMIN_CHAT_ID, f, caption="🎥 Vazifa videosi")
                    elif "voice" in temp_data["media"]:
                        bot.send_voice(ADMIN_CHAT_ID, f, caption="🎤 Ovozli hisobot")
            except Exception as e:
                print(f"Error sending media to admin: {e}")
        
        clear_user_state(message.chat.id)
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📌 Mening vazifalarim", "📂 Vazifalar tarixi")
        markup.add("🔙 Ortga")
        
        bot.send_message(
            message.chat.id,
            "✅ Vazifa muvaffaqiyatli yakunlandi!\n\n"
            "Admin sizning hisobotingizni oldi.",
            reply_markup=markup
        )
        
    except ValueError:
        bot.send_message(message.chat.id, "❌ Noto'g'ri format. Raqam kiriting (masalan: 50000):")

@bot.message_handler(func=lambda message: get_user_state(message.chat.id)[0] == "add_debt_amount")
def get_debt_amount(message):
    """Get debt amount"""
    state, data_str = get_user_state(message.chat.id)
    temp_data = parse_json_data(data_str)
    
    try:
        debt_amount = float(message.text.replace(" ", "").replace(",", ""))
        temp_data["debt_amount"] = debt_amount
        
        set_user_state(message.chat.id, "add_debt_reason", serialize_json_data(temp_data))
        bot.send_message(message.chat.id, "📝 To'lov olinmaganligining sababini kiriting:")
        
    except ValueError:
        bot.send_message(message.chat.id, "❌ Noto'g'ri format. Raqam kiriting:")

@bot.message_handler(func=lambda message: get_user_state(message.chat.id)[0] == "add_debt_reason")
def get_debt_reason(message):
    """Get debt reason"""
    state, data_str = get_user_state(message.chat.id)
    temp_data = parse_json_data(data_str)
    
    temp_data["debt_reason"] = message.text
    set_user_state(message.chat.id, "add_debt_date", serialize_json_data(temp_data))
    
    bot.send_message(
        message.chat.id,
        "📅 Qachon to'lanishi kerak? (masalan: 2025-01-15):"
    )

@bot.message_handler(func=lambda message: get_user_state(message.chat.id)[0] == "add_debt_date")
def get_debt_date(message):
    """Get debt payment date and finalize"""
    state, data_str = get_user_state(message.chat.id)
    temp_data = parse_json_data(data_str)
    
    # Get employee name
    employee_name = None
    for name, chat_id in EMPLOYEES.items():
        if chat_id == message.chat.id:
            employee_name = name
            break
    
    # Add debt record
    add_debt(
        employee_name=employee_name or "Noma'lum",
        employee_chat_id=message.chat.id,
        task_id=temp_data["task_id"],
        amount=temp_data["debt_amount"],
        reason=temp_data["debt_reason"],
        payment_date=message.text
    )
    
    # Complete task with debt info
    update_task_status(
        temp_data["task_id"],
        "completed",
        completion_report=temp_data["report"],
        completion_media=temp_data.get("media"),
        received_amount=0
    )
    
    # Notify admin
    admin_message = f"""
⚠️ Vazifa yakunlandi (QARZ bilan)

🆔 Vazifa ID: {temp_data["task_id"]}
👤 Xodim: {employee_name or "Noma'lum"}
💸 Qarz miqdori: {temp_data["debt_amount"]} so'm
📝 Sabab: {temp_data["debt_reason"]}
📅 To'lov sanasi: {message.text}

📝 Hisobot: {temp_data["report"]}
"""
    
    bot.send_message(ADMIN_CHAT_ID, admin_message)
    
    clear_user_state(message.chat.id)
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📌 Mening vazifalarim", "📂 Vazifalar tarixi")
    markup.add("🔙 Ortga")
    
    bot.send_message(
        message.chat.id,
        "✅ Vazifa yakunlandi va qarz ro'yxatiga qo'shildi.\n\n"
        "Admin xabardor qilindi.",
        reply_markup=markup
    )

@bot.message_handler(func=lambda message: message.text == "📂 Vazifalar tarixi")
def show_task_history(message):
    """Show employee task history"""
    employee_name = None
    for name, chat_id in EMPLOYEES.items():
        if chat_id == message.chat.id:
            employee_name = name
            break
    
    if not employee_name:
        bot.send_message(message.chat.id, "❌ Profil topilmadi.")
        return
    
    completed_tasks = get_employee_tasks(employee_name, "completed")
    
    if not completed_tasks:
        bot.send_message(message.chat.id, "📭 Bajarilgan vazifalar tarixi bo'sh.")
        return
    
    bot.send_message(message.chat.id, "📂 Bajarilgan vazifalar tarixi:")
    
    for task in completed_tasks[-10:]:  # Show last 10 tasks
        task_info = format_task_info(task)
        bot.send_message(message.chat.id, task_info)

@bot.message_handler(func=lambda message: message.text == "📊 Hisobotlar")
def show_employee_reports(message):
    """Show employee reports menu"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📅 30 kunlik hisobot", "🗓 1 haftalik hisobot")
    markup.add("📤 Excel yuklab olish", "🔙 Ortga")
    
    bot.send_message(
        message.chat.id,
        "📊 Hisobotlar bo'limi:\n\nKerakli variantni tanlang:",
        reply_markup=markup
    )

@bot.message_handler(func=lambda message: message.text == "📤 Excel yuklab olish" and message.chat.id in EMPLOYEES.values())
def generate_employee_excel(message):
    """Generate employee Excel report"""
    employee_name = None
    for name, chat_id in EMPLOYEES.items():
        if chat_id == message.chat.id:
            employee_name = name
            break
    
    if not employee_name:
        bot.send_message(message.chat.id, "❌ Profil topilmadi.")
        return
    
    bot.send_message(message.chat.id, "📊 Hisobot tayyorlanmoqda...")
    
    try:
        filepath = generate_employee_report(employee_name, 30)
        if filepath and os.path.exists(filepath):
            with open(filepath, 'rb') as f:
                bot.send_document(
                    message.chat.id,
                    f,
                    caption=f"📊 {employee_name} - 30 kunlik hisobot"
                )
            os.remove(filepath)
        else:
            bot.send_message(message.chat.id, "❌ Hisobot yaratishda xatolik yuz berdi.")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Xatolik: {str(e)}")

# COMMON HANDLERS
@bot.message_handler(func=lambda message: message.text == "🔙 Ortga")
def go_back(message):
    """Go back to main menu"""
    clear_user_state(message.chat.id)
    start_message(message)

# GPS tracking handler
@bot.message_handler(func=lambda message: message.text == "📍 Xodimlarni kuzatish")
def track_employees(message):
    """Track employees location"""
    if message.chat.id != ADMIN_CHAT_ID:
        return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    for employee_name in EMPLOYEES.keys():
        markup.add(f"📍 {employee_name}")
    markup.add("🔙 Ortga")
    
    bot.send_message(
        message.chat.id,
        "📍 Qaysi xodimning lokatsiyasini so'raysiz?",
        reply_markup=markup
    )

@bot.message_handler(func=lambda message: message.text.startswith("📍 👨‍🔧"))
def request_employee_location(message):
    """Request specific employee location"""
    if message.chat.id != ADMIN_CHAT_ID:
        return
    
    employee_name = message.text.replace("📍 ", "")
    employee_chat_id = EMPLOYEES.get(employee_name)
    
    if not employee_chat_id:
        bot.send_message(message.chat.id, "❌ Xodim topilmadi.")
        return
    
    try:
        # Request location from employee
        location_markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        location_btn = types.KeyboardButton("📍 Lokatsiyamni yuborish", request_location=True)
        location_markup.add(location_btn)
        location_markup.add("❌ Rad etish")
        
        bot.send_message(
            employee_chat_id,
            f"📍 Admin sizning joylashuvingizni so'ramoqda.\n\n"
            f"Lokatsiyangizni yuboring:",
            reply_markup=location_markup
        )
        
        bot.send_message(
            message.chat.id,
            f"📤 {employee_name}ga lokatsiya so'rovi yuborildi.\n"
            f"Javobni kutib turing..."
        )
        
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Xatolik: {str(e)}")

# Handle location sharing for tracking
@bot.message_handler(content_types=['location'])
def handle_location_sharing(message):
    """Handle location sharing from employees"""
    # Check if this is from an employee
    employee_name = None
    for name, chat_id in EMPLOYEES.items():
        if chat_id == message.chat.id:
            employee_name = name
            break
    
    if employee_name:
        # Send location to admin
        try:
            bot.send_message(
                ADMIN_CHAT_ID,
                f"📍 {employee_name} lokatsiyasi:"
            )
            bot.send_location(
                ADMIN_CHAT_ID,
                message.location.latitude,
                message.location.longitude
            )
            
            # Confirm to employee
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add("📌 Mening vazifalarim", "📂 Vazifalar tarixi")
            markup.add("🔙 Ortga")
            
            bot.send_message(
                message.chat.id,
                "✅ Lokatsiya adminga yuborildi.",
                reply_markup=markup
            )
            
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Xatolik: {str(e)}")

# Error handler
@bot.message_handler(func=lambda message: True)
def handle_unknown(message):
    """Handle unknown messages"""
    bot.send_message(
        message.chat.id,
        "❓ Tushunmadim. Iltimos, menyudan tanlang yoki /start bosing."
    )

if __name__ == "__main__":
    print("🤖 Bot ishga tushmoqda...")
    print(f"📱 Bot token: {BOT_TOKEN[:10]}...")
    print(f"👑 Admin chat ID: {ADMIN_CHAT_ID}")
    print(f"👥 Xodimlar soni: {len(EMPLOYEES)}")
    
    try:
        bot.infinity_polling(none_stop=True, interval=0, timeout=60)
    except Exception as e:
        print(f"❌ Bot xatosi: {e}")
        import time
        time.sleep(5)
        bot.infinity_polling(none_stop=True, interval=0, timeout=60)
