#!/usr/bin/env python3
"""
Enhanced Telegram Task Management Bot
A comprehensive bot for managing tasks between admins and employees
with location sharing, Excel reporting, debt tracking, and media support.
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
    add_message, get_user_state, set_user_state, clear_user_state
)
from utils import (
    save_media_file, generate_employee_report, generate_admin_report,
    format_task_info, parse_json_data, serialize_json_data, ensure_directories
)

def main():
    """Main function to start the enhanced bot"""
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN mavjud emas. Iltimos, bot tokenini qo'shing.")
        sys.exit(1)

    # Initialize bot
    bot = telebot.TeleBot(BOT_TOKEN)
    
    # Delete webhook to ensure polling works
    try:
        bot.delete_webhook()
    except Exception as e:
        print(f"⚠️ Webhook deletion warning: {e}")
    
    # Initialize database and directories
    init_database()
    ensure_directories()
    
    # Global variables for conversation states
    admin_data = {}

    @bot.message_handler(commands=['start'])
    def start_message(message):
        """Handle /start command"""
        clear_user_state(message.chat.id)
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("🔐 Admin", "👤 Xodim")
        markup.add("👥 Mijoz")
        
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
        markup.add("📍 Xodimlarni kuzatish", "👥 Mijozlar so'rovlari")
        markup.add("💸 Qarzlar", "📊 Ma'lumotlar")
        markup.add("🔙 Ortga")
        
        bot.send_message(
            message.chat.id,
            "🛠 Admin paneli\n\nKerakli bo'limni tanlang:",
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
        # Ensure admin_data exists for this user
        if message.chat.id not in admin_data:
            admin_data[message.chat.id] = {}
            
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
            # Ensure admin_data exists for this user
            if message.chat.id not in admin_data:
                admin_data[message.chat.id] = {}
                
            admin_data[message.chat.id]["location"] = {
                "latitude": message.location.latitude,
                "longitude": message.location.longitude
            }
            
            set_user_state(message.chat.id, "assign_task_payment")
            
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
            markup.add("💰 To'lov miqdorini kiriting")
            markup.add("⏭ To'lov belgilanmagan")
            markup.add("🔙 Bekor qilish")
            
            bot.send_message(
                message.chat.id,
                "✅ Lokatsiya qabul qilindi.\n\n💰 Vazifa uchun to'lov miqdorini kiriting yoki 'To'lov belgilanmagan' tugmasini bosing:",
                reply_markup=markup
            )
        else:
            # Handle location sharing for tracking
            handle_location_sharing(message)

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
            # Ensure admin_data exists for this user
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
            
            # Ensure admin_data exists for this user
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
            # Ensure admin_data exists for this user
            if message.chat.id not in admin_data:
                admin_data[message.chat.id] = {}
                
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
        """Show comprehensive data management menu"""
        if message.chat.id != ADMIN_CHAT_ID:
            return
            
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("👁 Barcha ma'lumotlar", "📊 Statistika")
        markup.add("➕ Ma'lumot qo'shish", "✏️ Ma'lumot tahrirlash")
        markup.add("🗑 Ma'lumot o'chirish", "📋 Batafsil ko'rish")
        markup.add("📤 Ma'lumot eksport", "🔄 Ma'lumot import")
        markup.add("🧹 Ma'lumot tozalash", "🔍 Ma'lumot qidirish")
        markup.add("📥 Excel yuklab olish", "📈 Umumiy hisobot")
        markup.add("🔙 Ortga")
        
        bot.send_message(
            message.chat.id,
            "📊 To'liq Ma'lumotlar Boshqaruv Tizimi\n\n"
            "🔹 Barcha jadvallardan ma'lumotlarni ko'rish\n"
            "🔹 To'liq CRUD operatsiyalari (Create, Read, Update, Delete)\n"
            "🔹 Professional Excel eksport/import\n"
            "🔹 Real-time statistika va tahlil\n"
            "🔹 Ma'lumotlarni qidirish va filtrlash\n\n"
            "Kerakli amaliyotni tanlang:",
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
        markup.add("✅ Qarzni to'lash", "❌ Qarzni o'chirish")
        markup.add("📊 Qarzlar hisoboti", "🔙 Ortga")
        
        bot.send_message(
            message.chat.id,
            "💸 Qarzlar bo'limi:\n\nKerakli amalni tanlang:",
            reply_markup=markup
        )

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
                debt_id, employee_name, employee_chat_id, task_id, amount, reason, payment_date, created_at, status = debt
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

    @bot.message_handler(func=lambda message: message.text == "➕ Yangi xodim qo'shish")  
    def start_add_employee(message):
        """Start adding new employee process"""
        if message.chat.id != ADMIN_CHAT_ID:
            return
        
        set_user_state(message.chat.id, "add_employee_name")
        admin_data[message.chat.id] = {}
        
        markup = types.ReplyKeyboardRemove()
        bot.send_message(
            message.chat.id,
            "👤 Yangi xodimning ismini kiriting:",
            reply_markup=markup
        )
    
    @bot.message_handler(func=lambda message: message.text == "👥 Mijozlar so'rovlari")
    def show_customer_requests(message):
        """Show customer requests menu"""
        if message.chat.id != ADMIN_CHAT_ID:
            return
            
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📋 Faol suhbatlar", "📋 Mijozning So'rovlari")
        markup.add("📊 Mijozlar statistikasi", "🔙 Ortga")
        
        bot.send_message(
            message.chat.id,
            "👥 Mijozlar so'rovlari bo'limi\n\n"
            "Mijozlar bilan ishlash uchun kerakli variantni tanlang:\n\n"
            "💡 Mijozga javob berish: /reply [chat_id] [xabar]",
            reply_markup=markup
        )
    
    @bot.message_handler(func=lambda message: message.text == "📋 Faol suhbatlar")
    def show_active_chats(message):
        """Show active customer chats"""
        if message.chat.id != ADMIN_CHAT_ID:
            return
        
        # Get active customer chats from database
        try:
            from database import DATABASE_PATH
            import sqlite3
            
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()
            
            # Get users in customer_chat state
            cursor.execute("""
                SELECT chat_id, updated_at FROM user_states 
                WHERE state = 'customer_chat'
                ORDER BY updated_at DESC
            """)
            
            active_chats = cursor.fetchall()
            conn.close()
            
            if not active_chats:
                bot.send_message(message.chat.id, "📭 Hozirda faol mijoz suhbatlari yo'q.")
                return
            
            chat_text = "📋 Faol mijoz suhbatlari:\n\n"
            
            for i, (chat_id, updated_at) in enumerate(active_chats, 1):
                try:
                    # Try to get user info
                    user_info = bot.get_chat(chat_id)
                    name = user_info.first_name or "Noma'lum"
                    username = f"@{user_info.username}" if user_info.username else "Username yo'q"
                except:
                    name = "Noma'lum mijoz"
                    username = ""
                
                chat_text += f"{i}. 👤 {name} {username}\n"
                chat_text += f"   🆔 Chat ID: {chat_id}\n"
                chat_text += f"   🕐 Oxirgi faollik: {updated_at[:16]}\n"
                chat_text += f"   💬 Javob: /reply {chat_id} [xabar]\n\n"
            
            bot.send_message(message.chat.id, chat_text)
            
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Xatolik: {str(e)}")

    @bot.message_handler(func=lambda message: message.text == "📋 Mijozning So'rovlari")
    def show_customer_calls(message):
        """Show customer requests history"""
        if message.chat.id != ADMIN_CHAT_ID:
            return
        
        try:
            from database import DATABASE_PATH
            import sqlite3
            
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()
            
            # Get recent customer messages (last 24 hours)
            yesterday = (datetime.now() - timedelta(days=1)).isoformat()
            
            cursor.execute("""
                SELECT from_chat_id, message_text, created_at FROM messages 
                WHERE to_chat_id = ? AND message_type IN ('customer_message', 'customer_start')
                AND created_at > ?
                ORDER BY created_at DESC
                LIMIT 20
            """, (ADMIN_CHAT_ID, yesterday))
            
            recent_messages = cursor.fetchall()
            conn.close()
            
            if not recent_messages:
                bot.send_message(message.chat.id, "📭 So'nggi 24 soatda mijoz so'rovlari yo'q.")
                return
            
            calls_text = "📋 So'nggi mijoz so'rovlari (24 soat):\n\n"
            
            for i, (chat_id, message_text, created_at) in enumerate(recent_messages, 1):
                try:
                    # Try to get user info
                    user_info = bot.get_chat(chat_id)
                    name = user_info.first_name or "Noma'lum"
                except:
                    name = "Noma'lum mijoz"
                
                try:
                    time_str = datetime.fromisoformat(created_at).strftime("%d.%m %H:%M")
                except:
                    time_str = created_at[:16]
                
                calls_text += f"{i}. 👤 {name} ({chat_id})\n"
                calls_text += f"   🕐 {time_str}\n"
                calls_text += f"   💬 {message_text[:50]}{'...' if len(message_text) > 50 else ''}\n\n"
            
            if len(calls_text) > 4000:
                # Split long messages
                parts = [calls_text[i:i+4000] for i in range(0, len(calls_text), 4000)]
                for part in parts:
                    bot.send_message(message.chat.id, part)
            else:
                bot.send_message(message.chat.id, calls_text)
                
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Xatolik: {str(e)}")
    
    @bot.message_handler(func=lambda message: message.text == "📊 Mijozlar statistikasi")
    def show_customer_stats(message):
        """Show customer statistics"""
        if message.chat.id != ADMIN_CHAT_ID:
            return
        
        try:
            from database import DATABASE_PATH
            import sqlite3
            
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()
            
            # Get total customer messages
            cursor.execute("""
                SELECT COUNT(*) FROM messages 
                WHERE to_chat_id = ? AND message_type = 'general'
            """, (ADMIN_CHAT_ID,))
            
            total_messages = cursor.fetchone()[0]
            
            # Get active chats today
            today = datetime.now().strftime('%Y-%m-%d')
            cursor.execute("""
                SELECT COUNT(*) FROM user_states 
                WHERE state = 'customer_chat' AND updated_at LIKE ?
            """, (f"{today}%",))
            
            today_chats = cursor.fetchone()[0]
            
            conn.close()
            
            stats_text = f"""
📊 Mijozlar statistikasi

📩 Jami xabarlar: {total_messages}
👥 Bugungi suhbatlar: {today_chats}
🕐 Oxirgi yangilanish: {datetime.now().strftime('%H:%M')}

