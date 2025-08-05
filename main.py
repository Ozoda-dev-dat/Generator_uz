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
    add_message, get_user_state, set_user_state, clear_user_state,
    add_customer_inquiry, get_customer_inquiries, respond_to_inquiry, get_inquiry_by_id, get_task_by_id
)
from utils import (
    save_media_file, generate_employee_report, generate_admin_report,
    format_task_info, parse_json_data, serialize_json_data, ensure_directories
)
# Return to employee panel after task completion

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

    @bot.message_handler(commands=['contact', 'sorov', 'murojaat'])
    def customer_contact(message):
        """Handle customer contact requests"""
        # Skip if user is admin or employee
        if message.chat.id == ADMIN_CHAT_ID or message.chat.id in EMPLOYEES.values():
            bot.send_message(
                message.chat.id,
                "Admin va xodimlar uchun bu komanda mo'ljallangan emas. /start ni ishlating."
            )
            return
        
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

    @bot.message_handler(func=lambda message: get_user_state(message.chat.id)[0] == "customer_contact_start")
    def handle_customer_contact_start(message):
        """Handle customer contact start options"""
        if message.text == "📞 Telefon raqamni ulashish":
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            contact_button = types.KeyboardButton("📞 Telefon raqamni ulashish", request_contact=True)
            markup.add(contact_button)
            markup.add("🔙 Bekor qilish")
            
            set_user_state(message.chat.id, "waiting_for_contact")
            
            bot.send_message(
                message.chat.id,
                "📞 Telefon raqamingizni ulash uchun pastdagi tugmani bosing:",
                reply_markup=markup
            )
            
        elif message.text == "📍 Joylashuvni ulashish":
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            location_button = types.KeyboardButton("📍 Joylashuvni ulashish", request_location=True)
            markup.add(location_button)
            markup.add("🔙 Bekor qilish")
            
            set_user_state(message.chat.id, "waiting_for_location")
            
            bot.send_message(
                message.chat.id,
                "📍 Joylashuvingizni ulash uchun pastdagi tugmani bosing:",
                reply_markup=markup
            )
            
        elif message.text == "💬 So'rov yuborish":
            set_user_state(message.chat.id, "writing_inquiry")
            
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add("🔙 Bekor qilish")
            
            bot.send_message(
                message.chat.id,
                "💬 So'rovingizni yozing:\n\n"
                "Masalan:\n"
                "- Xizmat haqida ma'lumot olish\n"
                "- Narxlar haqida savol\n"
                "- Shikoyat yoki taklif\n"
                "- Boshqa savollar",
                reply_markup=markup
            )
            
        elif message.text == "🔙 Bekor qilish":
            clear_user_state(message.chat.id)
            bot.send_message(
                message.chat.id,
                "❌ Bekor qilindi. Yana kerak bo'lsa /contact yozing."
            )
            
            # Check if user is an employee and redirect to employee panel  
            employee_name = None
            for name, chat_id in EMPLOYEES.items():
                if chat_id == message.chat.id:
                    employee_name = name
                    break
            
            if employee_name:
                show_employee_panel(message, employee_name)

    @bot.message_handler(content_types=['contact'])
    def handle_customer_contact(message):
        """Handle customer contact sharing"""
        if get_user_state(message.chat.id)[0] != "waiting_for_contact":
            return
        
        # Store contact info
        customer_data = {
            'phone': message.contact.phone_number,
            'name': message.contact.first_name + (' ' + message.contact.last_name if message.contact.last_name else ''),
            'username': message.from_user.username
        }
        
        set_user_state(message.chat.id, "customer_contact_saved", json.dumps(customer_data))
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        location_button = types.KeyboardButton("📍 Joylashuvni ulashish", request_location=True)
        markup.add(location_button)
        markup.add("💬 So'rov yuborish", "🔙 Bekor qilish")
        
        bot.send_message(
            message.chat.id,
            f"✅ Telefon raqam saqlandi: {message.contact.phone_number}\n\n"
            "Endi joylashuvingizni ham ulashing (ixtiyoriy):",
            reply_markup=markup
        )

    @bot.message_handler(content_types=['location'])
    def handle_all_location(message):
        """Handle all location sharing - customer, admin task assignment, employee"""
        state, data = get_user_state(message.chat.id)
        
        # Handle admin task assignment location
        if state == "assign_task_location":
            admin_data[message.chat.id]["location"] = {
                "latitude": message.location.latitude,
                "longitude": message.location.longitude
            }
            
            # Show animated location card for task assignment
            send_animated_location_card(
                message.chat.id,
                "Admin (Vazifa)",
                message.location.latitude,
                message.location.longitude,
                "task_location"
            )
            
            set_user_state(message.chat.id, "assign_task_payment")
            
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add("💰 To'lov miqdorini kiriting")
            markup.add("⏭ To'lov belgilanmagan")
            markup.add("🔙 Bekor qilish")
            
            bot.send_message(
                message.chat.id,
                "✅ Vazifa lokatsiyasi belgilandi!\n\n💰 To'lov miqdorini tanlang:",
                reply_markup=markup
            )
            print(f"DEBUG: Payment buttons sent to {message.chat.id}")
            return
        
        # Handle customer location sharing
        if state in ["waiting_for_location", "customer_contact_saved"]:
            handle_customer_location_data(message, state, data)
            return
        
        # Handle employee location sharing
        if state == "employee_location":
            handle_employee_location_data(message)
            return
    
    def handle_customer_location_data(message, state, data):
        """Handle customer location sharing"""
        
        # Get existing customer data or create new
        if data:
            customer_data = json.loads(data)
        else:
            customer_data = {
                'name': message.from_user.first_name + (' ' + message.from_user.last_name if message.from_user.last_name else ''),
                'username': message.from_user.username
            }
        
        # Add location data
        customer_data['location_lat'] = message.location.latitude
        customer_data['location_lon'] = message.location.longitude
        
        # Show animated location card for customer
        send_animated_location_card(
            message.chat.id,
            customer_data.get('name', 'Mijoz'),
            message.location.latitude,
            message.location.longitude,
            "customer_location"
        )
        
        set_user_state(message.chat.id, "customer_location_saved", json.dumps(customer_data))
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("💬 So'rov yuborish")
        if 'phone' not in customer_data:
            contact_button = types.KeyboardButton("📞 Telefon raqamni ulashish", request_contact=True)
            markup.add(contact_button)
        markup.add("🔙 Bekor qilish")
        
        bot.send_message(
            message.chat.id,
            "✅ Joylashuv saqlandi!\n\n"
            "Endi so'rovingizni yozing:",
            reply_markup=markup
        )
    
    def handle_employee_location_data(message):
        """Handle employee location sharing during task completion"""
        # Use the main location sharing handler which includes employee panel redirect
        handle_location_sharing(message)

    @bot.message_handler(func=lambda message: get_user_state(message.chat.id)[0] in ["writing_inquiry", "customer_contact_saved", "customer_location_saved"])
    def handle_customer_inquiry(message):
        """Handle customer inquiry text"""
        if message.text == "🔙 Bekor qilish":
            clear_user_state(message.chat.id)
            bot.send_message(
                message.chat.id,
                "❌ Bekor qilindi. Yana kerak bo'lsa /contact yozing."
            )
            
            # Check if user is an employee and redirect to employee panel
            employee_name = None
            for name, chat_id in EMPLOYEES.items():
                if chat_id == message.chat.id:
                    employee_name = name
                    break
            
            if employee_name:
                show_employee_panel(message, employee_name)
            return
        
        if message.text in ["📞 Telefon raqamni ulashish", "📍 Joylashuvni ulashish"]:
            # Handle these separately
            handle_customer_contact_start(message)
            return
        
        if message.text == "💬 So'rov yuborish":
            set_user_state(message.chat.id, "writing_inquiry_final")
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add("🔙 Bekor qilish")
            
            bot.send_message(
                message.chat.id,
                "💬 So'rovingizni batafsil yozing:",
                reply_markup=markup
            )
            return
        
        # This is the inquiry text
        state, data = get_user_state(message.chat.id)
        
        # Get customer data
        if data:
            customer_data = json.loads(data)
        else:
            customer_data = {
                'name': message.from_user.first_name + (' ' + message.from_user.last_name if message.from_user.last_name else ''),
                'username': message.from_user.username
            }
        
        try:
            # Save inquiry to database
            inquiry_id = add_customer_inquiry(
                customer_name=customer_data.get('name', 'Mijoz'),
                customer_phone=customer_data.get('phone', ''),
                customer_username=customer_data.get('username', ''),
                chat_id=message.chat.id,
                inquiry_text=message.text,
                location_lat=customer_data.get('location_lat', 0.0),
                location_lon=customer_data.get('location_lon', 0.0),
                inquiry_type='customer_request',
                source='telegram'
            )
            
            # Send confirmation to customer
            bot.send_message(
                message.chat.id,
                f"✅ **So'rovingiz qabul qilindi!**\n\n"
                f"📋 So'rov raqami: #{inquiry_id}\n"
                f"👤 Ism: {customer_data.get('name', 'Mijoz')}\n"
                f"📞 Telefon: {customer_data.get('phone', 'Kiritilmagan')}\n"
                f"💬 So'rov: {message.text}\n\n"
                f"🕐 Tez orada javob beramiz!\n"
                f"📞 Shoshilinch hollar uchun: +998 xx xxx xx xx"
            )
            
            # Notify admin
            if ADMIN_CHAT_ID:
                admin_message = f"""
🔔 **YANGI MIJOZ SO'ROVI**

📋 So'rov ID: #{inquiry_id}
👤 Mijoz: {customer_data.get('name', 'Mijoz')}
📞 Telefon: {customer_data.get('phone', 'Kiritilmagan')}
👤 Username: @{customer_data.get('username', 'mavjud emas')}
📱 Chat ID: {message.chat.id}

💬 **So'rov:**
{message.text}

📅 Vaqt: {datetime.now().strftime('%Y-%m-%d %H:%M')}

💡 Javob berish: 👥 Mijozlar so'rovlari → 🤖 Botdan kelgan so'rovlar
"""
                
                try:
                    bot.send_message(ADMIN_CHAT_ID, admin_message)
                    
                    # Send location if available
                    if customer_data.get('location_lat') and customer_data.get('location_lon'):
                        bot.send_location(
                            ADMIN_CHAT_ID, 
                            customer_data['location_lat'], 
                            customer_data['location_lon']
                        )
                        bot.send_message(
                            ADMIN_CHAT_ID,
                            f"📍 Mijoz joylashuvi (So'rov #{inquiry_id})"
                        )
                except Exception as admin_error:
                    print(f"Admin notification error: {admin_error}")
            
        except Exception as e:
            bot.send_message(
                message.chat.id,
                f"❌ So'rovni saqlashda xatolik yuz berdi. Iltimos, qayta urinib ko'ring.\n"
                f"Xatolik: {str(e)}"
            )
        
        clear_user_state(message.chat.id)
        
        # Check if user is an employee and redirect to employee panel
        employee_name = None
        for name, chat_id in EMPLOYEES.items():
            if chat_id == message.chat.id:
                employee_name = name
                break
        
        if employee_name:
            # User is an employee, show employee panel
            show_employee_panel(message, employee_name)
        else:
            # User is a customer, show start menu
            start_message(message)

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
        print(f"DEBUG: Admin panel ko'rsatilmoqda. Chat ID: {message.chat.id}")
        
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
        print(f"DEBUG: Admin paneli yuborildi")

    @bot.message_handler(func=lambda message: message.text == "📤 Vazifa berish")
    def start_task_assignment(message):
        """Start task assignment process"""
        print(f"DEBUG: Vazifa berish tugmasi bosildi. Chat ID: {message.chat.id}")
        
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
        print(f"DEBUG: Admin'ga vazifa tavsifi so'raldi")

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
        markup.add("🌐 Website dan kelgan so'rovlar", "🤖 Botdan kelgan so'rovlar")
        markup.add("📋 Barcha so'rovlar", "📊 So'rovlar statistikasi")
        markup.add("🔙 Ortga")
        
        # Get inquiry counts
        try:
            website_inquiries = len(get_customer_inquiries(source='website'))
            bot_inquiries = len(get_customer_inquiries(source='telegram'))
            pending_inquiries = len(get_customer_inquiries(status='pending'))
        except:
            website_inquiries = bot_inquiries = pending_inquiries = 0
        
        bot.send_message(
            message.chat.id,
            f"👥 **Mijozlar so'rovlari bo'limi**\n\n"
            f"🌐 Website so'rovlari: {website_inquiries} ta\n"
            f"🤖 Bot so'rovlari: {bot_inquiries} ta\n"
            f"⏳ Javob kutayotgan: {pending_inquiries} ta\n\n"
            f"Kerakli bo'limni tanlang:",
            reply_markup=markup
        )

    @bot.message_handler(func=lambda message: message.text == "🌐 Website dan kelgan so'rovlar")
    def show_website_inquiries(message):
        """Show website inquiries"""
        if message.chat.id != ADMIN_CHAT_ID:
            return
        
        try:
            inquiries = get_customer_inquiries(source='website')
            
            if not inquiries:
                bot.send_message(
                    message.chat.id,
                    "🌐 **Website so'rovlari**\n\n"
                    "Hozircha website dan so'rov kelmagan.\n\n"
                    "Website integrasiyasi orqali mijozlar so'rovlari bu yerda ko'rinadi."
                )
                return
            
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            response_text = "🌐 **Website dan kelgan so'rovlar:**\n\n"
            
            for inquiry in inquiries[:10]:  # Show first 10
                inquiry_id, customer_name, customer_phone, customer_username, chat_id, inquiry_text, inquiry_type, location_lat, location_lon, location_address, status, admin_response, created_at, responded_at, source = inquiry
                
                status_emoji = "⏳" if status == "pending" else "✅"
                response_text += f"{status_emoji} **ID{inquiry_id}** - {customer_name}\n"
                response_text += f"📧 {inquiry_text[:50]}{'...' if len(inquiry_text) > 50 else ''}\n"
                response_text += f"📅 {created_at}\n\n"
                
                markup.add(f"📋 ID{inquiry_id} - Ko'rish va javob berish")
            
            markup.add("🔄 Yangilash", "🔙 Ortga")
            
            bot.send_message(message.chat.id, response_text, reply_markup=markup)
            
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Xatolik: {str(e)}")

    @bot.message_handler(func=lambda message: message.text == "🤖 Botdan kelgan so'rovlar")
    def show_bot_inquiries(message):
        """Show bot inquiries"""
        if message.chat.id != ADMIN_CHAT_ID:
            return
        
        try:
            inquiries = get_customer_inquiries(source='telegram')
            
            if not inquiries:
                bot.send_message(
                    message.chat.id,
                    "🤖 **Bot so'rovlari**\n\n"
                    "Hozircha bot orqali so'rov kelmagan.\n\n"
                    "Mijozlar botga yozganda ularning so'rovlari bu yerda ko'rinadi."
                )
                return
            
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            response_text = "🤖 **Botdan kelgan so'rovlar:**\n\n"
            
            for inquiry in inquiries[:10]:  # Show first 10
                inquiry_id, customer_name, customer_phone, customer_username, chat_id, inquiry_text, inquiry_type, location_lat, location_lon, location_address, status, admin_response, created_at, responded_at, source = inquiry
                
                status_emoji = "⏳" if status == "pending" else "✅"
                response_text += f"{status_emoji} **ID{inquiry_id}** - {customer_name}\n"
                if customer_username:
                    response_text += f"👤 @{customer_username}\n"
                response_text += f"📧 {inquiry_text[:50]}{'...' if len(inquiry_text) > 50 else ''}\n"
                response_text += f"📅 {created_at}\n\n"
                
                markup.add(f"📋 ID{inquiry_id} - Ko'rish va javob berish")
            
            markup.add("🔄 Yangilash", "🔙 Ortga")
            
            bot.send_message(message.chat.id, response_text, reply_markup=markup)
            
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Xatolik: {str(e)}")

    @bot.message_handler(func=lambda message: message.text == "📋 Barcha so'rovlar")
    def show_all_inquiries(message):
        """Show all inquiries"""
        if message.chat.id != ADMIN_CHAT_ID:
            return
        
        try:
            inquiries = get_customer_inquiries()
            
            if not inquiries:
                bot.send_message(
                    message.chat.id,
                    "📋 **Barcha so'rovlar**\n\n"
                    "Hozircha hech qanday so'rov yo'q."
                )
                return
            
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            response_text = "📋 **Barcha mijoz so'rovlari:**\n\n"
            
            for inquiry in inquiries[:15]:  # Show first 15
                inquiry_id, customer_name, customer_phone, customer_username, chat_id, inquiry_text, inquiry_type, location_lat, location_lon, location_address, status, admin_response, created_at, responded_at, source = inquiry
                
                status_emoji = "⏳" if status == "pending" else "✅"
                source_emoji = "🌐" if source == "website" else "🤖"
                
                response_text += f"{status_emoji}{source_emoji} **ID{inquiry_id}** - {customer_name}\n"
                response_text += f"📧 {inquiry_text[:40]}{'...' if len(inquiry_text) > 40 else ''}\n"
                response_text += f"📅 {created_at}\n\n"
                
                markup.add(f"📋 ID{inquiry_id} - Ko'rish")
            
            markup.add("🔄 Yangilash", "🔙 Ortga")
            
            bot.send_message(message.chat.id, response_text, reply_markup=markup)
            
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Xatolik: {str(e)}")

    @bot.message_handler(func=lambda message: "ID" in message.text and "Ko'rish" in message.text)
    def view_inquiry_details(message):
        """View inquiry details and respond"""
        if message.chat.id != ADMIN_CHAT_ID:
            return
        
        try:
            # Extract inquiry ID
            inquiry_id = int(message.text.split("ID")[1].split(" ")[0])
            inquiry = get_inquiry_by_id(inquiry_id)
            
            if not inquiry:
                bot.send_message(message.chat.id, "❌ So'rov topilmadi.")
                return
            
            inquiry_id, customer_name, customer_phone, customer_username, chat_id, inquiry_text, inquiry_type, location_lat, location_lon, location_address, status, admin_response, created_at, responded_at, source = inquiry
            
            # Format inquiry details
            source_name = "Website" if source == "website" else "Telegram Bot"
            status_name = "Javob berilgan" if status == "responded" else "Javob kutmoqda"
            
            details_text = f"""
🔍 **So'rov tafsilotlari**

🆔 ID: {inquiry_id}
👤 Mijoz: {customer_name}
📞 Telefon: {customer_phone or 'Kiritilmagan'}
👤 Username: @{customer_username or 'Mavjud emas'}
📱 Chat ID: {chat_id or 'Mavjud emas'}
🌐 Manba: {source_name}
📋 Status: {status_name}
📅 Kelgan vaqt: {created_at}

📝 **So'rov matni:**
{inquiry_text}
"""
            
            if location_lat and location_lon:
                details_text += f"\n📍 **Joylashuv:** {location_address or 'Mavjud'}"
            
            if admin_response:
                details_text += f"\n\n✅ **Admin javobi:**\n{admin_response}\n📅 Javob vaqti: {responded_at}"
            
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            
            if status == "pending":
                markup.add(f"💬 ID{inquiry_id}ga javob berish")
            
            if source == "telegram" and chat_id:
                markup.add(f"📞 ID{inquiry_id}ga bevosita xabar yuborish")
            
            markup.add("🔙 Ortga")
            
            # Store inquiry ID for response
            set_user_state(message.chat.id, "viewing_inquiry", str(inquiry_id))
            
            bot.send_message(message.chat.id, details_text, reply_markup=markup)
            
            # Show location if available
            if location_lat and location_lon:
                bot.send_location(message.chat.id, location_lat, location_lon)
            
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Xatolik: {str(e)}")

    @bot.message_handler(func=lambda message: "javob berish" in message.text and "ID" in message.text)
    def start_inquiry_response(message):
        """Start responding to inquiry"""
        if message.chat.id != ADMIN_CHAT_ID:
            return
        
        try:
            # Extract inquiry ID
            inquiry_id = int(message.text.split("ID")[1].split("ga")[0])
            
            set_user_state(message.chat.id, "responding_to_inquiry", str(inquiry_id))
            
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add("🔙 Bekor qilish")
            
            bot.send_message(
                message.chat.id, 
                f"💬 **ID{inquiry_id} so'roviga javob**\n\n"
                "Mijozga jo'natmoqchi bo'lgan javobingizni yozing:",
                reply_markup=markup
            )
            
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Xatolik: {str(e)}")

    @bot.message_handler(func=lambda message: get_user_state(message.chat.id)[0] == "responding_to_inquiry")
    def send_inquiry_response(message):
        """Send response to inquiry"""
        if message.text == "🔙 Bekor qilish":
            clear_user_state(message.chat.id)
            show_customer_requests(message)
            return
        
        try:
            state, inquiry_id = get_user_state(message.chat.id)
            inquiry_id = int(inquiry_id)
            
            # Save response to database
            inquiry_details = respond_to_inquiry(inquiry_id, message.text)
            
            if inquiry_details:
                customer_name, chat_id, inquiry_text, customer_phone, source = inquiry_details
                
                # Send notification to customer if from Telegram
                if source == "telegram" and chat_id:
                    try:
                        response_message = f"""
👋 Assalomu alaykum {customer_name}!

💬 **So'rovingizga javob:**
{message.text}

📋 **Sizning so'rovingiz:**
{inquiry_text[:100]}{'...' if len(inquiry_text) > 100 else ''}

🤝 Boshqa savollaringiz bo'lsa, bemalol yozing!
"""
                        bot.send_message(chat_id, response_message)
                        notification = "✅ Mijozga Telegram orqali javob yuborildi!"
                    except:
                        notification = "⚠️ Javob saqlandi, lekin mijozga yuborib bo'lmadi."
                else:
                    notification = f"✅ Javob saqlandi! ({source} so'rovi)"
                
                bot.send_message(
                    message.chat.id,
                    f"✅ **Javob muvaffaqiyatli yuborildi!**\n\n"
                    f"📋 So'rov ID: {inquiry_id}\n"
                    f"👤 Mijoz: {customer_name}\n"
                    f"💬 Javob: {message.text}\n\n"
                    f"{notification}"
                )
            else:
                bot.send_message(message.chat.id, "❌ So'rov topilmadi.")
            
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Xatolik: {str(e)}")
        
        clear_user_state(message.chat.id)
        show_customer_requests(message)
    
    @bot.message_handler(func=lambda message: message.text == "🔄 Yangilash")
    def refresh_current_menu(message):
        """Refresh current menu based on context"""
        if message.chat.id != ADMIN_CHAT_ID:
            return
        
        try:
            # Determine which menu to refresh based on recent messages
            bot.send_message(message.chat.id, "🔄 Yangilanmoqda...")
            
            # Always refresh the main customer requests menu
            show_customer_requests(message)
            
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Yangilashda xatolik: {str(e)}")
            show_customer_requests(message)

    @bot.message_handler(func=lambda message: message.text == "🔄 Website yangilash")
    def refresh_website_inquiries(message):
        """Refresh website inquiries specifically"""
        if message.chat.id != ADMIN_CHAT_ID:
            return
        
        try:
            bot.send_message(message.chat.id, "🔄 Website so'rovlari yangilanmoqda...")
            show_website_inquiries(message)
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Xatolik: {str(e)}")

    @bot.message_handler(func=lambda message: message.text == "🔄 Bot yangilash")
    def refresh_bot_inquiries(message):
        """Refresh bot inquiries specifically"""
        if message.chat.id != ADMIN_CHAT_ID:
            return
        
        try:
            bot.send_message(message.chat.id, "🔄 Bot so'rovlari yangilanmoqda...")
            show_bot_inquiries(message)
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Xatolik: {str(e)}")

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

    def send_animated_location_card(chat_id, sender_name, latitude, longitude, location_type="general"):
        """Send animated location sharing card with interactive Google Maps preview"""
        import time
        
        # Create different card styles based on location type
        if location_type == "employee_location":
            card_title = "👤 Xodim Lokatsiyasi"
            card_icon = "📍"
            card_color = "🟢"
        elif location_type == "task_location":
            card_title = "🎯 Vazifa Lokatsiyasi"
            card_icon = "🚩"
            card_color = "🔵"
        elif location_type == "customer_location":
            card_title = "👥 Mijoz Lokatsiyasi"
            card_icon = "📌"
            card_color = "🟡"
        else:
            card_title = "📍 Lokatsiya Ma'lumoti"
            card_icon = "📍"
            card_color = "⚪"
        
        # Generate interactive map URLs
        google_maps_url = f"https://maps.google.com/?q={latitude},{longitude}"
        google_maps_embed = f"https://maps.google.com/maps?q={latitude},{longitude}&output=embed"
        yandex_maps_url = f"https://yandex.ru/maps/?ll={longitude},{latitude}&z=16&l=map"
        
        # Send animated loading message first
        loading_msg = bot.send_message(
            chat_id,
            f"🔄 Lokatsiya kartasi tayyorlanmoqda...\n⏳ Biroz kuting..."
        )
        
        time.sleep(1)  # Animation delay
        
        # Delete loading message and send main card
        try:
            bot.delete_message(chat_id, loading_msg.message_id)
        except:
            pass
        
        # Create animated location card with rich formatting
        current_time = datetime.now().strftime('%d.%m.%Y %H:%M:%S')
        
        location_card = f"""
{card_color} **{card_title}** {card_color}
╭─────────────────────────╮
│  {card_icon} **{sender_name}**
│  🌍 Joylashuv ma'lumotlari
╰─────────────────────────╯

📊 **Koordinatalar:**
• 🌐 Kenglik: `{latitude:.6f}`
• 🌐 Uzunlik: `{longitude:.6f}`

🗺 **Interaktiv Xaritalar:**
• [📍 Google Maps]({google_maps_url})
• [🗺 Yandex Maps]({yandex_maps_url})

⏰ **Vaqt:** {current_time}
📡 **Status:** ✅ Faol

┌─────────────────────────┐
│   🎯 Tezkor Amallar:    │
├─────────────────────────┤
│ 🧭 Navigatsiya          │
│ 📏 Masofa hisoblash     │
│ 📱 Telefondan ochish    │
└─────────────────────────┘
"""
        
        # Send the main location card
        bot.send_message(
            chat_id,
            location_card,
            parse_mode='Markdown',
            disable_web_page_preview=False
        )
        
        # Send actual location pin for precise mapping
        bot.send_location(
            chat_id,
            latitude,
            longitude
        )
        
        # Send interactive inline keyboard for additional actions
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            types.InlineKeyboardButton("🧭 Navigatsiya", url=google_maps_url),
            types.InlineKeyboardButton("📱 Telefondan ochish", url=f"geo:{latitude},{longitude}")
        )
        keyboard.add(
            types.InlineKeyboardButton("📏 Masofa hisoblash", callback_data=f"calc_distance_{latitude}_{longitude}"),
            types.InlineKeyboardButton("🔄 Yangilash", callback_data=f"refresh_location_{latitude}_{longitude}")
        )
        keyboard.add(
            types.InlineKeyboardButton("📊 Atrofdagi joylar", callback_data=f"nearby_places_{latitude}_{longitude}")
        )
        
        bot.send_message(
            chat_id,
            f"🎮 **Interaktiv Amallar** - {sender_name}\n\n"
            f"Quyidagi tugmalar orqali lokatsiya bilan ishlashingiz mumkin:",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

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
                
                # Confirm to employee and show main menu
                bot.send_message(
                    message.chat.id,
                    "✅ Lokatsiya qabul qilindi. Rahmat!"
                )
                
                # Show employee panel after location sharing
                show_employee_panel(message, employee_name)
                
                # Send animated location sharing card with interactive map preview
                send_animated_location_card(
                    ADMIN_CHAT_ID, 
                    employee_name, 
                    message.location.latitude, 
                    message.location.longitude,
                    "employee_location"
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

    @bot.message_handler(func=lambda message: message.text == "🔙 Ortga" and message.chat.id in EMPLOYEES.values())
    def employee_back_handler(message):
        """Handle back button for employees"""
        # Clear any active state
        clear_user_state(message.chat.id)
        
        # Check if user is an employee 
        employee_name = None
        for name, chat_id in EMPLOYEES.items():
            if chat_id == message.chat.id:
                employee_name = name
                break
        
        if employee_name:
            # Send them back to employee panel
            show_employee_panel(message)
        else:
            bot.send_message(message.chat.id, "❌ Tushunmadim. Iltimos, menyudan tanlang yoki /start bosing.")

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
        markup.add("📊 Hisobotlar")
        markup.add("🔙 Ortga")
        
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

    @bot.message_handler(func=lambda message: message.text == "📂 Vazifalar tarixi")
    def show_employee_task_history(message):
        """Show employee's task history with interactive options"""
        employee_name = None
        for name, chat_id in EMPLOYEES.items():
            if chat_id == message.chat.id:
                employee_name = name
                break
        
        if not employee_name:
            bot.send_message(message.chat.id, "❌ Profil topilmadi.")
            return
        
        # Show options for history view
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📊 Umumiy tarix", "📅 So'nggi 7 kun")
        markup.add("📆 So'nggi 30 kun", "💰 Faqat to'lovli vazifalar")
        markup.add("🔙 Ortga")
        
        set_user_state(message.chat.id, "task_history_menu")
        
        bot.send_message(
            message.chat.id,
            f"📂 **{employee_name}** - Vazifalar tarixi\n\n"
            "Qaysi ko'rinishni tanlaysiz?",
            reply_markup=markup
        )

    @bot.message_handler(func=lambda message: get_user_state(message.chat.id)[0] == "task_history_menu")
    def handle_task_history_menu(message):
        """Handle task history menu selections"""
        if message.text == "🔙 Ortga":
            clear_user_state(message.chat.id)
            show_employee_panel(message)
            return
        
        employee_name = None
        for name, chat_id in EMPLOYEES.items():
            if chat_id == message.chat.id:
                employee_name = name
                break
        
        if not employee_name:
            bot.send_message(message.chat.id, "❌ Profil topilmadi.")
            return
        
        if message.text == "📊 Umumiy tarix":
            show_complete_task_history(message, employee_name, "all")
        elif message.text == "📅 So'nggi 7 kun":
            show_complete_task_history(message, employee_name, "week")
        elif message.text == "📆 So'nggi 30 kun":
            show_complete_task_history(message, employee_name, "month")
        elif message.text == "💰 Faqat to'lovli vazifalar":
            show_complete_task_history(message, employee_name, "paid")
        else:
            bot.send_message(message.chat.id, "❌ Noto'g'ri tanlov.")

    def show_complete_task_history(message, employee_name, period_type):
        """Show detailed task history based on period"""
        
        try:
            from database import DATABASE_PATH
            import sqlite3
            from datetime import datetime, timedelta
            
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()
            
            # Build query based on period type
            base_query = """
                SELECT id, title, description, status, created_at, completion_report, 
                       received_amount, completion_media
                FROM tasks 
                WHERE assigned_to = ? AND status = 'completed'
            """
            
            params = [employee_name]
            
            if period_type == "week":
                week_ago = (datetime.now() - timedelta(days=7)).isoformat()
                base_query += " AND created_at >= ?"
                params.append(week_ago)
                limit = 50
            elif period_type == "month":
                month_ago = (datetime.now() - timedelta(days=30)).isoformat()
                base_query += " AND created_at >= ?"
                params.append(month_ago)
                limit = 100
            elif period_type == "paid":
                base_query += " AND received_amount > 0"
                limit = 50
            else:  # all
                limit = 30
            
            base_query += f" ORDER BY created_at DESC LIMIT {limit}"
            
            cursor.execute(base_query, params)
            
            completed_tasks = cursor.fetchall()
            conn.close()
            
            if not completed_tasks:
                period_text = {
                    "week": "so'nggi 7 kun",
                    "month": "so'nggi 30 kun", 
                    "paid": "to'lovli",
                    "all": "barcha"
                }.get(period_type, "")
                
                bot.send_message(message.chat.id, f"📭 {period_text} davrdagi bajarilgan vazifalar topilmadi.")
                clear_user_state(message.chat.id)
                show_employee_panel(message)
                return
            
            # Period title
            period_titles = {
                "week": "So'nggi 7 kun",
                "month": "So'nggi 30 kun",
                "paid": "To'lovli vazifalar",
                "all": "Barcha vazifalar"
            }
            
            period_title = period_titles.get(period_type, "Vazifalar tarixi")
            history_text = f"📂 **{employee_name}** - {period_title}\n\n"
            total_earned = 0
            total_tasks = len(completed_tasks)
            
            for i, task in enumerate(completed_tasks, 1):
                task_id, title, description, status, created_at, completion_report, received_amount, completion_media = task
                
                try:
                    date_str = datetime.fromisoformat(created_at).strftime("%d.%m.%Y %H:%M")
                except:
                    date_str = created_at[:16] if created_at else "Noma'lum"
                
                amount_text = f"{received_amount:,.0f} so'm" if received_amount else "To'lov belgilanmagan"
                if received_amount:
                    total_earned += received_amount
                
                history_text += f"{i}. 📋 **{title}**\n"
                history_text += f"   📅 {date_str}\n"
                history_text += f"   💰 {amount_text}\n"
                if completion_report:
                    report_preview = completion_report[:50] + "..." if len(completion_report) > 50 else completion_report
                    history_text += f"   📝 {report_preview}\n"
                history_text += "\n"
            
            # Summary statistics
            avg_earning = total_earned / total_tasks if total_tasks > 0 else 0
            
            history_text += f"📊 **Statistika:**\n"
            history_text += f"🔢 Jami vazifalar: {total_tasks} ta\n"
            history_text += f"💰 Jami daromad: {total_earned:,.0f} so'm\n"
            history_text += f"📈 O'rtacha to'lov: {avg_earning:,.0f} so'm\n\n"
            
            # Performance indicators
            if total_earned > 0:
                if avg_earning >= 100000:
                    history_text += "🏆 A'lo natija! Yuqori to'lovli vazifalar!\n"
                elif avg_earning >= 50000:
                    history_text += "⭐️ Yaxshi natija! Davom eting!\n"
                else:
                    history_text += "💪 Yaxshi ish! Yanada yuqoriga!\n"
            
            # Send in chunks if too long
            if len(history_text) > 4000:
                parts = [history_text[i:i+4000] for i in range(0, len(history_text), 4000)]
                for part in parts:
                    bot.send_message(message.chat.id, part)
            else:
                bot.send_message(message.chat.id, history_text)
            
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Vazifalar tarixi yuklanmadi: {str(e)}")
        
        clear_user_state(message.chat.id)
        show_employee_panel(message)







    @bot.message_handler(func=lambda message: message.text == "📊 Hisobotlar")
    def show_employee_reports_menu(message):
        """Show employee reports menu"""
        employee_name = None
        for name, chat_id in EMPLOYEES.items():
            if chat_id == message.chat.id:
                employee_name = name
                break
        
        if not employee_name:
            bot.send_message(message.chat.id, "❌ Profil topilmadi.")
            return
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📅 Haftalik hisobot", "📆 Oylik hisobot")
        markup.add("📈 Umumiy statistika", "📤 Excel hisobot")
        markup.add("🔙 Ortga")
        
        bot.send_message(
            message.chat.id,
            f"📊 **{employee_name}** - Hisobotlar bo'limi\n\n"
            "Kerakli hisobot turini tanlang:",
            reply_markup=markup
        )

    @bot.message_handler(func=lambda message: message.text == "📅 Haftalik hisobot")
    def show_weekly_report(message):
        """Show weekly report for employee"""
        employee_name = None
        for name, chat_id in EMPLOYEES.items():
            if chat_id == message.chat.id:
                employee_name = name
                break
        
        if not employee_name:
            bot.send_message(message.chat.id, "❌ Profil topilmadi.")
            return
        
        try:
            from database import DATABASE_PATH
            import sqlite3
            from datetime import datetime, timedelta
            
            # Calculate date range (last 7 days)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()
            
            # Get completed tasks in last 7 days
            cursor.execute("""
                SELECT id, title, created_at, received_amount
                FROM tasks 
                WHERE assigned_to = ? AND status = 'completed'
                AND datetime(created_at) >= datetime(?)
                ORDER BY created_at DESC
            """, (employee_name, start_date.isoformat()))
            
            weekly_tasks = cursor.fetchall()
            conn.close()
            
            if not weekly_tasks:
                bot.send_message(
                    message.chat.id, 
                    f"📅 **Haftalik hisobot**\n\n"
                    f"👤 Xodim: {employee_name}\n"
                    f"📅 Davr: {start_date.strftime('%d.%m')} - {end_date.strftime('%d.%m.%Y')}\n\n"
                    f"📭 Oxirgi 7 kunda bajarilgan vazifalar yo'q."
                )
                return
            
            total_earned = sum(task[3] for task in weekly_tasks if task[3])
            
            report_text = f"📅 **Haftalik hisobot**\n\n"
            report_text += f"👤 Xodim: {employee_name}\n"
            report_text += f"📅 Davr: {start_date.strftime('%d.%m')} - {end_date.strftime('%d.%m.%Y')}\n\n"
            report_text += f"✅ Bajarilgan vazifalar: {len(weekly_tasks)} ta\n"
            report_text += f"💰 Jami ishlab topilgan: {total_earned:,.0f} so'm\n\n"
            
            if len(weekly_tasks) <= 10:
                report_text += "📋 **Vazifalar ro'yxati:**\n\n"
                for i, task in enumerate(weekly_tasks, 1):
                    task_id, title, created_at, amount = task
                    try:
                        date_str = datetime.fromisoformat(created_at).strftime("%d.%m %H:%M")
                    except:
                        date_str = created_at[:10] if created_at else "Noma'lum"
                    
                    amount_text = f"{amount:,.0f} so'm" if amount else "To'lov yo'q"
                    report_text += f"{i}. {title}\n"
                    report_text += f"   📅 {date_str} | 💰 {amount_text}\n\n"
            
            bot.send_message(message.chat.id, report_text)
            
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Haftalik hisobot yuklanmadi: {str(e)}")

    @bot.message_handler(func=lambda message: message.text == "📆 Oylik hisobot")
    def show_monthly_report(message):
        """Show monthly report for employee"""
        employee_name = None
        for name, chat_id in EMPLOYEES.items():
            if chat_id == message.chat.id:
                employee_name = name
                break
        
        if not employee_name:
            bot.send_message(message.chat.id, "❌ Profil topilmadi.")
            return
        
        try:
            from database import DATABASE_PATH
            import sqlite3
            from datetime import datetime, timedelta
            
            # Calculate date range (last 30 days)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()
            
            # Get completed tasks in last 30 days
            cursor.execute("""
                SELECT id, title, created_at, received_amount
                FROM tasks 
                WHERE assigned_to = ? AND status = 'completed'
                AND datetime(created_at) >= datetime(?)
                ORDER BY created_at DESC
            """, (employee_name, start_date.isoformat()))
            
            monthly_tasks = cursor.fetchall()
            conn.close()
            
            if not monthly_tasks:
                bot.send_message(
                    message.chat.id, 
                    f"📆 **Oylik hisobot**\n\n"
                    f"👤 Xodim: {employee_name}\n"
                    f"📅 Davr: {start_date.strftime('%d.%m')} - {end_date.strftime('%d.%m.%Y')}\n\n"
                    f"📭 Oxirgi 30 kunda bajarilgan vazifalar yo'q."
                )
                return
            
            total_earned = sum(task[3] for task in monthly_tasks if task[3])
            avg_per_task = total_earned / len(monthly_tasks) if monthly_tasks else 0
            
            report_text = f"📆 **Oylik hisobot**\n\n"
            report_text += f"👤 Xodim: {employee_name}\n"
            report_text += f"📅 Davr: {start_date.strftime('%d.%m')} - {end_date.strftime('%d.%m.%Y')}\n\n"
            report_text += f"✅ Bajarilgan vazifalar: {len(monthly_tasks)} ta\n"
            report_text += f"💰 Jami ishlab topilgan: {total_earned:,.0f} so'm\n"
            report_text += f"📊 O'rtacha vazifa uchun: {avg_per_task:,.0f} so'm\n\n"
            
            # Group by weeks
            weeks_data = {}
            for task in monthly_tasks:
                try:
                    task_date = datetime.fromisoformat(task[2])
                    week_start = task_date - timedelta(days=task_date.weekday())
                    week_key = week_start.strftime("%d.%m")
                    
                    if week_key not in weeks_data:
                        weeks_data[week_key] = {"count": 0, "amount": 0}
                    
                    weeks_data[week_key]["count"] += 1
                    if task[3]:
                        weeks_data[week_key]["amount"] += task[3]
                except:
                    pass
            
            if weeks_data:
                report_text += "📈 **Haftalik taqsimot:**\n\n"
                for week, data in weeks_data.items():
                    report_text += f"📅 {week} haftasi: {data['count']} vazifa | {data['amount']:,.0f} so'm\n"
            
            bot.send_message(message.chat.id, report_text)
            
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Oylik hisobot yuklanmadi: {str(e)}")

    @bot.message_handler(func=lambda message: message.text == "📈 Umumiy statistika")
    def show_employee_statistics(message):
        """Show overall employee statistics"""
        employee_name = None
        for name, chat_id in EMPLOYEES.items():
            if chat_id == message.chat.id:
                employee_name = name
                break
        
        if not employee_name:
            bot.send_message(message.chat.id, "❌ Profil topilmadi.")
            return
        
        try:
            from database import DATABASE_PATH
            import sqlite3
            from datetime import datetime
            
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()
            
            # Get all task statistics
            cursor.execute("""
                SELECT status, COUNT(*), COALESCE(SUM(received_amount), 0)
                FROM tasks 
                WHERE assigned_to = ?
                GROUP BY status
            """, (employee_name,))
            
            status_stats = cursor.fetchall()
            
            # Get first task date
            cursor.execute("""
                SELECT MIN(created_at) FROM tasks WHERE assigned_to = ?
            """, (employee_name,))
            
            first_task_date = cursor.fetchone()[0]
            conn.close()
            
            # Calculate statistics
            stats = {
                'pending': {'count': 0, 'amount': 0},
                'in_progress': {'count': 0, 'amount': 0},
                'completed': {'count': 0, 'amount': 0}
            }
            
            total_tasks = 0
            total_earned = 0
            
            for status, count, amount in status_stats:
                if status in stats:
                    stats[status] = {'count': count, 'amount': amount}
                    total_tasks += count
                    if status == 'completed':
                        total_earned += amount
            
            try:
                start_date = datetime.fromisoformat(first_task_date).strftime("%d.%m.%Y") if first_task_date else "Noma'lum"
            except:
                start_date = "Noma'lum"
            
            completion_rate = (stats['completed']['count'] / total_tasks * 100) if total_tasks > 0 else 0
            
            stats_text = f"📈 **{employee_name}** - Umumiy statistika\n\n"
            stats_text += f"📅 Birinchi vazifa: {start_date}\n"
            stats_text += f"📊 Jami vazifalar: {total_tasks} ta\n"
            stats_text += f"📈 Bajarish foizi: {completion_rate:.1f}%\n\n"
            
            stats_text += f"⏳ Kutilayotgan: {stats['pending']['count']} ta\n"
            stats_text += f"🔄 Jarayonda: {stats['in_progress']['count']} ta\n"
            stats_text += f"✅ Bajarilgan: {stats['completed']['count']} ta\n\n"
            
            stats_text += f"💰 **Jami ishlab topilgan:** {total_earned:,.0f} so'm\n"
            
            if stats['completed']['count'] > 0:
                avg_per_task = total_earned / stats['completed']['count']
                stats_text += f"📊 O'rtacha vazifa uchun: {avg_per_task:,.0f} so'm"
            
            bot.send_message(message.chat.id, stats_text)
            
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Statistika yuklanmadi: {str(e)}")

    @bot.message_handler(func=lambda message: message.text == "📤 Excel hisobot")
    def generate_employee_excel_report(message):
        """Generate Excel report for employee"""
        employee_name = None
        for name, chat_id in EMPLOYEES.items():
            if chat_id == message.chat.id:
                employee_name = name
                break
        
        if not employee_name:
            bot.send_message(message.chat.id, "❌ Profil topilmadi.")
            return
        
        bot.send_message(message.chat.id, "📤 Excel hisobot tayyorlanyapti...")
        
        try:
            from database import DATABASE_PATH
            import sqlite3
            from datetime import datetime
            import os
            
            # Get all tasks for employee
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, title, description, status, created_at, 
                       completion_report, received_amount
                FROM tasks 
                WHERE assigned_to = ?
                ORDER BY created_at DESC
            """, (employee_name,))
            
            tasks = cursor.fetchall()
            conn.close()
            
            if not tasks:
                bot.send_message(message.chat.id, "📭 Hisobot uchun vazifalar topilmadi.")
                return
            
            # Create text report
            report_text = f"📤 **{employee_name}** - To'liq hisobot\n"
            report_text += f"📅 Yaratilgan: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
            
            total_tasks = len(tasks)
            completed_tasks = sum(1 for task in tasks if task[3] == 'completed')
            total_earned = sum(task[6] for task in tasks if task[6])
            
            report_text += f"📊 **UMUMIY STATISTIKA:**\n"
            report_text += f"🔢 Jami vazifalar: {total_tasks} ta\n"
            report_text += f"✅ Bajarilgan: {completed_tasks} ta\n"
            report_text += f"📈 Bajarish foizi: {(completed_tasks/total_tasks*100):.1f}%\n"
            report_text += f"💰 Jami daromad: {total_earned:,.0f} so'm\n\n"
            
            report_text += f"📋 **VAZIFALAR RO'YXATI:**\n\n"
            
            for i, task in enumerate(tasks, 1):
                task_id, title, description, status, created_at, completion_report, received_amount = task
                
                try:
                    created_date = datetime.fromisoformat(created_at).strftime("%d.%m.%Y %H:%M")
                except:
                    created_date = created_at[:16] if created_at else "Noma'lum"
                
                status_uz = {
                    'pending': '⏳ Kutilmoqda',
                    'in_progress': '🔄 Bajarilmoqda', 
                    'completed': '✅ Tugallangan'
                }.get(status, status)
                
                amount_text = f"{received_amount:,.0f} so'm" if received_amount else "To'lov yo'q"
                
                report_text += f"{i}. **{title}**\n"
                report_text += f"   🆔 ID: {task_id}\n"
                report_text += f"   📊 Holat: {status_uz}\n"
                report_text += f"   📅 Sana: {created_date}\n"
                report_text += f"   💰 To'lov: {amount_text}\n"
                if description:
                    desc_preview = description[:100] + "..." if len(description) > 100 else description
                    report_text += f"   📝 Tavsif: {desc_preview}\n"
                if completion_report:
                    report_preview = completion_report[:100] + "..." if len(completion_report) > 100 else completion_report
                    report_text += f"   📋 Hisobot: {report_preview}\n"
                report_text += "\n"
            
            # Create reports directory
            os.makedirs("reports", exist_ok=True)
            
            # Save to text file
            filename = f"reports/{employee_name}_hisobot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(report_text)
            
            filepath = filename
            
            if filepath and os.path.exists(filepath):
                with open(filepath, 'rb') as f:
                    bot.send_document(
                        message.chat.id,
                        f,
                        caption=f"📤 {employee_name} - Excel hisobot"
                    )
                # Clean up file
                os.remove(filepath)
                bot.send_message(message.chat.id, "✅ Excel hisobot yuborildi!")
            else:
                bot.send_message(message.chat.id, "❌ Excel hisobot yaratishda xatolik yuz berdi.")
                
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Excel hisobot xatoligi: {str(e)}")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("start_task_"))
    def start_task(call):
        """Start a task"""
        task_id = int(call.data.split("_")[-1])
        
        try:
            # Get task details including location
            task = get_task_by_id(task_id)
            if not task:
                bot.answer_callback_query(call.id, "❌ Vazifa topilmadi!")
                return
            
            update_task_status(task_id, "in_progress")
            
            bot.edit_message_reply_markup(
                call.message.chat.id,
                call.message.message_id,
                reply_markup=None
            )
            
            # Prepare task start message
            start_message = "✅ Vazifa boshlandi!\n\n"
            start_message += f"📝 Vazifa: {task[1]}\n\n"  # description
            start_message += "Vazifani yakunlash uchun '📌 Mening vazifalarim' bo'limiga o'ting."
            
            bot.send_message(call.message.chat.id, start_message)
            
            # Send location if coordinates are available
            if task[2] and task[3]:
                bot.send_location(call.message.chat.id, task[2], task[3])
                bot.send_message(call.message.chat.id, "📍 Vazifa joylashuvi yuqorida ko'rsatilgan.")
            
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
            show_employee_panel(message)
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
            
            # Return to employee panel after task completion
            # Task completed successfully
            
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
        show_employee_panel(message)

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
            
            # Return to employee panel after task completion
            # Task completed successfully
            
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
        show_employee_panel(message)

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
            
            # Return to employee panel after task completion
            # Task completed successfully
            
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
        show_employee_panel(message)

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
    @bot.message_handler(func=lambda message: message.text == "🔙 Ortga" and message.chat.id != ADMIN_CHAT_ID)
    def go_back(message):
        """Go back to main menu for non-admin users"""
        clear_user_state(message.chat.id)
        start_message(message)
    
    @bot.message_handler(func=lambda message: message.text == "🔙 Ortga" and message.chat.id == ADMIN_CHAT_ID)
    def admin_go_back(message):
        """Go back to admin panel"""
        clear_user_state(message.chat.id)
        start_message(message)


    # =============================================================================
    # ENTERTAINMENT SYSTEM REMOVED PER USER REQUEST
    # =============================================================================

    # Callback query handlers for interactive location cards

    # Callback query handlers for interactive location cards
    @bot.callback_query_handler(func=lambda call: call.data.startswith('calc_distance_'))
    def handle_distance_calculation(call):
        """Handle distance calculation from location"""
        try:
            _, _, lat, lon = call.data.split('_')
            latitude = float(lat)
            longitude = float(lon)
            
            # Create inline keyboard for distance calculation options
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(
                types.InlineKeyboardButton("📍 Toshkent markazidan", callback_data=f"dist_tashkent_{lat}_{lon}"),
                types.InlineKeyboardButton("🏢 Ofisdan", callback_data=f"dist_office_{lat}_{lon}")
            )
            keyboard.add(
                types.InlineKeyboardButton("🔙 Orqaga", callback_data=f"back_location_{lat}_{lon}")
            )
            
            bot.edit_message_text(
                "📏 **Masofa Hisoblash**\n\n"
                "Qaysi joydan masofani hisoblashni xohlaysiz?",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            bot.answer_callback_query(call.id, f"❌ Xatolik: {str(e)}")

    @bot.callback_query_handler(func=lambda call: call.data.startswith('dist_'))
    def handle_specific_distance(call):
        """Calculate specific distance"""
        try:
            parts = call.data.split('_')
            location_type = parts[1]
            lat = float(parts[2])
            lon = float(parts[3])
            
            # Define reference points
            reference_points = {
                'tashkent': (41.2995, 69.2401, "Toshkent markaziga"),
                'office': (41.3111, 69.2797, "Ofisga")  # Example office coordinates
            }
            
            if location_type in reference_points:
                ref_lat, ref_lon, location_name = reference_points[location_type]
                
                # Calculate distance using Haversine formula
                import math
                
                def haversine_distance(lat1, lon1, lat2, lon2):
                    R = 6371  # Earth's radius in kilometers
                    
                    lat1_rad = math.radians(lat1)
                    lon1_rad = math.radians(lon1)
                    lat2_rad = math.radians(lat2)
                    lon2_rad = math.radians(lon2)
                    
                    dlat = lat2_rad - lat1_rad
                    dlon = lon2_rad - lon1_rad
                    
                    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
                    c = 2 * math.asin(math.sqrt(a))
                    
                    return R * c
                
                distance = haversine_distance(ref_lat, ref_lon, lat, lon)
                
                # Create result message
                result_text = f"""
📏 **Masofa Hisoboti**

📍 **Manzil:** {location_name}
🎯 **Belgilangan joy:** {lat:.6f}, {lon:.6f}

📐 **Masofa:** {distance:.2f} km
⏱ **Taxminiy vaqt:**
• 🚗 Avtomobil: {int(distance * 2)} daqiqa
• 🚶 Piyoda: {int(distance * 12)} daqiqa

🗺 **Navigatsiya:**
• [Google Maps Yo'l](https://maps.google.com/maps?saddr={ref_lat},{ref_lon}&daddr={lat},{lon})
"""
                
                keyboard = types.InlineKeyboardMarkup()
                keyboard.add(
                    types.InlineKeyboardButton("🗺 Navigatsiya", url=f"https://maps.google.com/maps?saddr={ref_lat},{ref_lon}&daddr={lat},{lon}"),
                    types.InlineKeyboardButton("🔙 Orqaga", callback_data=f"back_location_{lat}_{lon}")
                )
                
                bot.edit_message_text(
                    result_text,
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
            
        except Exception as e:
            bot.answer_callback_query(call.id, f"❌ Xatolik: {str(e)}")

    @bot.callback_query_handler(func=lambda call: call.data.startswith('nearby_places_'))
    def handle_nearby_places(call):
        """Show nearby places"""
        try:
            _, _, lat, lon = call.data.split('_')
            latitude = float(lat)
            longitude = float(lon)
            
            # Simulated nearby places (in real implementation, you would use Google Places API)
            nearby_info = f"""
📊 **Atrofdagi Joylar**

📍 **Koordinatalar:** {latitude:.6f}, {longitude:.6f}

🏢 **Yaqin ob'yektlar:**
• 🏪 Do'konlar va supermarketlar
• ⛽ Yoqilg'i quyish shoxobchalari  
• 🏥 Tibbiyot muassasalari
• 🍽 Restoranlar va kafelar
• 🏧 ATM va banklar

📱 **Qo'shimcha ma'lumot:**
Bu joyni quyidagi xizmatlar orqali o'rganishingiz mumkin:
"""
            
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(
                types.InlineKeyboardButton("🗺 Google Maps", url=f"https://maps.google.com/?q={latitude},{longitude}"),
                types.InlineKeyboardButton("🔍 Yandex", url=f"https://yandex.ru/maps/?ll={longitude},{latitude}&z=16")
            )
            keyboard.add(
                types.InlineKeyboardButton("🔙 Orqaga", callback_data=f"back_location_{lat}_{lon}")
            )
            
            bot.edit_message_text(
                nearby_info,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            bot.answer_callback_query(call.id, f"❌ Xatolik: {str(e)}")

    @bot.callback_query_handler(func=lambda call: call.data.startswith('refresh_location_'))
    def handle_location_refresh(call):
        """Refresh location information"""
        try:
            _, _, lat, lon = call.data.split('_')
            latitude = float(lat)
            longitude = float(lon)
            
            current_time = datetime.now().strftime('%d.%m.%Y %H:%M:%S')
            
            refresh_text = f"""
🔄 **Lokatsiya Yangilandi**

📍 **Koordinatalar:** {latitude:.6f}, {longitude:.6f}
⏰ **Yangilangan vaqt:** {current_time}
📡 **Status:** ✅ Faol va aniq

🎯 **Yangilangan ma'lumotlar:**
• GPS signali: Kuchli
• Aniqlik: Yuqori
• Oxirgi yangilanish: Hozir
"""
            
            keyboard = types.InlineKeyboardMarkup(row_width=2)
            keyboard.add(
                types.InlineKeyboardButton("🧭 Navigatsiya", url=f"https://maps.google.com/?q={latitude},{longitude}"),
                types.InlineKeyboardButton("📱 Telefondan ochish", url=f"geo:{latitude},{longitude}")
            )
            keyboard.add(
                types.InlineKeyboardButton("📏 Masofa hisoblash", callback_data=f"calc_distance_{latitude}_{longitude}"),
                types.InlineKeyboardButton("📊 Atrofdagi joylar", callback_data=f"nearby_places_{latitude}_{longitude}")
            )
            
            bot.edit_message_text(
                refresh_text,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            
            bot.answer_callback_query(call.id, "🔄 Ma'lumotlar yangilandi!")
            
        except Exception as e:
            bot.answer_callback_query(call.id, f"❌ Xatolik: {str(e)}")

    @bot.callback_query_handler(func=lambda call: call.data.startswith('back_location_'))
    def handle_back_to_location(call):
        """Return to main location view"""
        try:
            _, _, lat, lon = call.data.split('_')
            latitude = float(lat)
            longitude = float(lon)
            
            # Recreate the main location interface
            keyboard = types.InlineKeyboardMarkup(row_width=2)
            keyboard.add(
                types.InlineKeyboardButton("🧭 Navigatsiya", url=f"https://maps.google.com/?q={latitude},{longitude}"),
                types.InlineKeyboardButton("📱 Telefondan ochish", url=f"geo:{latitude},{longitude}")
            )
            keyboard.add(
                types.InlineKeyboardButton("📏 Masofa hisoblash", callback_data=f"calc_distance_{latitude}_{longitude}"),
                types.InlineKeyboardButton("🔄 Yangilash", callback_data=f"refresh_location_{latitude}_{longitude}")
            )
            keyboard.add(
                types.InlineKeyboardButton("📊 Atrofdagi joylar", callback_data=f"nearby_places_{latitude}_{longitude}")
            )
            
            bot.edit_message_text(
                f"🎮 **Interaktiv Amallar**\n\n"
                f"Lokatsiya bilan ishlash uchun tugmalarni bosing:",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            bot.answer_callback_query(call.id, f"❌ Xatolik: {str(e)}")

    # Error handler
    @bot.message_handler(func=lambda message: True)
    def handle_unknown(message):
        """Handle unknown messages"""
        bot.send_message(
            message.chat.id,
            "❓ Tushunmadim. Iltimos, menyudan tanlang yoki /start bosing."
        )

    # Start the bot with enhanced error handling for production
    try:
        print("🚀 Enhanced Telegram Task Management Bot ishga tushmoqda...")
        print(f"🔑 Bot Token: {'✅ Mavjud' if BOT_TOKEN else '❌ Mavjud emas'}")
        print(f"👑 Admin chat ID: {ADMIN_CHAT_ID}")
        print(f"👥 Xodimlar soni: {len(EMPLOYEES)}")
        print("📊 Ma'lumotlar bazasi tayyorlandi")
        print("✅ Bot muvaffaqiyatli ishga tushdi!")
        print("📱 Bot Telegram orqali foydalanishga tayyor")
        print("🛑 Botni to'xtatish uchun Ctrl+C bosing")
        
        # Enhanced polling with better error handling for production
        while True:
            try:
                print("🔄 Bot doimiy ishlash rejimida...")
                bot.infinity_polling(none_stop=True, interval=1, timeout=20, long_polling_timeout=60)
            except Exception as e:
                print(f"⚠️ Bot ulanishida xatolik: {e}")
                print("🔄 10 soniyadan keyin avtomatik qayta ulanish...")
                import time
                time.sleep(10)
                print("🚀 Bot qayta ishga tushirilmoqda...")
                continue
        
    except KeyboardInterrupt:
        print("\n🛑 Bot to'xtatildi.")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Jiddiy bot xatosi: {e}")
        print("🚨 Bot avtomatik qayta ishga tushirilmoqda...")
        import time
        time.sleep(15)
        print("🔄 Qayta ulanish...")
        # Recursive restart to ensure bot never stops
        try:
            main()  # Restart the entire main function
        except Exception as restart_error:
            print(f"❌ Qayta ishga tushirishda xatolik: {restart_error}")
            print("⏳ 30 soniya kutib, yana urinish...")
            time.sleep(30)
            main()  # Try again

if __name__ == "__main__":
    main()
