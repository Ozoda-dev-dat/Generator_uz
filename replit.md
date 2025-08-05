# Overview

This project is an Enhanced Telegram Task Management Bot built in Python. Its main purpose is to facilitate comprehensive task assignment and tracking between administrators and employees. Key capabilities include creating tasks, assigning them, tracking completion status with media, and generating detailed reports. The bot supports advanced features like location sharing, real-time employee tracking, Excel-based reporting, debt management (including a "Boshqalar" category), handling various media files (photos, videos, voice), direct employee management, comprehensive data management, and multi-step task completion workflows. The system is designed for small to medium-sized teams needing sophisticated work assignment management through Telegram with professional reporting capabilities.

# User Preferences

Preferred communication style: Simple, everyday language.
Task completion flow: Employees should return to main menu (employee panel) after completing tasks, not task list.

# System Architecture

## Bot Framework and Communication
- **Framework**: pyTelegramBotAPI (telebot)
- **Architecture Pattern**: Single-file comprehensive design with advanced state management
- **Session Management**: Database-persistent user state tracking with JSON serialization
- **Multi-step Conversations**: Advanced conversation flows with context preservation

## Data Storage
- **Database**: Single SQLite database (`task_management.db`) with normalized schema
- **Database Tables**: `tasks`, `debts`, `messages`, `user_states`
- **File Storage**: Organized `media/` and `reports/` directories with automatic creation
- **Media Management**: Advanced file handling for photos, videos, voice messages with unique naming

## Authentication and Authorization
- **Admin Authentication**: Environment-variable based secure admin code verification
- **Employee Identification**: Chat ID-based recognition with employee roster
- **Role-based Access**: Permission system with admin-only features
- **State Persistence**: Database-backed session management

## Core Features Architecture
- **Task Management**: Complete lifecycle tracking (pending → in_progress → completed) with optional payment amounts
- **Media Integration**: Support for task completion with photo/video proof and voice reports
- **Location Services**: GPS location sharing for task assignments and employee tracking; includes animated cards with Google Maps/Yandex Maps integration, distance calculation, and navigation links.
- **Reporting System**: Professional Excel generation with multi-sheet reports and statistics
- **Debt Management**: Integrated debt tracking with task completion workflows, supporting employees and "Boshqalar" (Others) category
- **Employee Management**: Direct employee addition by admins with name and Telegram ID
- **Data Management**: Comprehensive data viewing, insertion, and deletion capabilities
- **Real-time Notifications**: Admin notification system for task updates and completions
- **Customer Inquiry System**: Comprehensive management system for inquiries from website and Telegram, with admin response capabilities and real-time notifications.
- **Payment Processing System**: Three-way payment method (card, cash, debt) with detailed admin notifications.
- **Streamlined Employee Experience**: Focused work environment without entertainment distractions.

## File and Data Management
- **Excel Integration**: `openpyxl` for multi-sheet report generation
- **Directory Structure**: Organized `reports/` and `media/` directories
- **Media Handling**: Secure file download, storage, and admin forwarding
- **Data Serialization**: JSON-based complex data storage for conversation states

# External Dependencies

## Core Libraries
- **pyTelegramBotAPI**: Telegram Bot API wrapper
- **openpyxl**: Excel file creation
- **sqlite3**: Built-in Python SQLite interface
- **json**: Data serialization

## Telegram Bot API Features
- **Bot Token**: Environment variable-based authentication
- **Webhook/Polling**: Enhanced polling with error recovery
- **Message Types**: Support for text, location, photos, videos, voice messages
- **Interactive Elements**: Inline keyboards, callback queries, and custom reply keyboards
- **File Handling**: Media download, processing, and forwarding

## Configuration Management
- **Environment Variables**: `BOT_TOKEN`, `ADMIN_CODE`, `ADMIN_CHAT_ID`
- **Static Configuration**: Employee roster in `config.py`
- **Runtime Configuration**: Automatic database and directory initialization
- **Dynamic Employee Management**: Real-time employee addition updating `config.py`

## External Services/APIs
- **Google Maps / Yandex Maps**: For location sharing and navigation links
- **Website API Integration**: RESTful API (`website_api.py`) for submitting and managing customer inquiries from an external website.