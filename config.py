import os

# Bot configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CODE = os.getenv("ADMIN_CODE", "1234")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "7792775986"))

# Database configuration
DATABASE_PATH = "task_management.db"

# Employee configuration
EMPLOYEES = {
    "👨‍🔧 Kamol": 7442895800,
    "👨‍🔧 Fozil": 747368650,
    "👨‍🔧 Asomiddin": 1894259641,
    "👨‍🔧 Farruh": 1037206796,
    "Ozoda": 826129625,
}

# File paths
REPORTS_DIR = "reports"
MEDIA_DIR = "media"
EXCEL_FILE = "tasks_report.xlsx"
