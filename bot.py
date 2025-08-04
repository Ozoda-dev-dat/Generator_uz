import telebot
from telebot import types
from config import BOT_TOKEN, ADMIN_CODE, ADMIN_CHAT_ID, EMPLOYEES
from handlers.admin_handlers import AdminHandler
from handlers.employee_handlers import EmployeeHandler
from utils.database import init_all_databases

# Initialize bot
bot = telebot.TeleBot(BOT_TOKEN)

# Initialize databases
init_all_databases()

# Initialize handlers
admin_handler = AdminHandler(bot)
employee_handler = EmployeeHandler(bot)

# User session management
user_sessions = {}

@bot.message_handler(commands=['start'])
def start_message(message):
    """Handle /start command"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🔐 Admin", "👤 Xodim")
    bot.send_message(message.chat.id, "Assalomu alaykum!\nIltimos, rolingizni tanlang:", reply_markup=markup)

@bot.message_handler(commands=['getid'])
def send_chat_id(message):
    """Send user's chat ID"""
    bot.reply_to(message, f"🆔 Sizning chat ID'ingiz: {message.chat.id}")

@bot.message_handler(func=lambda message: message.text == "🔐 Admin")
def ask_admin_code(message):
    """Ask for admin code"""
    msg = bot.send_message(message.chat.id, "🔑 Iltimos, admin kodini kiriting:")
    bot.register_next_step_handler(msg, verify_admin_code)

def verify_admin_code(message):
    """Verify admin code"""
    if message.text == ADMIN_CODE:
        user_sessions[message.chat.id] = "admin"
        bot.send_message(message.chat.id, "✅ Xush kelibsiz, admin!")
        admin_handler.show_admin_panel(message)
    else:
        msg = bot.send_message(message.chat.id, "❌ Kod noto'g'ri. Qaytadan urinib ko'ring:")
        bot.register_next_step_handler(msg, verify_admin_code)

@bot.message_handler(func=lambda message: message.text == "👤 Xodim")
def employee_login(message):
    """Handle employee login"""
    chat_id = message.chat.id
    
    # Check if user is in employee list
    if chat_id in EMPLOYEES.values():
        user_sessions[chat_id] = "employee"
        employee_handler.show_employee_panel(message)
    else:
        bot.send_message(chat_id, "❌ Siz hodimlar ro'yxatida yo'qsiz.\n🆔 Chat ID'ingiz: " + str(chat_id))

# Admin handlers
@bot.message_handler(func=lambda message: message.text == "📝 Topshiriqlar" and user_sessions.get(message.chat.id) == "admin")
def handle_admin_tasks(message):
    admin_handler.start_task_creation(message)

@bot.message_handler(func=lambda message: message.text == "📊 Qarzdorlik" and user_sessions.get(message.chat.id) == "admin")
def handle_admin_debts(message):
    admin_handler.show_debt_menu(message)

@bot.message_handler(func=lambda message: message.text == "➕ Qarz qo'shish" and user_sessions.get(message.chat.id) == "admin")
def handle_add_debt(message):
    admin_handler.start_add_debt(message)

@bot.message_handler(func=lambda message: message.text == "📋 Qarzlarni ko'rish" and user_sessions.get(message.chat.id) == "admin")
def handle_view_debts(message):
    admin_handler.show_all_debts(message)

@bot.message_handler(func=lambda message: message.text == "💰 Pul miqdori" and user_sessions.get(message.chat.id) == "admin")
def handle_admin_payment(message):
    admin_handler.ask_payment(message)

@bot.message_handler(func=lambda message: message.text == "👥 Kerakli hodimlar" and user_sessions.get(message.chat.id) == "admin")
def handle_admin_employees(message):
    admin_handler.choose_employees(message)

# Employee handlers
@bot.message_handler(func=lambda message: message.text == "📋 Mening vazifalarim" and user_sessions.get(message.chat.id) == "employee")
def handle_my_tasks(message):
    employee_handler.show_my_tasks(message)

@bot.message_handler(func=lambda message: message.text == "✅ Bajarilgan vazifalar" and user_sessions.get(message.chat.id) == "employee")
def handle_completed_tasks(message):
    employee_handler.show_completed_tasks(message)

@bot.message_handler(func=lambda message: message.text == "📊 Hisobot" and user_sessions.get(message.chat.id) == "employee")
def handle_employee_reports(message):
    employee_handler.show_report_menu(message)

@bot.message_handler(func=lambda message: message.text == "📅 30 kunlik hisobot" and user_sessions.get(message.chat.id) == "employee")
def handle_30_day_report(message):
    employee_handler.report_30_days(message)

@bot.message_handler(func=lambda message: message.text == "🗓 1 haftalik hisobot" and user_sessions.get(message.chat.id) == "employee")
def handle_7_day_report(message):
    employee_handler.report_7_days(message)

@bot.message_handler(func=lambda message: message.text == "📤 Excel faylga chop etish" and user_sessions.get(message.chat.id) == "employee")
def handle_excel_export(message):
    employee_handler.export_excel_report(message)

# Back buttons
@bot.message_handler(func=lambda message: message.text in ["⬅️ Ortga", "🔙 Ortga", "🔙 Orqaga"])
def handle_back_buttons(message):
    session = user_sessions.get(message.chat.id)
    if session == "admin":
        admin_handler.show_admin_panel(message)
    elif session == "employee":
        employee_handler.show_employee_panel(message)
    else:
        start_message(message)

# Location handler
@bot.message_handler(content_types=['location'])
def handle_location(message):
    if user_sessions.get(message.chat.id) == "admin":
        admin_handler.receive_location(message)

# Callback query handler for task status updates
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    if user_sessions.get(call.message.chat.id) == "employee":
        employee_handler.handle_task_callback(call)

# Error handler
@bot.message_handler(func=lambda message: True)
def handle_unknown_messages(message):
    chat_id = message.chat.id
    session = user_sessions.get(chat_id)
    
    if session == "admin":
        bot.send_message(chat_id, "❌ Noma'lum buyruq. Admin panelidagi tugmalardan foydalaning.")
        admin_handler.show_admin_panel(message)
    elif session == "employee":
        bot.send_message(chat_id, "❌ Noma'lum buyruq. Hodim panelidagi tugmalardan foydalaning.")
        employee_handler.show_employee_panel(message)
    else:
        start_message(message)

if __name__ == "__main__":
    print("🤖 Bot ishga tushdi...")
    bot.infinity_polling(none_stop=True)