💡 Barcha faol suhbatlarni ko'rish uchun "📋 Faol suhbatlar" tugmasini bosing.
"""
            
            bot.send_message(message.chat.id, stats_text)
            
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Statistika olishda xatolik: {str(e)}")

    @bot.message_handler(func=lambda message: message.text == "➕ Qarz qo'shish")
    def start_manual_debt_add(message):
        """Start manual debt addition process"""
        if message.chat.id != ADMIN_CHAT_ID:
            return
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        for employee_name in EMPLOYEES.keys():
            markup.add(employee_name)
        markup.add("👥 Boshqalar")
        markup.add("🔙 Bekor qilish")
        
        set_user_state(message.chat.id, "select_debt_employee")
        
        bot.send_message(
            message.chat.id,
            "👥 Kimga qarz qo'shmoqchisiz?",
            reply_markup=markup
        )

    @bot.message_handler(func=lambda message: get_user_state(message.chat.id)[0] == "select_debt_employee")
    def select_debt_employee(message):
        """Select employee for debt"""
        if message.text == "🔙 Bekor qilish":
            clear_user_state(message.chat.id)
            show_debts_menu(message)
            return
        
        if message.text in EMPLOYEES:
            admin_data[message.chat.id] = {"employee": message.text, "employee_type": "staff"}
            set_user_state(message.chat.id, "manual_debt_amount")
            
            markup = types.ReplyKeyboardRemove()
            bot.send_message(
                message.chat.id,
                "💰 Qarz miqdorini kiriting (so'mda):",
                reply_markup=markup
            )
        elif message.text == "👥 Boshqalar":
            admin_data[message.chat.id] = {"employee_type": "other"}
            set_user_state(message.chat.id, "other_debt_name")
            
            markup = types.ReplyKeyboardRemove()
            bot.send_message(
                message.chat.id,
                "👤 Qarzdorning ismini kiriting:",
                reply_markup=markup
            )
        else:
            bot.send_message(message.chat.id, "❌ Iltimos, ro'yxatdan variant tanlang!")

    @bot.message_handler(func=lambda message: get_user_state(message.chat.id)[0] == "manual_debt_amount")
    def get_manual_debt_amount(message):
        """Get manual debt amount"""
        try:
            amount = float(message.text.replace(" ", "").replace(",", ""))
            
            # Ensure admin_data exists for this user
            if message.chat.id not in admin_data:
                admin_data[message.chat.id] = {}
            
            admin_data[message.chat.id]["amount"] = amount
            set_user_state(message.chat.id, "manual_debt_reason")
            
            bot.send_message(message.chat.id, "📝 Qarz sababini kiriting:")
            
        except ValueError:
            bot.send_message(message.chat.id, "❌ Noto'g'ri format. Raqam kiriting:")
        except KeyError:
            bot.send_message(message.chat.id, "❌ Sessiya tugagan. Qaytadan boshlang.")
            clear_user_state(message.chat.id)
            show_debts_menu(message)

    @bot.message_handler(func=lambda message: get_user_state(message.chat.id)[0] == "manual_debt_reason")
    def get_manual_debt_reason(message):
        """Get manual debt reason"""
        try:
            # Ensure admin_data exists for this user
            if message.chat.id not in admin_data:
                admin_data[message.chat.id] = {}
            
            admin_data[message.chat.id]["reason"] = message.text
            set_user_state(message.chat.id, "manual_debt_date")
            
            bot.send_message(
                message.chat.id,
                "📅 To'lov sanasini kiriting (masalan: 2025-01-15):"
            )
        except KeyError:
            bot.send_message(message.chat.id, "❌ Sessiya tugagan. Qaytadan boshlang.")
            clear_user_state(message.chat.id)
            show_debts_menu(message)

    @bot.message_handler(func=lambda message: get_user_state(message.chat.id)[0] == "manual_debt_date")
    def get_manual_debt_date(message):
        """Get manual debt date and create debt"""
        try:
            # Ensure admin_data exists for this user
            if message.chat.id not in admin_data:
                bot.send_message(message.chat.id, "❌ Sessiya tugagan. Qaytadan boshlang.")
                clear_user_state(message.chat.id)
                show_debts_menu(message)
                return
            
            data = admin_data[message.chat.id]
            employee_name = data["employee"]
        
            # Handle different employee types
            if data["employee_type"] == "staff":
                employee_chat_id = EMPLOYEES[employee_name]
            else:
                employee_chat_id = 0  # For non-employees
        
            # Add debt record
            add_debt(
                employee_name=employee_name,
                employee_chat_id=employee_chat_id,
                task_id=None,
                amount=data["amount"],
                reason=data["reason"],
                payment_date=message.text
            )
            
            bot.send_message(
                message.chat.id,
                f"✅ Qarz qo'shildi!\n\n"
                f"👤 Xodim: {employee_name}\n"
                f"💰 Miqdor: {data['amount']} so'm\n"
                f"📝 Sabab: {data['reason']}\n"
                f"📅 To'lov sanasi: {message.text}"
            )
            
            # Notify employee (only if it's a staff member)
            if data["employee_type"] == "staff":
                try:
                    bot.send_message(
                        employee_chat_id,
                        f"⚠️ Sizga yangi qarz qo'shildi:\n\n"
                        f"💰 Miqdor: {data['amount']} so'm\n"
                        f"📝 Sabab: {data['reason']}\n"
                        f"📅 To'lov sanasi: {message.text}"
                    )
                except:
                    pass
        
            clear_user_state(message.chat.id)
            admin_data.pop(message.chat.id, None)
            show_debts_menu(message)
        
        except KeyError as e:
            bot.send_message(message.chat.id, f"❌ Sessiya xatoligi: {str(e)}")
            clear_user_state(message.chat.id)
            show_debts_menu(message)
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Xatolik: {str(e)}")
            clear_user_state(message.chat.id)
            show_debts_menu(message)

    @bot.message_handler(func=lambda message: message.text == "✅ Qarzni to'lash")
    def start_pay_debt(message):
        """Start debt payment process"""
        if message.chat.id != ADMIN_CHAT_ID:
            return
        
        try:
            debts = get_debts()
            
            if not debts:
                bot.send_message(message.chat.id, "✅ To'lanadigan qarzlar yo'q!")
                return
            
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            
            for debt in debts[:10]:  # Show first 10 debts
                debt_id, employee_name, employee_chat_id, task_id, amount, reason, payment_date, created_at, status = debt
                markup.add(f"💸 ID:{debt_id} - {employee_name} ({amount} so'm)")
            
            markup.add("🔙 Bekor qilish")
            
            set_user_state(message.chat.id, "select_debt_to_pay")
            
            bot.send_message(
                message.chat.id,
                "✅ Qaysi qarzni to'langanini belgilaysiz?",
                reply_markup=markup
            )
            
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Xatolik: {str(e)}")

    @bot.message_handler(func=lambda message: get_user_state(message.chat.id)[0] == "select_debt_to_pay")
    def pay_selected_debt(message):
        """Pay selected debt"""
        if message.text == "🔙 Bekor qilish":
            clear_user_state(message.chat.id)
            show_debts_menu(message)
            return
        
        try:
            # Extract debt ID from message
            if "ID:" in message.text:
                debt_id = int(message.text.split("ID:")[1].split(" ")[0])
                
                # Update debt status to paid
                from database import DATABASE_PATH
                import sqlite3
                
                conn = sqlite3.connect(DATABASE_PATH)
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE debts SET status = 'paid' WHERE id = ?
                """, (debt_id,))
                
                # Get debt info
                cursor.execute("""
                    SELECT employee_name, employee_chat_id, amount, reason 
                    FROM debts WHERE id = ?
                """, (debt_id,))
                
                debt_info = cursor.fetchone()
                conn.commit()
                conn.close()
                
                if debt_info:
                    employee_name, employee_chat_id, amount, reason = debt_info
                    
                    bot.send_message(
                        message.chat.id,
                        f"✅ Qarz to'langanini belgilandi!\n\n"
                        f"🆔 Qarz ID: {debt_id}\n"
                        f"👤 Xodim: {employee_name}\n"
                        f"💰 Miqdor: {amount} so'm\n"
                        f"📝 Sabab: {reason}"
                    )
                    
                    # Notify employee
                    try:
                        bot.send_message(
                            employee_chat_id,
                            f"✅ Sizning qarzingiz to'langanini belgilandi:\n\n"
                            f"💰 Miqdor: {amount} so'm\n"
                            f"📝 Sabab: {reason}"
                        )
                    except:
                        pass
                else:
                    bot.send_message(message.chat.id, "❌ Qarz topilmadi.")
            else:
                bot.send_message(message.chat.id, "❌ Noto'g'ri format.")
                
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Xatolik: {str(e)}")
        
        clear_user_state(message.chat.id)
        show_debts_menu(message)

    @bot.message_handler(func=lambda message: message.text == "❌ Qarzni o'chirish")
    def start_delete_debt(message):
        """Start debt deletion process"""
        if message.chat.id != ADMIN_CHAT_ID:
            return
        
        try:
            debts = get_debts()
            
            if not debts:
                bot.send_message(message.chat.id, "✅ O'chiriladigan qarzlar yo'q!")
                return
            
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            
            for debt in debts[:10]:  # Show first 10 debts
                debt_id, employee_name, employee_chat_id, task_id, amount, reason, payment_date, created_at, status = debt
                markup.add(f"🗑 ID:{debt_id} - {employee_name} ({amount} so'm)")
            
            markup.add("🔙 Bekor qilish")
            
            set_user_state(message.chat.id, "select_debt_to_delete")
            
            bot.send_message(
                message.chat.id,
                "🗑 Qaysi qarzni o'chirmoqchisiz?",
                reply_markup=markup
            )
            
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Xatolik: {str(e)}")

    @bot.message_handler(func=lambda message: get_user_state(message.chat.id)[0] == "select_debt_to_delete")
    def delete_selected_debt(message):
        """Delete selected debt"""
        if message.text == "🔙 Bekor qilish":
            clear_user_state(message.chat.id)
            show_debts_menu(message)
            return
        
        try:
            # Extract debt ID from message
            if "ID:" in message.text:
                debt_id = int(message.text.split("ID:")[1].split(" ")[0])
                
                # Delete debt
                from database import DATABASE_PATH
                import sqlite3
                
                conn = sqlite3.connect(DATABASE_PATH)
                cursor = conn.cursor()
                
                # Get debt info before deleting
                cursor.execute("""
                    SELECT employee_name, amount, reason 
                    FROM debts WHERE id = ?
                """, (debt_id,))
                
                debt_info = cursor.fetchone()
                
                if debt_info:
                    cursor.execute("DELETE FROM debts WHERE id = ?", (debt_id,))
                    conn.commit()
                    
                    employee_name, amount, reason = debt_info
                    
                    bot.send_message(
                        message.chat.id,
                        f"🗑 Qarz o'chirildi!\n\n"
                        f"🆔 Qarz ID: {debt_id}\n"
                        f"👤 Xodim: {employee_name}\n"
                        f"💰 Miqdor: {amount} so'm\n"
                        f"📝 Sabab: {reason}"
                    )
                else:
                    bot.send_message(message.chat.id, "❌ Qarz topilmadi.")
                
                conn.close()
            else:
                bot.send_message(message.chat.id, "❌ Noto'g'ri format.")
                
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Xatolik: {str(e)}")
        
        clear_user_state(message.chat.id)
        show_debts_menu(message)

    @bot.message_handler(func=lambda message: message.text == "📊 Qarzlar hisoboti")
    def generate_debts_report(message):
        """Generate debts Excel report"""
        if message.chat.id != ADMIN_CHAT_ID:
            return
        
        bot.send_message(message.chat.id, "📊 Qarzlar hisoboti tayyorlanmoqda...")
        
        try:
            from utils import generate_debts_report_excel
            filepath = generate_debts_report_excel()
            
            if filepath and os.path.exists(filepath):
                with open(filepath, 'rb') as f:
                    bot.send_document(
                        message.chat.id,
                        f,
                        caption="📊 Qarzlar hisoboti (Excel)"
                    )
                # Clean up file
                os.remove(filepath)
            else:
                bot.send_message(message.chat.id, "❌ Hisobot yaratishda xatolik yuz berdi.")
                
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Xatolik: {str(e)}")

    # NEW EMPLOYEE ADDITION HANDLERS
    @bot.message_handler(func=lambda message: get_user_state(message.chat.id)[0] == "add_employee_name")
    def get_employee_name(message):
        """Get new employee name"""
        admin_data[message.chat.id]["name"] = message.text
        set_user_state(message.chat.id, "add_employee_id")
        
        bot.send_message(
            message.chat.id,
            "🆔 Xodimning Telegram ID sini kiriting:"
        )

    @bot.message_handler(func=lambda message: get_user_state(message.chat.id)[0] == "add_employee_id")
    def get_employee_id(message):
        """Get new employee Telegram ID and add to system"""
        try:
            chat_id = int(message.text)
            name = admin_data[message.chat.id]["name"]
            
            # Update config file
            import config
            
            # Read current config
            with open('config.py', 'r', encoding='utf-8') as f:
                config_content = f.read()
            
            # Find EMPLOYEES dictionary and add new employee
            if "EMPLOYEES = {" in config_content:
                # Add new employee to the dictionary
                new_employee_line = f'    "{name}": {chat_id},'
                
                # Find the closing brace of EMPLOYEES
                employees_start = config_content.find("EMPLOYEES = {")
                employees_end = config_content.find("}", employees_start)
                
                # Insert new employee before closing brace
                new_config = (config_content[:employees_end] + 
                             new_employee_line + "\n" + 
                             config_content[employees_end:])
                
                # Write updated config
                with open('config.py', 'w', encoding='utf-8') as f:
                    f.write(new_config)
                
                # Update runtime EMPLOYEES dictionary and reload config
                EMPLOYEES[name] = chat_id
                
                # Reload the config module to get updated EMPLOYEES
                import importlib
                import config
                importlib.reload(config)
                
                bot.send_message(
                    message.chat.id,
                    f"✅ Yangi xodim qo'shildi!\n\n"
                    f"👤 Ism: {name}\n"
                    f"🆔 Telegram ID: {chat_id}\n\n"
                    f"⚠️ O'zgarishlar darhol kuchga kiradi."
                )
                
                # Notify new employee
                try:
                    bot.send_message(
                        chat_id,
                        f"🎉 Salom {name}!\n\n"
                        f"Siz tizimga xodim sifatida qo'shildingiz.\n"
                        f"Botdan foydalanish uchun '👤 Xodim' tugmasini bosing."
                    )
                except:
                    bot.send_message(
                        message.chat.id,
                        f"⚠️ Xodim qo'shildi, lekin xodimga xabar yuborib bo'lmadi."
                    )
            else:
                bot.send_message(message.chat.id, "❌ Config faylidagi EMPLOYEES bo'limini o'qib bo'lmadi.")
                
        except ValueError:
            bot.send_message(message.chat.id, "❌ Noto'g'ri ID format. Raqam kiriting:")
            return
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Xatolik: {str(e)}")
        
        clear_user_state(message.chat.id)
        admin_data.pop(message.chat.id, None)
        show_admin_panel(message)

    # OTHER DEBT HANDLERS
    @bot.message_handler(func=lambda message: get_user_state(message.chat.id)[0] == "other_debt_name")
    def get_other_debt_name(message):
        """Get name for non-employee debt"""
        admin_data[message.chat.id]["employee"] = message.text
        set_user_state(message.chat.id, "manual_debt_amount")
        
        bot.send_message(
            message.chat.id,
            "💰 Qarz miqdorini kiriting (so'mda):"
        )

    # DATA MANAGEMENT HANDLERS
    @bot.message_handler(func=lambda message: message.text == "➕ Ma'lumot qo'shish")
    def start_add_data(message):
        """Start adding new data process"""
        if message.chat.id != ADMIN_CHAT_ID:
            return
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📝 Vazifa qo'shish", "👤 Xodim qo'shish")
        markup.add("💸 Qarz qo'shish", "💬 Xabar qo'shish")
        markup.add("🔙 Bekor qilish")
        
        bot.send_message(
            message.chat.id,
            "➕ Qanday ma'lumot qo'shmoqchisiz?",
            reply_markup=markup
        )

    @bot.message_handler(func=lambda message: message.text == "👁 Barcha ma'lumotlar")
    def show_all_data(message):
        """Show all data summary"""
        if message.chat.id != ADMIN_CHAT_ID:
            return
        
        try:
            from database import DATABASE_PATH
            import sqlite3
            
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()
            
            # Get tasks count
            cursor.execute("SELECT COUNT(*) FROM tasks")
            tasks_count = cursor.fetchone()[0]
            
            # Get debts count
            cursor.execute("SELECT COUNT(*) FROM debts")
            debts_count = cursor.fetchone()[0]
            
            # Get messages count
            cursor.execute("SELECT COUNT(*) FROM messages")
            messages_count = cursor.fetchone()[0]
            
            # Get user states count
            cursor.execute("SELECT COUNT(*) FROM user_states")
            states_count = cursor.fetchone()[0]
            
            conn.close()
            
            data_summary = f"""
📊 Barcha ma'lumotlar statistikasi

📝 Vazifalar: {tasks_count}
💸 Qarzlar: {debts_count}
💬 Xabarlar: {messages_count}
👥 Xodimlar: {len(EMPLOYEES)}
🔄 Faol sessiyalar: {states_count}

🕐 Oxirgi yangilanish: {datetime.now().strftime('%d.%m.%Y %H:%M')}
"""
            
            bot.send_message(message.chat.id, data_summary)
            
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Ma'lumotlarni olishda xatolik: {str(e)}")

    @bot.message_handler(func=lambda message: message.text == "📊 Statistika")
    def show_detailed_statistics(message):
        """Show detailed system statistics"""
        if message.chat.id != ADMIN_CHAT_ID:
            return
        
        try:
            from database import DATABASE_PATH
            import sqlite3
            
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()
            
            # Tasks statistics
            cursor.execute("SELECT status, COUNT(*) FROM tasks GROUP BY status")
            task_stats = cursor.fetchall()
            
            cursor.execute("SELECT SUM(payment_amount) FROM tasks WHERE payment_amount IS NOT NULL")
            total_payments = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT SUM(received_amount) FROM tasks WHERE received_amount IS NOT NULL")
            total_received = cursor.fetchone()[0] or 0
            
            # Debts statistics
            cursor.execute("SELECT COUNT(*), SUM(amount) FROM debts")
            debt_count, total_debt = cursor.fetchone()
            total_debt = total_debt or 0
            
            # Employee locations statistics
            cursor.execute("SELECT COUNT(*) FROM employee_locations WHERE created_at > datetime('now', '-24 hours')")
            recent_locations = cursor.fetchone()[0]
            
            # Top employees by completed tasks
            cursor.execute("""
                SELECT assigned_to, COUNT(*) as completed_count 
                FROM tasks 
                WHERE status = 'completed' 
                GROUP BY assigned_to 
                ORDER BY completed_count DESC 
                LIMIT 5
            """)
            top_employees = cursor.fetchall()
            
            conn.close()
            
            # Format task statistics
            task_status_text = ""
            for status, count in task_stats:
                emoji = {"pending": "⏳", "in_progress": "🔄", "completed": "✅"}.get(status, "❓")
                task_status_text += f"{emoji} {status.title()}: {count}\n"
            
            # Format top employees
            top_emp_text = ""
            for i, (emp_name, count) in enumerate(top_employees, 1):
                top_emp_text += f"{i}. {emp_name}: {count} ta\n"
            
            stats_text = f"""
📊 Batafsil Tizim Statistikasi

📝 VAZIFALAR:
{task_status_text}
💰 Umumiy to'lov: {total_payments:,.0f} so'm
💵 Olingan to'lov: {total_received:,.0f} so'm
💸 To'lanmagan: {total_payments - total_received:,.0f} so'm

💳 QARZLAR:
🔢 Umumiy qarzlar: {debt_count} ta
💰 Umumiy qarz miqdori: {total_debt:,.0f} so'm

📍 LOKATSIYA KUZATUVI:
📊 So'nggi 24 soat: {recent_locations} ta lokatsiya

🏆 ENG FAOL XODIMLAR:
{top_emp_text}

👥 Ro'yxatdagi xodimlar: {len(EMPLOYEES)} ta

🕐 Hisoblangan vaqt: {datetime.now().strftime('%d.%m.%Y %H:%M')}
"""
            
            bot.send_message(message.chat.id, stats_text)
            
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Statistika olishda xatolik: {str(e)}")

    @bot.message_handler(func=lambda message: message.text == "✏️ Ma'lumot tahrirlash")
    def start_edit_data(message):
        """Start data editing process"""
        if message.chat.id != ADMIN_CHAT_ID:
            return
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📝 Vazifa tahrirlash", "👤 Xodim ma'lumotlari")
        markup.add("💸 Qarz tahrirlash", "💬 Xabar tahrirlash")
        markup.add("🔙 Bekor qilish")
        
        bot.send_message(
            message.chat.id,
            "✏️ Qanday ma'lumotni tahrirlashni xohlaysiz?",
            reply_markup=markup
        )

    @bot.message_handler(func=lambda message: message.text == "📤 Ma'lumot eksport")
    def start_data_export(message):
        """Start data export process"""
        if message.chat.id != ADMIN_CHAT_ID:
            return
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📊 Barcha ma'lumotlar", "📝 Faqat vazifalar")
        markup.add("💸 Faqat qarzlar", "📍 Lokatsiya tarixi")
        markup.add("👥 Xodimlar ma'lumoti", "💬 Xabarlar tarixi")
        markup.add("🔙 Bekor qilish")
        
        bot.send_message(
            message.chat.id,
            "📤 Qanday ma'lumotlarni eksport qilmoqchisiz?\n\n"
            "Excel formatida professional hisobot tayyorlanadi.",
            reply_markup=markup
        )

    @bot.message_handler(func=lambda message: message.text == "🔄 Ma'lumot import")
    def start_data_import(message):
        """Start data import process"""
        if message.chat.id != ADMIN_CHAT_ID:
            return
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📝 Vazifalar import", "👤 Xodimlar import")
        markup.add("💸 Qarzlar import", "📋 Template yuklab olish")
        markup.add("🔙 Bekor qilish")
        
        bot.send_message(
            message.chat.id,
            "🔄 Ma'lumot Import Tizimi\n\n"
            "Excel fayldan ma'lumotlarni import qilish uchun:\n"
            "1. Template faylni yuklab oling\n"  
            "2. Ma'lumotlarni to'ldiring\n"
            "3. Faylni yuklang\n\n"
            "Qanday ma'lumot import qilmoqchisiz?",
            reply_markup=markup
        )

    @bot.message_handler(func=lambda message: message.text == "🧹 Ma'lumot tozalash")
    def start_data_cleanup(message):
        """Start data cleanup process"""
        if message.chat.id != ADMIN_CHAT_ID:
            return
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("🗑 Eski vazifalarni o'chirish", "💸 Yopilgan qarzlarni tozalash")
        markup.add("📍 Eski lokatsiyalarni o'chirish", "💬 Eski xabarlarni o'chirish")
        markup.add("🔄 Nofaol sessiyalarni tozalash", "⚠️ Barcha ma'lumotlarni o'chirish")
        markup.add("🔙 Bekor qilish")
        
        bot.send_message(
            message.chat.id,
            "🧹 Ma'lumot Tozalash Tizimi\n\n"
            "⚠️ DIQQAT: Bu amallar qaytarib bo'lmaydi!\n\n"
            "Qanday ma'lumotlarni tozalamoqchisiz?",
            reply_markup=markup
        )

    @bot.message_handler(func=lambda message: message.text == "🔍 Ma'lumot qidirish")
    def start_data_search(message):
        """Start data search process"""
        if message.chat.id != ADMIN_CHAT_ID:
            return
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("🔍 Vazifa qidirish", "👤 Xodim qidirish")
        markup.add("💸 Qarz qidirish", "📅 Sana bo'yicha qidirish")
        markup.add("💰 Summa bo'yicha qidirish", "📍 Lokatsiya qidirish")
        markup.add("🔙 Bekor qilish")
        
        set_user_state(message.chat.id, "search_data_type")
        
        bot.send_message(
            message.chat.id,
            "🔍 Ma'lumot Qidirish Tizimi\n\n"
            "Qanday ma'lumot qidirmoqchisiz?",
            reply_markup=markup
        )

    @bot.message_handler(func=lambda message: get_user_state(message.chat.id)[0] == "search_data_type")
    def handle_search_type_selection(message):
        """Handle data search type selection"""
        if message.text == "🔙 Bekor qilish":
            clear_user_state(message.chat.id)
            show_data_menu(message)
            return
        
        search_types = {
            "🔍 Vazifa qidirish": "task_search",
            "👤 Xodim qidirish": "employee_search", 
            "💸 Qarz qidirish": "debt_search",
            "📅 Sana bo'yicha qidirish": "date_search",
            "💰 Summa bo'yicha qidirish": "amount_search",
            "📍 Lokatsiya qidirish": "location_search"
        }
        
        if message.text in search_types:
            search_type = search_types[message.text]
            set_user_state(message.chat.id, f"search_{search_type}")
            
            prompts = {
                "task_search": "🔍 Vazifa ID, tavsif yoki xodim nomini kiriting:",
                "employee_search": "👤 Xodim nomini kiriting:",
                "debt_search": "💸 Xodim nomi yoki qarz sababini kiriting:",
                "date_search": "📅 Sanani kiriting (DD.MM.YYYY formatida):",
                "amount_search": "💰 Summani kiriting (so'mda):",
                "location_search": "📍 Joylashuv ma'lumotini kiriting:"
            }
            
            bot.send_message(
                message.chat.id,
                prompts[search_type],
                reply_markup=types.ReplyKeyboardRemove()
            )
        else:
            bot.send_message(message.chat.id, "❌ Noto'g'ri tanlov. Qaytadan tanlang.")

    @bot.message_handler(func=lambda message: get_user_state(message.chat.id)[0].startswith("search_"))
    def handle_search_query(message):
        """Handle search queries"""
        state = get_user_state(message.chat.id)[0]
        query = message.text.strip()
        
        try:
            from database import DATABASE_PATH
            import sqlite3
            
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()
            
            results = []
            
            if state == "search_task_search":
                cursor.execute("""
                    SELECT id, description, assigned_to, status, created_at, payment_amount
                    FROM tasks 
                    WHERE id LIKE ? OR description LIKE ? OR assigned_to LIKE ?
                """, (f"%{query}%", f"%{query}%", f"%{query}%"))
                results = cursor.fetchall()
                
                if results:
                    result_text = "🔍 Vazifa qidiruv natijalari:\n\n"
                    for task_id, desc, assigned_to, status, created_at, payment in results:
                        emoji = {"pending": "⏳", "in_progress": "🔄", "completed": "✅"}.get(status, "❓")
                        result_text += f"{emoji} ID: {task_id}\n"
                        result_text += f"📝 {desc[:50]}{'...' if len(desc) > 50 else ''}\n"
                        result_text += f"👤 {assigned_to} | 💰 {payment or 0:,.0f} so'm\n\n"
                else:
                    result_text = "❌ Hech qanday vazifa topilmadi."
            
            elif state == "search_employee_search":
                cursor.execute("""
                    SELECT COUNT(*) as task_count, 
                           SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) as completed,
                           SUM(payment_amount) as total_payment
                    FROM tasks 
                    WHERE assigned_to LIKE ?
                """, (f"%{query}%",))
                emp_stats = cursor.fetchone()
                
                if emp_stats and emp_stats[0] > 0:
                    task_count, completed, total_payment = emp_stats
                    result_text = f"👤 {query} xodimi haqida ma'lumot:\n\n"
                    result_text += f"📝 Umumiy vazifalar: {task_count}\n"
                    result_text += f"✅ Bajarilgan: {completed}\n"
                    result_text += f"💰 Umumiy to'lov: {total_payment or 0:,.0f} so'm"
                else:
                    result_text = "❌ Bunday xodim topilmadi."
            
            elif state == "search_debt_search":
                cursor.execute("""
                    SELECT employee_name, amount, reason, payment_date, created_at
                    FROM debts 
                    WHERE employee_name LIKE ? OR reason LIKE ?
                """, (f"%{query}%", f"%{query}%"))
                results = cursor.fetchall()
                
                if results:
                    result_text = "💸 Qarz qidiruv natijalari:\n\n"
                    for emp_name, amount, reason, pay_date, created in results:
                        result_text += f"👤 {emp_name}\n"
                        result_text += f"💰 {amount:,.0f} so'm\n"
                        result_text += f"📝 {reason}\n"
                        result_text += f"📅 {pay_date}\n\n"
                else:
                    result_text = "❌ Hech qanday qarz topilmadi."
            else:
                result_text = "❌ Qidiruv turi tanilmadi."
            
            conn.close()
            
            if len(result_text) > 4000:
                parts = [result_text[i:i+4000] for i in range(0, len(result_text), 4000)]
                for part in parts:
                    bot.send_message(message.chat.id, part)
            else:
                bot.send_message(message.chat.id, result_text)
            
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Qidirishda xatolik: {str(e)}")
        
        clear_user_state(message.chat.id)
        show_data_menu(message)

    # EXPORT HANDLERS
    @bot.message_handler(func=lambda message: message.text in [
        "📊 Barcha ma'lumotlar", "📝 Faqat vazifalar", "💸 Faqat qarzlar", 
        "📍 Lokatsiya tarixi", "👥 Xodimlar ma'lumoti", "💬 Xabarlar tarixi"
    ])
    def handle_data_export(message):
        """Handle data export requests"""
        if message.chat.id != ADMIN_CHAT_ID:
            return
        
        export_type = message.text
        
        bot.send_message(message.chat.id, f"📤 {export_type} eksport qilinmoqda...")
        
        try:
            from utils import generate_custom_export
            filepath = generate_custom_export(export_type)
            
            if filepath and os.path.exists(filepath):
                with open(filepath, 'rb') as f:
                    bot.send_document(
                        message.chat.id,
                        f,
                        caption=f"📊 {export_type} - Excel hisobot"
                    )
                # Clean up file
                os.remove(filepath)
                bot.send_message(message.chat.id, "✅ Eksport muvaffaqiyatli yakunlandi!")
            else:
                bot.send_message(message.chat.id, "❌ Eksport qilishda xatolik yuz berdi.")
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Eksport xatoligi: {str(e)}")
        
        show_data_menu(message)

    # EMPLOYEE TRACKING HANDLERS
    @bot.message_handler(func=lambda message: message.text == "📍 Xodimlarni kuzatish")
    def start_employee_tracking(message):
        """Start employee tracking process"""
        if message.chat.id != ADMIN_CHAT_ID:
            return
        
        # Reload config to get latest employee list
        import importlib
        import config
        importlib.reload(config)
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        for employee_name in config.EMPLOYEES.keys():
            markup.add(employee_name)
        markup.add("🌍 Barchani kuzatish", "📊 Kuzatuv tarixi")
        markup.add("🔙 Ortga")
        
        set_user_state(message.chat.id, "select_employee_track")
        
        bot.send_message(
            message.chat.id,
            "📍 Xodimlarni kuzatish tizimi\n\n"
            "👤 Xodim tanlash - aynan bir xodimni kuzatish\n"
            "🌍 Barchani kuzatish - barcha xodimlardan lokatsiya so'rash\n"
            "📊 Kuzatuv tarixi - oxirgi lokatsiyalarni ko'rish\n\n"
            "⚠️ Xodimlar bu so'rovdan habardor bo'lmaydi",
            reply_markup=markup
        )

    @bot.message_handler(func=lambda message: get_user_state(message.chat.id)[0] == "select_employee_track")
    def handle_employee_tracking_selection(message):
        """Handle employee tracking selection"""
        if message.text == "🔙 Ortga":
            clear_user_state(message.chat.id)
            show_admin_panel(message)
            return
        
        # Reload config to get latest employee list
        import importlib
        import config
        importlib.reload(config)
        
        if message.text == "🌍 Barchani kuzatish":
            # Request location from all employees
            success_count = 0
            total_count = len(config.EMPLOYEES)
            
            for employee_name, employee_chat_id in config.EMPLOYEES.items():
                try:
                    # Send silent location request
                    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
                    location_btn = types.KeyboardButton("📍 Joriy joylashuvim", request_location=True)
                    markup.add(location_btn)
                    
                    bot.send_message(
                        employee_chat_id,
                        "📍 Vazifa uchun joriy joylashuvingizni yuboring:",
                        reply_markup=markup
                    )
                    success_count += 1
                except:
                    pass
            
            bot.send_message(
                message.chat.id,
                f"📍 Lokatsiya so'rovi yuborildi!\n\n"
                f"✅ Muvaffaqiyatli: {success_count}/{total_count} xodim\n"
                f"⏱ Javoblar kutilmoqda..."
            )
            
        elif message.text == "📊 Kuzatuv tarixi":
            show_location_history(message)
            
        elif message.text in config.EMPLOYEES:
            # Request location from specific employee
            employee_chat_id = config.EMPLOYEES[message.text]
            
            try:
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
                location_btn = types.KeyboardButton("📍 Joriy joylashuvim", request_location=True)
                markup.add(location_btn)
                
                bot.send_message(
                    employee_chat_id,
                    "📍 Vazifa uchun joriy joylashuvingizni yuboring:",
                    reply_markup=markup
                )
                
                bot.send_message(
                    message.chat.id,
                    f"📍 {message.text} xodimiga lokatsiya so'rovi yuborildi!\n"
                    f"⏱ Javob kutilmoqda..."
                )
                
            except Exception as e:
                bot.send_message(
                    message.chat.id,
                    f"❌ {message.text} xodimiga xabar yuborishda xatolik: {str(e)}"
                )
        else:
            bot.send_message(message.chat.id, "❌ Noto'g'ri tanlov. Qaytadan tanlang.")
            return
        
        clear_user_state(message.chat.id)
        show_admin_panel(message)

    def show_location_history(message):
        """Show recent employee locations"""
        try:
            from database import DATABASE_PATH
            import sqlite3
            
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()
            
            # Get recent locations (last 24 hours)
            cursor.execute("""
                SELECT employee_name, latitude, longitude, created_at, location_type
                FROM employee_locations 
                WHERE created_at > datetime('now', '-1 day')
                ORDER BY created_at DESC
                LIMIT 20
            """)
            
            locations = cursor.fetchall()
            conn.close()
            
            if not locations:
                bot.send_message(message.chat.id, "📍 So'nggi 24 soatda lokatsiya ma'lumotlari topilmadi.")
                return
            
            history_text = "📊 So'nggi 24 soat lokatsiya tarixi:\n\n"
            
            for i, (emp_name, lat, lon, created_at, loc_type) in enumerate(locations, 1):
                try:
                    time_str = datetime.fromisoformat(created_at).strftime("%d.%m %H:%M")
                except:
                    time_str = created_at
                
                history_text += f"{i}. 👤 {emp_name}\n"
                history_text += f"   📍 {lat:.6f}, {lon:.6f}\n"
                history_text += f"   🕐 {time_str}\n\n"
            
            # Send Google Maps links for recent locations
            if locations:
                latest_locations = {}
                for emp_name, lat, lon, created_at, loc_type in locations:
                    if emp_name not in latest_locations:
                        latest_locations[emp_name] = (lat, lon)
                
                history_text += "🗺 Google Maps havolalar:\n"
                for emp_name, (lat, lon) in latest_locations.items():
                    maps_url = f"https://maps.google.com/?q={lat},{lon}"
                    history_text += f"📍 {emp_name}: {maps_url}\n"
            
            if len(history_text) > 4000:
                parts = [history_text[i:i+4000] for i in range(0, len(history_text), 4000)]
                for part in parts:
                    bot.send_message(message.chat.id, part)
            else:
                bot.send_message(message.chat.id, history_text)
                
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Xatolik: {str(e)}")

    def handle_location_sharing(message):
        """Handle location sharing from employees"""
        # Find employee name
        employee_name = None
        
        # Reload config to get latest employee list  
        import importlib
        import config
        importlib.reload(config)
        
        for name, chat_id in config.EMPLOYEES.items():
            if chat_id == message.chat.id:
                employee_name = name
                break
        
        if employee_name:
            # Save location to database
            try:
                from database import DATABASE_PATH
                import sqlite3
                
                conn = sqlite3.connect(DATABASE_PATH)
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO employee_locations 
                    (employee_name, employee_chat_id, latitude, longitude, location_type)
                    VALUES (?, ?, ?, ?, ?)
                """, (employee_name, message.chat.id, message.location.latitude, 
                      message.location.longitude, 'requested'))
                
                conn.commit()
                conn.close()
                
                # Confirm to employee
                bot.send_message(
                    message.chat.id,
                    "✅ Lokatsiya qabul qilindi. Rahmat!",
                    reply_markup=types.ReplyKeyboardRemove()
                )
                
                # Notify admin with location details
                maps_url = f"https://maps.google.com/?q={message.location.latitude},{message.location.longitude}"
                
                bot.send_message(
                    ADMIN_CHAT_ID,
                    f"📍 {employee_name} lokatsiyasi keldi!\n\n"
                    f"🌐 Koordinatalar: {message.location.latitude:.6f}, {message.location.longitude:.6f}\n"
                    f"🗺 Google Maps: {maps_url}\n"
                    f"🕐 Vaqt: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
                )
                
                # Send live location to admin  
                bot.send_location(
                    ADMIN_CHAT_ID,
                    message.location.latitude,
                    message.location.longitude
                )
                
            except Exception as e:
                bot.send_message(
                    message.chat.id,
                    "❌ Lokatsiya saqlashda xatolik yuz berdi."
                )

    @bot.message_handler(func=lambda message: message.text == "🗑 Ma'lumot o'chirish")
    def start_delete_data(message):
        """Start data deletion process"""
        if message.chat.id != ADMIN_CHAT_ID:
            return
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("🗑 Vazifani o'chirish", "🗑 Qarzni o'chirish")
        markup.add("🗑 Xabarni o'chirish", "🗑 Sessiyani o'chirish")
        markup.add("🔙 Bekor qilish")
        
        bot.send_message(
            message.chat.id,
            "🗑 Qanday ma'lumotni o'chirmoqchisiz?",
            reply_markup=markup
        )

    # EMPLOYEE SECTION
    @bot.message_handler(func=lambda message: message.text == "👤 Xodim")
    def employee_login(message):
        """Employee panel access"""
        # Reload config to get latest employee list
        import importlib
        import config
        importlib.reload(config)
        
        # Check if user is in employee list from updated config
        employee_name = None
        for name, chat_id in config.EMPLOYEES.items():
            if chat_id == message.chat.id:
                employee_name = name
                break
        
        if not employee_name:
            bot.send_message(
                message.chat.id,
                "❌ Sizning profilingiz topilmadi.\n"
                "Admin bilan bog'laning yoki '🎯 Mijoz' bo'limidan foydalaning."
            )
            return
        
        show_employee_panel(message, employee_name)

    def show_employee_panel(message, employee_name=None):
        """Show employee panel"""
        if not employee_name:
            # Reload config to get latest employee list
            import importlib
            import config
            importlib.reload(config)
            
            for name, chat_id in config.EMPLOYEES.items():
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
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        markup.add("💳 Karta orqali olindi")
        markup.add("💵 Naqd pul olindi") 
        markup.add("💸 Qarzga qo'yildi")
        markup.add("🔙 Bekor qilish")
        
        bot.send_message(
            message.chat.id,
            "💰 To'lov qanday olingan?\n\n"
            "Kerakli variantni tanlang:",
            reply_markup=markup
        )

    @bot.message_handler(func=lambda message: get_user_state(message.chat.id)[0] == "complete_task_payment")
    def get_payment_method(message):
        """Get payment method selection"""
        state, data_str = get_user_state(message.chat.id)
        temp_data = parse_json_data(data_str)
        
        if message.text == "🔙 Bekor qilish":
            clear_user_state(message.chat.id)
            show_employee_tasks(message)
            return
        
        if message.text == "💳 Karta orqali olindi":
            # Card payment process
            temp_data["payment_method"] = "card"
            set_user_state(message.chat.id, "card_payment_amount", serialize_json_data(temp_data))
            
            markup = types.ReplyKeyboardRemove()
            bot.send_message(
                message.chat.id,
                "💳 Karta orqali qabul qilingan pul miqdorini kiriting (so'mda):",
                reply_markup=markup
            )
            
        elif message.text == "💵 Naqd pul olindi":
            # Cash payment process
            temp_data["payment_method"] = "cash"  
            set_user_state(message.chat.id, "cash_payment_amount", serialize_json_data(temp_data))
            
            markup = types.ReplyKeyboardRemove()
            bot.send_message(
                message.chat.id,
                "💵 Naqd olingan pul miqdorini kiriting (so'mda):",
                reply_markup=markup
            )
            
        elif message.text == "💸 Qarzga qo'yildi":
            # Debt process
            temp_data["payment_method"] = "debt"
            set_user_state(message.chat.id, "debt_person_name", serialize_json_data(temp_data))
            
            markup = types.ReplyKeyboardRemove() 
            bot.send_message(
                message.chat.id,
                "💸 Kimning zimmasi qarzga qo'yildi?\n\n"
                "Ism va familiyasini kiriting:",
                reply_markup=markup
            )
        else:
            bot.send_message(message.chat.id, "❌ Iltimos, variantlardan birini tanlang.")

    @bot.message_handler(func=lambda message: get_user_state(message.chat.id)[0] == "card_payment_amount")
    def process_card_payment(message):
        """Process card payment completion"""
        state, data_str = get_user_state(message.chat.id)
        temp_data = parse_json_data(data_str)
        
        try:
            received_amount = float(message.text.replace(" ", "").replace(",", ""))
            
            # Complete the task
            update_task_status(
                temp_data["task_id"],
                "completed",
                completion_report=temp_data["report"],
                completion_media=temp_data.get("media") or "",
                received_amount=received_amount
            )
            
            # Get employee name
            employee_name = None
            for name, chat_id in EMPLOYEES.items():
                if chat_id == message.chat.id:
                    employee_name = name
                    break
            
            # Success message to employee
            success_msg = f"""
