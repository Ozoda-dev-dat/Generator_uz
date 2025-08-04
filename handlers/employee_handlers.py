import telebot
from telebot import types
from datetime import datetime, timedelta
from utils.database import get_task_db
from utils.excel_handler import ExcelHandler
from config import EMPLOYEES

class EmployeeHandler:
    def __init__(self, bot: telebot.TeleBot):
        self.bot = bot
        self.task_db = get_task_db()
        self.excel_handler = ExcelHandler()
        self.employee_states = {}
    
    def show_employee_panel(self, message):
        """Show employee main panel"""
        chat_id = message.chat.id
        
        # Find employee name by chat ID
        employee_name = None
        for name, emp_id in EMPLOYEES.items():
            if emp_id == chat_id:
                employee_name = name.split()[-1]  # Get short name
                break
        
        if not employee_name:
            self.bot.send_message(chat_id, "❌ Siz ro'yxatda yo'qsiz.")
            return
        
        # Store employee info
        self.employee_states[chat_id] = {"name": employee_name}
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📋 Mening vazifalarim", "✅ Bajarilgan vazifalar")
        markup.add("📊 Hisobot", "⬅️ Ortga")
        
        self.bot.send_message(chat_id, f"Xush kelibsiz, {employee_name}!", reply_markup=markup)
    
    def show_my_tasks(self, message):
        """Show employee's current tasks"""
        chat_id = message.chat.id
        employee_name = self.employee_states.get(chat_id, {}).get("name")
        
        if not employee_name:
            self.bot.send_message(chat_id, "❌ Hodim ma'lumotlari topilmadi.")
            return
        
        # Get pending tasks
        tasks = self.task_db.get_tasks_by_employee(employee_name, "⏳ Davom etmoqda")
        
        if not tasks:
            self.bot.send_message(chat_id, "📋 Sizda hozircha vazifalar yo'q.")
            return
        
        for task in tasks:
            task_text = f"📝 Vazifa: {task['description']}\n"
            task_text += f"📍 Manzil: {task['location']}\n"
            task_text += f"💰 To'lov: {task['amount']} so'm\n"
            task_text += f"📅 Sana: {task['date']} {task['time']}\n"
            task_text += f"📞 Telefon: {task['phone']}"
            
            # Create inline keyboard for task actions
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("✅ Bajarildi", callback_data=f"complete_{task['id']}"),
                types.InlineKeyboardButton("🔄 Jarayonda", callback_data=f"progress_{task['id']}")
            )
            
            self.bot.send_message(chat_id, task_text, reply_markup=markup)
    
    def show_completed_tasks(self, message):
        """Show employee's completed tasks"""
        chat_id = message.chat.id
        employee_name = self.employee_states.get(chat_id, {}).get("name")
        
        if not employee_name:
            self.bot.send_message(chat_id, "❌ Hodim ma'lumotlari topilmadi.")
            return
        
        # Get completed tasks
        tasks = self.task_db.get_tasks_by_employee(employee_name, "✅ Bajarildi")
        
        if not tasks:
            self.bot.send_message(chat_id, "📋 Bajarilgan vazifalar yo'q.")
            return
        
        total_amount = sum(task['amount'] for task in tasks)
        task_count = len(tasks)
        
        message_text = f"✅ Bajarilgan vazifalar: {task_count} ta\n"
        message_text += f"💰 Umumiy to'lov: {total_amount} so'm\n\n"
        
        # Show last 5 tasks
        for task in tasks[-5:]:
            message_text += f"📝 {task['description']}\n"
            message_text += f"💰 {task['amount']} so'm - {task['date']}\n\n"
        
        if task_count > 5:
            message_text += f"... va yana {task_count - 5} ta vazifa"
        
        self.bot.send_message(chat_id, message_text)
    
    def show_report_menu(self, message):
        """Show report menu"""
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📅 30 kunlik hisobot", "🗓 1 haftalik hisobot")
        markup.add("📤 Excel faylga chop etish", "🔙 Ortga")
        self.bot.send_message(message.chat.id, "Quyidagilardan birini tanlang:", reply_markup=markup)
    
    def report_30_days(self, message):
        """Generate 30-day report"""
        chat_id = message.chat.id
        employee_name = self.employee_states.get(chat_id, {}).get("name", "Noma'lum")
        
        today = datetime.now()
        start_date = today - timedelta(days=30)
        
        tasks = self.task_db.get_tasks_in_date_range(
            employee_name, 
            start_date.strftime("%Y-%m-%d"), 
            today.strftime("%Y-%m-%d")
        )
        
        if not tasks:
            self.bot.send_message(chat_id, "Oxirgi 30 kunda bajarilgan vazifalar yo'q.")
        else:
            total = sum(task['amount'] for task in tasks)
            self.bot.send_message(
                chat_id, 
                f"✅ 30 kun ichida {len(tasks)} ta vazifa bajarilgan.\n💰 Umumiy to'lov: {total} so'm."
            )
    
    def report_7_days(self, message):
        """Generate 7-day report"""
        chat_id = message.chat.id
        employee_name = self.employee_states.get(chat_id, {}).get("name", "Noma'lum")
        
        today = datetime.now()
        start_date = today - timedelta(days=7)
        
        tasks = self.task_db.get_tasks_in_date_range(
            employee_name, 
            start_date.strftime("%Y-%m-%d"), 
            today.strftime("%Y-%m-%d")
        )
        
        if not tasks:
            self.bot.send_message(chat_id, "Oxirgi 7 kunda bajarilgan vazifalar yo'q.")
        else:
            total = sum(task['amount'] for task in tasks)
            self.bot.send_message(
                chat_id, 
                f"✅ 1 hafta ichida {len(tasks)} ta vazifa bajarilgan.\n💰 Umumiy to'lov: {total} so'm."
            )
    
    def export_excel_report(self, message):
        """Export Excel report"""
        chat_id = message.chat.id
        employee_name = self.employee_states.get(chat_id, {}).get("name", "Noma'lum")
        
        today = datetime.now()
        start_date = today - timedelta(days=30)
        
        tasks = self.task_db.get_tasks_in_date_range(
            employee_name, 
            start_date.strftime("%Y-%m-%d"), 
            today.strftime("%Y-%m-%d")
        )
        
        if not tasks:
            self.bot.send_message(chat_id, "Excelga chop etiladigan vazifalar yo'q.")
            return
        
        # Create Excel file
        filepath = self.excel_handler.create_employee_report(employee_name, tasks)
        
        if filepath:
            try:
                with open(filepath, "rb") as f:
                    self.bot.send_document(chat_id, f, caption="📤 Excel hisobotingiz tayyor!")
            except Exception as e:
                self.bot.send_message(chat_id, f"❌ Fayl yuborishda xato: {e}")
        else:
            self.bot.send_message(chat_id, "❌ Excel fayl yaratishda xato.")
    
    def handle_task_callback(self, call):
        """Handle task status update callbacks"""
        try:
            action, task_id = call.data.split('_')
            task_id = int(task_id)
            
            if action == "complete":
                status = "✅ Bajarildi"
                message = "✅ Vazifa bajarildi deb belgilandi!"
            elif action == "progress":
                status = "🔄 Jarayonda"
                message = "🔄 Vazifa jarayonda deb belgilandi!"
            else:
                return
            
            # Update task status
            if self.task_db.update_task_status(task_id, status):
                self.bot.answer_callback_query(call.id, message)
                self.bot.edit_message_reply_markup(
                    call.message.chat.id, 
                    call.message.message_id, 
                    reply_markup=None
                )
            else:
                self.bot.answer_callback_query(call.id, "❌ Status yangilanmadi!")
                
        except Exception as e:
            self.bot.answer_callback_query(call.id, f"❌ Xato: {e}")
