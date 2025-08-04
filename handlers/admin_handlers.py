import telebot
from telebot import types
from datetime import datetime
from utils.database import get_task_db, get_debt_db
from utils.excel_handler import ExcelHandler
from config import EMPLOYEES, ADMIN_CHAT_ID

class AdminHandler:
    def __init__(self, bot: telebot.TeleBot):
        self.bot = bot
        self.task_db = get_task_db()
        self.debt_db = get_debt_db()
        self.excel_handler = ExcelHandler()
        self.admin_task_data = {}
        self.admin_debt_data = {}
    
    def show_admin_panel(self, message):
        """Show main admin panel"""
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📝 Topshiriqlar", "📊 Qarzdorlik", "📋 Hisobot", "⬅️ Ortga")
        self.bot.send_message(message.chat.id, "Admin panelga xush kelibsiz!", reply_markup=markup)
    
    def start_task_creation(self, message):
        """Start task creation process"""
        chat_id = message.chat.id
        self.admin_task_data[chat_id] = {}
        msg = self.bot.send_message(chat_id, "📝 Topshiriq matnini kiriting:")
        self.bot.register_next_step_handler(msg, self.get_task_text)
    
    def get_task_text(self, message):
        """Get task description"""
        chat_id = message.chat.id
        self.admin_task_data[chat_id]["description"] = message.text
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        loc_btn = types.KeyboardButton("📍 Lokatsiyani yuborish", request_location=True)
        markup.add(loc_btn)
        self.bot.send_message(chat_id, "📍 Lokatsiyani yuboring:", reply_markup=markup)
    
    def receive_location(self, message):
        """Handle location reception"""
        chat_id = message.chat.id
        if chat_id in self.admin_task_data:
            self.admin_task_data[chat_id]["location"] = message.location
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add("💰 Pul miqdori")
            self.bot.send_message(chat_id, "✅ Lokatsiya qabul qilindi.\n💰 Endi pul miqdorini kiriting:", reply_markup=markup)
    
    def ask_payment(self, message):
        """Ask for payment amount"""
        msg = self.bot.send_message(message.chat.id, "💸 Pul miqdorini kiriting:")
        self.bot.register_next_step_handler(msg, self.save_payment)
    
    def save_payment(self, message):
        """Save payment amount"""
        chat_id = message.chat.id
        try:
            # Validate payment amount
            amount = float(message.text.replace(',', '').replace(' ', ''))
            self.admin_task_data[chat_id]["payment"] = amount
            
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add("👥 Kerakli hodimlar")
            self.bot.send_message(chat_id, "👥 Endi kerakli hodimlarni tanlang:", reply_markup=markup)
        except ValueError:
            msg = self.bot.send_message(chat_id, "❌ Iltimos, to'g'ri raqam kiriting:")
            self.bot.register_next_step_handler(msg, self.save_payment)
    
    def choose_employees(self, message):
        """Show employee selection menu"""
        chat_id = message.chat.id
        self.admin_task_data[chat_id]["selected"] = []
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        for name in EMPLOYEES:
            markup.add(name)
        markup.add("📨 Yuborish")
        self.bot.send_message(chat_id, "Tanlang (bir nechta hodim tanlashingiz mumkin):", reply_markup=markup)
        self.bot.register_next_step_handler(message, self.select_employee)
    
    def select_employee(self, message):
        """Handle employee selection"""
        chat_id = message.chat.id
        name = message.text
        
        if name == "📨 Yuborish":
            self.send_task_to_employees(message)
            return
        
        if name in EMPLOYEES:
            if name not in self.admin_task_data.get(chat_id, {}).get("selected", []):
                self.admin_task_data[chat_id]["selected"].append(name)
                self.bot.send_message(chat_id, f"✅ {name} tanlandi.")
            else:
                self.bot.send_message(chat_id, f"⚠️ {name} allaqachon tanlangan.")
        else:
            self.bot.send_message(chat_id, "❌ Tugmalardan birini tanlang.")
        
        self.bot.register_next_step_handler(message, self.select_employee)
    
    def send_task_to_employees(self, message):
        """Send task to selected employees"""
        chat_id = message.chat.id
        data = self.admin_task_data.get(chat_id)
        
        if not data or "location" not in data or "description" not in data or "payment" not in data or not data.get("selected"):
            self.bot.send_message(chat_id, "❌ Ma'lumotlar to'liq emas. Iltimos, qaytadan boshlang.")
            return
        
        lat, lon = data["location"].latitude, data["location"].longitude
        task_text = f"📢 Sizga yangi topshiriq:\n\n📝 {data['description']}\n📍 Lokatsiya: xaritada\n💰 Pul: {data['payment']} so'm"
        
        # Send to each selected employee
        success_count = 0
        for name in data["selected"]:
            user_id = EMPLOYEES.get(name)
            if not user_id:
                continue
            
            try:
                # Send task message and location
                self.bot.send_message(user_id, task_text)
                self.bot.send_location(user_id, latitude=lat, longitude=lon)
                
                # Save to database
                short_name = name.split()[-1]
                location_str = f"{lat}, {lon}"
                self.task_db.add_task(
                    description=data['description'],
                    location=location_str,
                    employee=short_name,
                    amount=data['payment']
                )
                success_count += 1
                
            except Exception as e:
                self.bot.send_message(chat_id, f"⚠️ {name} ga yuborilmadi.\nXato: {e}")
        
        # Save to Excel
        self.excel_handler.save_task_to_excel(
            data['description'], 
            data['location'], 
            data['selected'], 
            str(data['payment'])
        )
        
        if success_count > 0:
            self.bot.send_message(chat_id, f"✅ Topshiriq {success_count} ta hodimga yuborildi.")
        
        self.show_admin_panel(message)
    
    def show_debt_menu(self, message):
        """Show debt management menu"""
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("➕ Qarz qo'shish", "📋 Qarzlarni ko'rish", "🔙 Orqaga")
        self.bot.send_message(message.chat.id, "Qarzdorlik bo'limi:", reply_markup=markup)
    
    def start_add_debt(self, message):
        """Start debt addition process"""
        chat_id = message.chat.id
        self.admin_debt_data[chat_id] = {}
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        for name in EMPLOYEES:
            markup.add(name)
        
        msg = self.bot.send_message(chat_id, "Hodimni tanlang:", reply_markup=markup)
        self.bot.register_next_step_handler(msg, self.select_debt_employee)
    
    def select_debt_employee(self, message):
        """Select employee for debt"""
        chat_id = message.chat.id
        employee_name = message.text
        
        if employee_name not in EMPLOYEES:
            msg = self.bot.send_message(chat_id, "❌ Iltimos, ro'yxatdagi hodimni tanlang:")
            self.bot.register_next_step_handler(msg, self.select_debt_employee)
            return
        
        self.admin_debt_data[chat_id]["employee"] = employee_name
        msg = self.bot.send_message(chat_id, "💸 Qarz miqdorini kiriting:")
        self.bot.register_next_step_handler(msg, self.get_debt_amount)
    
    def get_debt_amount(self, message):
        """Get debt amount"""
        chat_id = message.chat.id
        try:
            amount = float(message.text.replace(',', '').replace(' ', ''))
            self.admin_debt_data[chat_id]["amount"] = amount
            msg = self.bot.send_message(chat_id, "📝 Qarz sababini kiriting:")
            self.bot.register_next_step_handler(msg, self.get_debt_reason)
        except ValueError:
            msg = self.bot.send_message(chat_id, "❌ Iltimos, to'g'ri raqam kiriting:")
            self.bot.register_next_step_handler(msg, self.get_debt_amount)
    
    def get_debt_reason(self, message):
        """Get debt reason and save"""
        chat_id = message.chat.id
        reason = message.text
        
        data = self.admin_debt_data.get(chat_id)
        if not data:
            self.bot.send_message(chat_id, "❌ Ma'lumotlar yo'qoldi. Qaytadan boshlang.")
            return
        
        # Save debt to database
        employee_name = data["employee"].split()[-1]  # Get short name
        if self.debt_db.add_debt(employee_name, data["amount"], reason):
            self.bot.send_message(chat_id, f"✅ {data['employee']} uchun qarz qo'shildi:\n💰 {data['amount']} so'm\n📝 {reason}")
        else:
            self.bot.send_message(chat_id, "❌ Qarz qo'shishda xato yuz berdi.")
        
        self.show_debt_menu(message)
    
    def show_all_debts(self, message):
        """Show debts for all employees"""
        chat_id = message.chat.id
        total_debt = 0
        debt_info = []
        
        for name, user_id in EMPLOYEES.items():
            short_name = name.split()[-1]
            debts = self.debt_db.get_debts_by_employee(short_name)
            if debts:
                employee_total = sum(debt['amount'] for debt in debts)
                debt_info.append(f"{name}: {employee_total} so'm")
                total_debt += employee_total
        
        if debt_info:
            message_text = "📊 Barcha hodimlar qarzi:\n\n" + "\n".join(debt_info)
            message_text += f"\n\n💰 Umumiy qarz: {total_debt} so'm"
        else:
            message_text = "✅ Hech qanday qarz yo'q."
        
        self.bot.send_message(chat_id, message_text)