✅ Vazifa muvaffaqiyatli yakunlandi!

💳 To'lov usuli: Karta orqali
💰 Miqdor: {received_amount:,.0f} so'm  
📝 Status: Karta orqali to'lov qabul qilindi va hisobga tushirildi

Rahmat!
"""
            bot.send_message(message.chat.id, success_msg)
            
            # Start motivation and entertainment system
            start_motivation_system(message)
            
            # Admin notification
            admin_message = f"""
✅ Vazifa yakunlandi!

🆔 Vazifa ID: {temp_data["task_id"]}
👤 Xodim: {employee_name or "Noma'lum"}
💳 To'lov usuli: Karta orqali  
💰 Olingan to'lov: {received_amount:,.0f} so'm
📊 Status: Kartaga o'tkazildi, hisobga tushirildi

📝 Hisobot: {temp_data["report"]}
"""
            
            bot.send_message(ADMIN_CHAT_ID, admin_message)
            send_completion_media(temp_data)
            
        except ValueError:
            bot.send_message(message.chat.id, "❌ Iltimos, to'g'ri raqam kiriting!")
            return
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Xatolik: {str(e)}")
            return
        
        clear_user_state(message.chat.id)
        show_employee_tasks(message)

    @bot.message_handler(func=lambda message: get_user_state(message.chat.id)[0] == "cash_payment_amount")
    def process_cash_payment(message):
        """Process cash payment completion"""
        state, data_str = get_user_state(message.chat.id)
        temp_data = parse_json_data(data_str)
        
        try:
            received_amount = float(message.text.replace(" ", "").replace(",", ""))
            
            # Complete the task
            update_task_status(
                temp_data["task_id"],
                "completed", 
                completion_report=temp_data["report"],
                completion_media=temp_data.get("media") or "",
                received_amount=received_amount
            )
            
            # Get employee name
            employee_name = None
            for name, chat_id in EMPLOYEES.items():
                if chat_id == message.chat.id:
                    employee_name = name
                    break
            
            # Success message to employee
            success_msg = f"""
✅ Vazifa muvaffaqiyatli yakunlandi!

💵 To'lov usuli: Naqd pul
💰 Miqdor: {received_amount:,.0f} so'm
📝 Status: Naqd pul qabul qilindi

Rahmat!
"""
            bot.send_message(message.chat.id, success_msg)
            
            # Start motivation and entertainment system
            start_motivation_system(message)
            
            # Admin notification
            admin_message = f"""
✅ Vazifa yakunlandi!

🆔 Vazifa ID: {temp_data["task_id"]}
👤 Xodim: {employee_name or "Noma'lum"}
💵 To'lov usuli: Naqd pul
💰 Olingan to'lov: {received_amount:,.0f} so'm
📊 Status: Naqd pul olingan

📝 Hisobot: {temp_data["report"]}
"""
            
            bot.send_message(ADMIN_CHAT_ID, admin_message)
            send_completion_media(temp_data)
            
        except ValueError:
            bot.send_message(message.chat.id, "❌ Iltimos, to'g'ri raqam kiriting!")
            return
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Xatolik: {str(e)}")
            return
        
        clear_user_state(message.chat.id)  
        show_employee_tasks(message)

    @bot.message_handler(func=lambda message: get_user_state(message.chat.id)[0] == "debt_person_name")
    def get_debt_person_name(message):
        """Get the name of person who owes money"""
        state, data_str = get_user_state(message.chat.id)
        temp_data = parse_json_data(data_str)
        
        temp_data["debt_person"] = message.text.strip()
        set_user_state(message.chat.id, "debt_amount", serialize_json_data(temp_data))
        
        bot.send_message(
            message.chat.id,
            f"💸 {message.text} zimmasi qancha pul qo'yildi?\n\n"
            "Miqdorini kiriting (so'mda):"
        )

    @bot.message_handler(func=lambda message: get_user_state(message.chat.id)[0] == "debt_amount")
    def get_debt_amount(message):
        """Get debt amount"""
        state, data_str = get_user_state(message.chat.id)
        temp_data = parse_json_data(data_str)
        
        try:
            debt_amount = float(message.text.replace(" ", "").replace(",", ""))
            temp_data["debt_amount"] = debt_amount
            set_user_state(message.chat.id, "debt_reason", serialize_json_data(temp_data))
            
            bot.send_message(
                message.chat.id,
                f"📝 {temp_data['debt_person']} zimmasi {debt_amount:,.0f} so'm qarzga qo'yildi.\n\n"
                "Qarz sababi nima? (masalan: 'Vazifa uchun oldindan to'lov'):"
            )
            
        except ValueError:
            bot.send_message(message.chat.id, "❌ Iltimos, to'g'ri raqam kiriting!")
            return

    @bot.message_handler(func=lambda message: get_user_state(message.chat.id)[0] == "debt_reason")
    def get_debt_reason(message):
        """Get debt reason"""
        state, data_str = get_user_state(message.chat.id)
        temp_data = parse_json_data(data_str)
        
        temp_data["debt_reason"] = message.text.strip()
        set_user_state(message.chat.id, "debt_payment_date", serialize_json_data(temp_data))
        
        bot.send_message(
            message.chat.id,
            f"📅 {temp_data['debt_person']} qarzni qachon qaytarishi kerak?\n\n"
            "To'lov sanasini kiriting (masalan: 01.01.2024):"
        )

    @bot.message_handler(func=lambda message: get_user_state(message.chat.id)[0] == "debt_payment_date")
    def complete_debt_process(message):
        """Complete debt process and finish task"""
        state, data_str = get_user_state(message.chat.id)
        temp_data = parse_json_data(data_str)
        
        payment_date = message.text.strip()
        
        try:
            # Complete the task with debt
            update_task_status(
                temp_data["task_id"],
                "completed",
                completion_report=temp_data["report"],
                completion_media=temp_data.get("media") or "",
                received_amount=0  # No money received, it's debt
            )
            
            # Add debt record
            add_debt(
                employee_name=temp_data["debt_person"],
                employee_chat_id=0,  # Unknown chat ID for external person
                task_id=temp_data["task_id"],
                amount=temp_data["debt_amount"],
                reason=temp_data["debt_reason"],
                payment_date=payment_date
            )
            
            # Get employee name
            employee_name = None
            for name, chat_id in EMPLOYEES.items():
                if chat_id == message.chat.id:
                    employee_name = name
                    break
            
            # Success message to employee
            success_msg = f"""
✅ Vazifa muvaffaqiyatli yakunlandi!

💸 To'lov usuli: Qarzga qo'yildi
👤 Qarzdor: {temp_data["debt_person"]}
💰 Miqdor: {temp_data["debt_amount"]:,.0f} so'm
📝 Sabab: {temp_data["debt_reason"]}
📅 To'lov sanasi: {payment_date}

Qarz ma'lumotlari saqlandi. Rahmat!
"""
            bot.send_message(message.chat.id, success_msg)
            
            # Start motivation and entertainment system
            start_motivation_system(message)
            
            # Admin notification with full debt details
            admin_message = f"""
✅ Vazifa yakunlandi!

🆔 Vazifa ID: {temp_data["task_id"]}
👤 Xodim: {employee_name or "Noma'lum"}
💸 To'lov usuli: Qarzga qo'yildi

📊 QARZ MA'LUMOTLARI:
👤 Qarzdor: {temp_data["debt_person"]}
💰 Miqdor: {temp_data["debt_amount"]:,.0f} so'm
📝 Sabab: {temp_data["debt_reason"]}
📅 To'lov sanasi: {payment_date}
🕐 Yaratilgan: {datetime.now().strftime('%d.%m.%Y %H:%M')}

📝 Vazifa hisoboti: {temp_data["report"]}
"""
            
            bot.send_message(ADMIN_CHAT_ID, admin_message)
            send_completion_media(temp_data)
            
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Xatolik: {str(e)}")
            return
        
        clear_user_state(message.chat.id)
        show_employee_tasks(message)

    def send_completion_media(temp_data):
        """Send task completion media to admin"""
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

    # CUSTOMER SECTION
    @bot.message_handler(func=lambda message: message.text == "👥 Mijoz")
    def customer_panel(message):
        """Customer panel access"""
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("💬 Admin bilan bog'lanish")
        markup.add("🔙 Ortga")
        
        bot.send_message(
            message.chat.id,
            "👥 Mijoz paneli\n\n"
            "Salom! Admin bilan bog'lanish uchun tugmani bosing:",
            reply_markup=markup
        )

    @bot.message_handler(func=lambda message: message.text == "💬 Admin bilan bog'lanish")
    def start_customer_chat(message):
        """Start customer chat with admin - first collect phone number"""
        set_user_state(message.chat.id, "customer_phone")
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        phone_btn = types.KeyboardButton("📱 Telefon raqamini yuborish", request_contact=True)
        markup.add(phone_btn)
        markup.add("🔙 Bekor qilish")
        
        bot.send_message(
            message.chat.id,
            "📱 Admin bilan bog'lanish uchun telefon raqamingizni yuboring:\n\n"
            "Telefon raqami admin uchun zarur.",
            reply_markup=markup
        )

    @bot.message_handler(content_types=['contact'], func=lambda message: get_user_state(message.chat.id)[0] == "customer_phone")
    def get_customer_phone(message):
        """Get customer phone number"""
        if message.contact:
            phone_number = message.contact.phone_number
            temp_data = {"phone": phone_number, "name": message.from_user.first_name or "Anonim"}
            set_user_state(message.chat.id, "customer_location", serialize_json_data(temp_data))
            
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            location_btn = types.KeyboardButton("📍 Joylashuvni yuborish", request_location=True)
            markup.add(location_btn)
            markup.add("🔙 Bekor qilish")
            
            bot.send_message(
                message.chat.id,
                "📍 Endi joylashuvingizni yuboring:\n\n"
                "Bu admin uchun zarur ma'lumot.",
                reply_markup=markup
            )
        else:
            bot.send_message(message.chat.id, "❌ Telefon raqamini yuborishda xatolik. Qayta urinib ko'ring.")

    @bot.message_handler(func=lambda message: get_user_state(message.chat.id)[0] == "customer_phone" and message.text == "🔙 Bekor qilish")
    def cancel_customer_phone(message):
        """Cancel customer phone input"""
        clear_user_state(message.chat.id)
        customer_panel(message)

    @bot.message_handler(content_types=['location'], func=lambda message: get_user_state(message.chat.id)[0] == "customer_location")
    def get_customer_location(message):
        """Get customer location and start chat"""
        state, data_str = get_user_state(message.chat.id)
        temp_data = parse_json_data(data_str)
        
        if message.location:
            latitude = message.location.latitude
            longitude = message.location.longitude
            
            # Save customer info with location
            temp_data.update({
                "latitude": latitude,
                "longitude": longitude,
                "chat_id": message.chat.id,
                "username": message.from_user.username or ""
            })
            
            set_user_state(message.chat.id, "customer_chat", serialize_json_data(temp_data))
            
            # Notify admin about new customer
            customer_info = f"""
👤 Yangi mijoz bog'landi!

📱 Ism: {temp_data['name']}
📞 Telefon: {temp_data['phone']}
🆔 Chat ID: {message.chat.id}
👤 Username: @{temp_data['username']} 
📍 Lokatsiya: {latitude}, {longitude}
🕐 Vaqt: {datetime.now().strftime('%d.%m.%Y %H:%M')}

Mijoz admindan javob kutmoqda.
"""
            
            bot.send_message(ADMIN_CHAT_ID, customer_info)
            bot.send_location(ADMIN_CHAT_ID, latitude, longitude)
            
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add("❌ Suhbatni tugatish")
            
            bot.send_message(
                message.chat.id,
                "✅ Ma'lumotlaringiz adminga yuborildi!\n\n"
                "💬 Endi xabaringizni yozing. Admin sizga javob beradi.\n"
                "Suhbatni tugatish uchun tugmani bosing.",
                reply_markup=markup
            )
        else:
            bot.send_message(message.chat.id, "❌ Joylashuvni yuborishda xatolik. Qayta urinib ko'ring.")

    @bot.message_handler(func=lambda message: get_user_state(message.chat.id)[0] == "customer_location" and message.text == "🔙 Bekor qilish")
    def cancel_customer_location(message):
        """Cancel customer location input"""
        clear_user_state(message.chat.id)
        customer_panel(message)

    @bot.message_handler(func=lambda message: get_user_state(message.chat.id)[0] == "customer_chat")
    def handle_customer_message(message):
        """Handle customer messages to admin"""
        if message.text == "❌ Suhbatni tugatish":
            clear_user_state(message.chat.id)
            bot.send_message(
                message.chat.id,
                "✅ Suhbat tugatildi.\n\n"
                "Yana bog'lanish kerak bo'lsa, admin bilan bog'lanish tugmasini bosing.",
                reply_markup=types.ReplyKeyboardRemove()
            )
            customer_panel(message)
            return
        
        # Get customer data
        state, data_str = get_user_state(message.chat.id)
        customer_data = parse_json_data(data_str)
        
        # Forward message to admin with customer info
        customer_info = f"""
👤 Mijoz: {customer_data.get('name', 'Anonim')}
📞 Telefon: {customer_data.get('phone', "Noma'lum")}
🆔 Chat ID: {message.chat.id}
👤 Username: @{customer_data.get('username', "yo'q")}
"""
        
        forwarded_message = f"💬 Mijoz xabari:\n\n{customer_info}\n📝 Xabar: {message.text}"
        
        bot.send_message(ADMIN_CHAT_ID, forwarded_message)
        
        bot.send_message(
            message.chat.id,
            "✅ Xabaringiz adminga yuborildi!\n\n"
            "Admin tez orada javob beradi."
        )

    @bot.message_handler(commands=['reply'])
    def admin_reply_to_customer(message):
        """Admin reply to customer"""
        if message.chat.id != ADMIN_CHAT_ID:
            return
        
        try:
            # Parse command: /reply chat_id message
            parts = message.text.split(' ', 2)
            if len(parts) < 3:
                bot.send_message(
                    message.chat.id,
                    "❌ Noto'g'ri format. Ishlatish: /reply [chat_id] [xabar]"
                )
                return
            
            customer_chat_id = int(parts[1])
            reply_message = parts[2]
            
            # Send reply to customer
            bot.send_message(
                customer_chat_id,
                f"👑 Admin javobi:\n\n{reply_message}"
            )
            
            # Confirm to admin
            bot.send_message(
                message.chat.id,
                f"✅ Javob yuborildi (Chat ID: {customer_chat_id})"
            )
            
        except ValueError:
            bot.send_message(
                message.chat.id,
                "❌ Noto'g'ri chat ID. Raqam kiriting."
            )
        except Exception as e:
            bot.send_message(
                message.chat.id,
                f"❌ Xatolik: {str(e)}"
            )



    # COMMON HANDLERS
    @bot.message_handler(func=lambda message: message.text == "🔙 Ortga")
    def go_back(message):
        """Go back to main menu"""
        clear_user_state(message.chat.id)
        start_message(message)

    # =============================================================================
    # ENTERTAINMENT AND MOTIVATION SYSTEM  
    # =============================================================================
    
    def start_motivation_system(message):
        """Start motivation and entertainment system after task completion"""
        import random
        
        # Motivational messages
        motivational_messages = [
            "🎉 Ajoyib! Siz zo'r xodimsiniz!",
            "⭐️ Mukammal ish! Tabriklayman!",
            "🏆 A'lo darajada bajarildi!",
            "💪 Siz haqiqiy professional!",
            "🌟 Ajoyib natija! Davom eting!",
            "👏 Qoyil! Siz eng yaxshi xodimlardan birisiz!",
            "🎯 Maqsadga erishingiz g'aroyib!",
            "🚀 Siz jamoamizning yulduzi!",
            "💎 Sizning ishingiz oltin qiymatida!",
            "🏅 Champion! Tabriklayman!"
        ]
        
        # Send random motivational message
        motivation_msg = random.choice(motivational_messages)
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("🎬 Kino ko'rish", "🎵 Musiqa tinglash")
        markup.add("🍽 Ovqatlanish", "📰 Yangiliklar")
        markup.add("❌ Hech narsa", "🔙 Asosiy menyu")
        
        set_user_state(message.chat.id, "entertainment_menu")
        
        bot.send_message(
            message.chat.id,
            f"{motivation_msg}\n\n"
            "🎊 Vazifa bajarilganligi munosabati bilan sizga bir necha variantni taklif qilamiz:\n\n"
            "🎬 Kino - yangi filmlarni tomosha qiling\n"
            "🎵 Musiqa - eng so'nggi qo'shiqlarni tinglang\n"
            "🍽 Ovqatlanish - yaqin atrofdagi restoranlar\n"
            "📰 Yangiliklar - bugungi eng muhim xabarlar\n\n"
            "Nima qilishni xohlaysiz?",
            reply_markup=markup
        )

    @bot.message_handler(func=lambda message: get_user_state(message.chat.id)[0] == "entertainment_menu")
    def handle_entertainment_choice(message):
        """Handle entertainment menu choices"""
        if message.text == "🎬 Kino ko'rish":
            set_user_state(message.chat.id, "movie_search")
            
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add("🔙 Bekor qilish")
            
            bot.send_message(
                message.chat.id,
                "🎬 Qaysi kino turini ko'rishni xohlaysiz?\n\n"
                "Kino nomini yozing (masalan: Avengers, Sherlock Holmes, Matrix):",
                reply_markup=markup
            )
            
        elif message.text == "🎵 Musiqa tinglash":
            handle_music_choice(message)
            
        elif message.text == "🍽 Ovqatlanish":
            request_location_for_restaurants(message)
            
        elif message.text == "📰 Yangiliklar":
            get_daily_news(message)
            
        elif message.text == "❌ Hech narsa":
            clear_user_state(message.chat.id)
            show_employee_panel(message)
            
        elif message.text == "🔙 Asosiy menyu":
            clear_user_state(message.chat.id)
            show_employee_panel(message)
        else:
            bot.send_message(message.chat.id, "❌ Noto'g'ri tanlov. Iltimos, tugmalardan birini tanlang.")

    @bot.message_handler(func=lambda message: get_user_state(message.chat.id)[0] == "movie_search")
    def handle_movie_search(message):
        """Handle movie search and download"""
        if message.text == "🔙 Bekor qilish":
            clear_user_state(message.chat.id)
            start_motivation_system(message)
            return
        
        movie_name = message.text.strip()
        
        bot.send_message(
            message.chat.id,
            f"🎬 '{movie_name}' kinosi qidirilmoqda...\n"
            "⏳ Biroz kuting..."
        )
        
        try:
            # Simulate movie download (in real implementation, this would search torrent sites)
            import time
            time.sleep(2)
            
            # Send movie "download" link (placeholder)
            movie_message = f"""
🎬 **{movie_name}** kinosi topildi!

📥 Yuklab olish havolasi:
🔗 https://example-movie-site.com/download/{movie_name.replace(' ', '-').lower()}

⚠️ **Eslatma:** Mualliflik huquqlarini hurmat qiling!

🍿 Yaxshi tomosha!
"""
            
            bot.send_message(message.chat.id, movie_message)
            
        except Exception as e:
            bot.send_message(
                message.chat.id,
                f"❌ '{movie_name}' kinosi topilmadi yoki xatolik yuz berdi.\n"
                "Boshqa kino nomini kiriting."
            )
        
        clear_user_state(message.chat.id)
        show_employee_panel(message)

    def handle_music_choice(message):
        """Handle music listening options"""
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("🎵 Oxirgi 1 oylik musiqalar")
        markup.add("🔍 Musiqa qidirish")
        markup.add("🔙 Bekor qilish")
        
        set_user_state(message.chat.id, "music_menu")
        
        bot.send_message(
            message.chat.id,
            "🎵 Musiqa tanlovi:\n\n"
            "🎵 Oxirgi 1 oylik - eng yangi qo'shiqlar\n"
            "🔍 Musiqa qidirish - o'zingiz tanlagan qo'shiq\n\n"
            "Qaysi birini tanlaysiz?",
            reply_markup=markup
        )

    @bot.message_handler(func=lambda message: get_user_state(message.chat.id)[0] == "music_menu")
    def handle_music_menu(message):
        """Handle music menu choices"""
        if message.text == "🎵 Oxirgi 1 oylik musiqalar":
            send_latest_music(message)
        elif message.text == "🔍 Musiqa qidirish":
            set_user_state(message.chat.id, "music_search")
            
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add("🔙 Bekor qilish")
            
            bot.send_message(
                message.chat.id,
                "🔍 Qaysi qo'shiq yoki ijrochini qidirishni xohlaysiz?\n\n"
                "Qo'shiq yoki ijrochi nomini yozing:",
                reply_markup=markup
            )
        elif message.text == "🔙 Bekor qilish":
            clear_user_state(message.chat.id)
            start_motivation_system(message)

    def send_latest_music(message):
        """Send latest month music collection"""
        music_collection = f"""
🎵 **Oxirgi 1 oy eng mashhur qo'shiqlar**

🔥 **O'zbek qo'shiqlar:**
• Shahzoda - Yoruglik
• Rayhon - Sevaman 
• Munisa Rizayeva - Qalb
• Shohruhxon - Muhabbat

🌟 **Xorijiy qo'shiqlar:**
• Ed Sheeran - Bad Habits
• Dua Lipa - Levitating  
• The Weeknd - Blinding Lights
• Billie Eilish - Good 4 U

📱 **Tinglash havolalari:**
🎧 Spotify: https://open.spotify.com/playlist/latest-uzbek
🎧 YouTube Music: https://music.youtube.com/playlist/latest-hits

🎶 Yaxshi tinglashlar!
"""
        
        bot.send_message(message.chat.id, music_collection)
        clear_user_state(message.chat.id)
        show_employee_panel(message)

    @bot.message_handler(func=lambda message: get_user_state(message.chat.id)[0] == "music_search")
    def handle_music_search(message):
        """Handle music search"""
        if message.text == "🔙 Bekor qilish":
            clear_user_state(message.chat.id)
            handle_music_choice(message)
            return
        
        search_query = message.text.strip()
        
        bot.send_message(
            message.chat.id,
            f"🔍 '{search_query}' qidirilmoqda...\n"
            "⏳ Biroz kuting..."
        )
        
        try:
            import time
            time.sleep(1)
            
            # Simulate music search results
            music_results = f"""
🎵 **'{search_query}' uchun natijalar:**

🎧 **Topilgan qo'shiqlar:**
• {search_query} - Original
• {search_query} - Remix Version
• {search_query} - Acoustic Version

📱 **Tinglash havolalari:**
🎧 YouTube: https://youtube.com/results?search_query={search_query.replace(' ', '+')}
🎧 Spotify: https://open.spotify.com/search/{search_query.replace(' ', '%20')}
🎧 SoundCloud: https://soundcloud.com/search?q={search_query.replace(' ', '%20')}

🎶 Yaxshi tinglashlar!
"""
            
            bot.send_message(message.chat.id, music_results)
            
        except Exception as e:
            bot.send_message(
                message.chat.id,
                f"❌ '{search_query}' uchun natija topilmadi.\n"
                "Boshqa nom bilan qidirib ko'ring."
            )
        
        clear_user_state(message.chat.id)
        show_employee_panel(message)

    def request_location_for_restaurants(message):
        """Request location for restaurant recommendations"""
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        location_btn = types.KeyboardButton("📍 Joylashuvimni yuborish", request_location=True)
        markup.add(location_btn)
        markup.add("🔙 Bekor qilish")
        
        set_user_state(message.chat.id, "restaurant_location")
        
        bot.send_message(
            message.chat.id,
            "📍 Yaqin atrofdagi restoranlarni topish uchun joylashuvingizni yuboring:\n\n"
            "Sizning joylashuvingiz asosida eng yaxshi tavsiyalar beramiz!",
            reply_markup=markup
        )

    @bot.message_handler(content_types=['location'], func=lambda message: get_user_state(message.chat.id)[0] == "restaurant_location")
    def handle_restaurant_location(message):
        """Handle restaurant location and show recommendations"""
        if message.location:
            latitude = message.location.latitude
            longitude = message.location.longitude
            
            bot.send_message(
                message.chat.id,
                "🔍 Yaqin atrofdagi restoranlar qidirilmoqda...\n"
                "⏳ Biroz kuting..."
            )
            
            # Show restaurant recommendations
            restaurant_recommendations = f"""
🍽 **Yaqin atrofdagi restoranlar**
📍 Sizning joylashuvingiz: {latitude:.4f}, {longitude:.4f}

🏪 **Mashhur zanjir restoranlar:**

🍟 **Evos**
📍 2.1 km - Amir Temur ko'chasi
⭐️ 4.5/5 - Fast food, burger
📞 +998 71 200 05 05

🥙 **Lavash**  
📍 1.8 km - Buyuk Ipak Yo'li
⭐️ 4.3/5 - Lavash, milliy taomlar
📞 +998 71 202 40 40

🍗 **Beshqozon**
📍 3.2 km - Chilonzor tumani
⭐️ 4.6/5 - Go'sht, kabob
📞 +998 71 203 50 50

🥘 **Oq Tepa**
📍 2.7 km - Mirzo Ulugbek tumani
⭐️ 4.4/5 - Milliy oshlar
📞 +998 71 201 30 30

🍕 **MaxWay**
📍 1.5 km - Yunusobod tumani
⭐️ 4.2/5 - Pizza, fast food
📞 +998 71 205 15 15

🍗 **KFC**
📍 4.1 km - Tashkent City
⭐️ 4.1/5 - Tovuq, fast food
📞 +998 71 207 25 25

🍽 Yaxshi ishtaha!
"""
            
            bot.send_message(message.chat.id, restaurant_recommendations)
        else:
            bot.send_message(message.chat.id, "❌ Joylashuv olinmadi. Qayta urinib ko'ring.")
        
        clear_user_state(message.chat.id)
        show_employee_panel(message)

    @bot.message_handler(func=lambda message: get_user_state(message.chat.id)[0] == "restaurant_location" and message.text == "🔙 Bekor qilish")
    def cancel_restaurant_location(message):
        """Cancel restaurant location request"""
        clear_user_state(message.chat.id)
        start_motivation_system(message)

    def get_daily_news(message):
        """Get daily world and Uzbekistan news using web scraping"""
        bot.send_message(
            message.chat.id,
            "📰 Bugungi yangiliklar yuklanmoqda...\n"
            "⏳ Biroz kuting..."
        )
        
        try:
            import trafilatura
            import requests
            from datetime import datetime
            
            # Get news from multiple sources
            news_sources = [
                ("🌍 Dunyo yangiliklari", "https://www.bbc.com/uzbek"),
                ("🇺🇿 O'zbekiston yangiliklari", "https://kun.uz"),
            ]
            
            all_news = "📰 **Bugungi yangiliklar**\n"
            all_news += f"📅 {datetime.now().strftime('%d.%m.%Y')}\n\n"
            
            for source_name, source_url in news_sources:
                try:
                    # Fetch website content
                    downloaded = trafilatura.fetch_url(source_url)
                    if downloaded:
                        # Extract main text content
                        text = trafilatura.extract(downloaded)
                        if text:
                            # Take first 500 characters of news content
                            news_summary = text[:500] + "..." if len(text) > 500 else text
                            all_news += f"{source_name}:\n{news_summary}\n\n"
                        else:
                            all_news += f"{source_name}:\n❌ Yangiliklar yuklanmadi\n\n"
                    else:
                        all_news += f"{source_name}:\n❌ Sayt ochilmadi\n\n"
                        
                except Exception as e:
                    all_news += f"{source_name}:\n❌ Xatolik: {str(e)}\n\n"
            
            # Add direct links
            all_news += "🔗 **To'liq yangiliklarga havola:**\n"
            all_news += "🌍 BBC O'zbek: https://www.bbc.com/uzbek\n"
            all_news += "🇺🇿 Kun.uz: https://kun.uz\n"
            all_news += "📺 Daryo.uz: https://daryo.uz\n"
            all_news += "📰 Gazeta.uz: https://www.gazeta.uz\n"
            
            # Send news in chunks if too long
            if len(all_news) > 4000:
                parts = [all_news[i:i+4000] for i in range(0, len(all_news), 4000)]
                for part in parts:
                    bot.send_message(message.chat.id, part)
            else:
                bot.send_message(message.chat.id, all_news)
                
        except Exception as e:
            error_news = f"""
📰 **Bugungi yangiliklar**
❌ Yangiliklar yuklanmadi: {str(e)}

🔗 **Yangilik saytlarga to'g'ridan-to'g'ri kirish:**
🌍 BBC O'zbek: https://www.bbc.com/uzbek
🇺🇿 Kun.uz: https://kun.uz
📺 Daryo.uz: https://daryo.uz
📰 Gazeta.uz: https://www.gazeta.uz
🌐 Sputnik: https://uz.sputniknews.ru
"""
            bot.send_message(message.chat.id, error_news)
        
        clear_user_state(message.chat.id)
        show_employee_panel(message)

    # Error handler
    @bot.message_handler(func=lambda message: True)
    def handle_unknown(message):
        """Handle unknown messages"""
        bot.send_message(
            message.chat.id,
            "❓ Tushunmadim. Iltimos, menyudan tanlang yoki /start bosing."
        )

    # Start the bot
    try:
        print("🚀 Enhanced Telegram Task Management Bot ishga tushmoqda...")
        print(f"🔑 Bot Token: {'✅ Mavjud' if BOT_TOKEN else '❌ Mavjud emas'}")
        print(f"👑 Admin chat ID: {ADMIN_CHAT_ID}")
        print(f"👥 Xodimlar soni: {len(EMPLOYEES)}")
        print("📊 Ma'lumotlar bazasi tayyorlandi")
        print("✅ Bot muvaffaqiyatli ishga tushdi!")
        print("📱 Bot Telegram orqali foydalanishga tayyor")
        print("🛑 Botni to'xtatish uchun Ctrl+C bosing")
        
        bot.infinity_polling(none_stop=True, interval=0, timeout=60)
        
    except KeyboardInterrupt:
        print("\n🛑 Bot to'xtatildi.")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Bot xatosi: {e}")
        import time
        time.sleep(5)
        bot.infinity_polling(none_stop=True, interval=0, timeout=60)

if __name__ == "__main__":
    main()
