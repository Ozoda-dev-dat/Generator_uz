# Overview

This is an Enhanced Telegram Task Management Bot built in Python that facilitates comprehensive task assignment and tracking between administrators and employees. The bot provides a complete workflow for creating tasks, assigning them to specific employees, tracking completion status with media attachments, and generating detailed reports. It includes advanced features like location sharing, real-time employee tracking, Excel-based reporting, debt management (including "Boshqalar" category), media file handling (photos, videos, voice), direct employee management, comprehensive data management capabilities, and multi-step task completion workflows. The system is designed for small to medium-sized teams requiring sophisticated work assignment management through Telegram with professional reporting capabilities.

# User Preferences

Preferred communication style: Simple, everyday language.
Task completion flow: Employees should return to main menu (employee panel) after completing tasks, not task list.

# System Architecture

## Bot Framework and Communication
- **Framework**: pyTelegramBotAPI (telebot) for Telegram bot integration
- **Architecture Pattern**: Single-file comprehensive design with advanced state management
- **Session Management**: Database-persistent user state tracking with JSON serialization for complex data
- **Multi-step Conversations**: Advanced conversation flows with context preservation and error handling

## Data Storage
- **Database**: Single SQLite database (`task_management.db`) with normalized schema
- **Database Tables**: 
  - `tasks` - comprehensive task management with media and completion tracking
  - `debts` - financial obligation management linked to tasks
  - `messages` - notification and communication logging
  - `user_states` - persistent conversation state management
- **File Storage**: Organized media and report storage with automatic directory creation
- **Media Management**: Advanced file handling for photos, videos, voice messages with unique naming

## Authentication and Authorization
- **Admin Authentication**: Environment-variable based secure admin code verification
- **Employee Identification**: Chat ID-based recognition with comprehensive employee roster
- **Role-based Access**: Sophisticated permission system with admin-only features
- **State Persistence**: Database-backed session management for complex workflows

## Core Features Architecture
- **Task Management**: Complete lifecycle tracking (pending → in_progress → completed) with optional payment amounts
- **Media Integration**: Full support for task completion with photo/video proof and voice reports
- **Location Services**: GPS location sharing for task assignments and employee tracking
- **Reporting System**: Professional Excel generation with multi-sheet reports and statistics
- **Debt Management**: Integrated debt tracking with task completion workflows supporting both employees and "Boshqalar" (Others) category
- **Employee Management**: Direct employee addition with name and Telegram ID through admin interface
- **Data Management**: Comprehensive data viewing, insertion, and deletion capabilities
- **Real-time Notifications**: Admin notification system for task updates and completions

## File and Data Management
- **Excel Integration**: openpyxl with professional multi-sheet report generation
- **Directory Structure**: Organized `reports/` and `media/` directories with automatic creation
- **Media Handling**: Secure file download, storage, and admin forwarding capabilities
- **Data Serialization**: JSON-based complex data storage for conversation states

## Recent Changes (August 5, 2025)

### Panel Interface Restoration (August 5, 2025)
- **Original Panel Layout Restored**: Admin and employee panels returned to their original button configuration per user preference
- **Admin Panel**: ➕ Yangi xodim qo'shish, 📤 Vazifa berish, 📍 Xodimlarni kuzatish, 👥 Mijozlar so'rovlari, 💸 Qarzlar, 📊 Ma'lumotlar
- **Employee Panel**: 📌 Mening vazifalarim, 📂 Vazifalar tarixi, 📊 Hisobotlar, 🎊 Ko'ngilochar
- **Traditional Interface**: Simple, familiar button layout that users prefer over floating action buttons
- **Entertainment Access**: Restored to original 🎊 Ko'ngilochar submenu with entertainment options

### Enhanced Customer Inquiry System
- **Comprehensive Customer Support**: Complete customer inquiry management system with website and Telegram integration
- **Dual-Source Inquiries**: Separate handling for website (`source='website'`) and Telegram bot (`source='telegram'`) inquiries
- **Customer Contact Flow**: Multi-step customer contact process with phone sharing, location sharing, and inquiry submission
- **Admin Response System**: Full admin interface for viewing, managing, and responding to customer inquiries
- **Website API Integration**: RESTful API (`website_api.py`) for website integration with endpoints:
  - `POST /api/submit_inquiry` - Submit customer inquiries from website
  - `GET /api/inquiry_status/{id}` - Check inquiry status
  - `GET /api/health` - API health check
- **Real-time Notifications**: Automatic admin notifications for new inquiries from both sources
- **Database Schema Extension**: New `customer_inquiries` table with comprehensive customer data tracking
- **Customer Commands**: `/contact`, `/sorov`, `/murojaat` commands for easy customer access
- **Location and Contact Integration**: Full support for customer location sharing and contact information
- **Admin Panel Integration**: "👥 Mijozlar so'rovlari" button in admin panel with submenus:
  - `🌐 Website dan kelgan so'rovlar` - View and respond to website inquiries
  - `🤖 Botdan kelgan so'rovlar` - View and respond to bot inquiries
  - `📋 Barcha so'rovlar` - View all inquiries from both sources
  - `📊 So'rovlar statistikasi` - Inquiry statistics and analytics
- **Dual Workflow System**: Bot runs on default workflow, Website API runs on port 8080 separately

# External Dependencies

## Core Libraries
- **pyTelegramBotAPI**: Advanced Telegram Bot API wrapper with callback query support
- **openpyxl**: Professional Excel file creation with multi-sheet and formatting capabilities
- **sqlite3**: Built-in Python SQLite interface with advanced query operations
- **json**: Data serialization for complex conversation state management

## Telegram Bot API Features
- **Bot Token**: Secure environment variable-based authentication
- **Webhook/Polling**: Enhanced polling with error recovery and timeout handling
- **Message Types**: Comprehensive support for text, location, photos, videos, voice messages
- **Interactive Elements**: Inline keyboards, callback queries, and custom reply keyboards
- **File Handling**: Media download, processing, and forwarding capabilities

## Configuration Management
- **Environment Variables**: 
  - `BOT_TOKEN` (required): Telegram bot authentication token
  - `ADMIN_CODE` (optional): Admin verification code (default: "1234")
  - `ADMIN_CHAT_ID` (optional): Admin chat identifier for notifications
- **Static Configuration**: Employee roster in config.py with chat ID mapping
- **Runtime Configuration**: Automatic database and directory initialization
- **Dynamic Employee Management**: Real-time employee addition to config.py with immediate system updates

## Recent Changes (August 2025)

### Production Deployment Fixes (August 4, 2025)
- **Deployment Type Change**: Fixed Autoscale (GCE) deployment issues by adding HTTP health check server
- **Run Command Fix**: Created production-ready `start.py` script with explicit file specification
- **Enhanced Error Handling**: Added comprehensive error recovery and logging for production environments
- **Health Check System**: Implemented HTTP endpoint on port 8080 for Cloud Run compatibility
- **Container Support**: Added Dockerfile and Cloud Run deployment configuration
- **Deployment Documentation**: Created comprehensive DEPLOYMENT.md guide with multiple deployment options
- **Auto-restart Mechanism**: Enhanced bot polling with automatic reconnection on network failures

### Enhanced Customer Contact System
- **Phone Number Collection**: Mandatory phone number collection via Telegram contact sharing
- **Location Request**: Required GPS location sharing for all customer inquiries
- **Complete Customer Profile**: Admin receives name, phone, username, location, and timestamp
- **Two-Step Verification**: Phone → Location → Chat activation sequence
- **Enhanced Admin Notifications**: Full customer profile with interactive location data

### Advanced Payment Processing System
- **Three-Way Payment Method**: Complete overhaul of task completion payment system
- **Card Payment Flow**: Karta orqali to'lov with confirmation and transfer status notification
- **Cash Payment Flow**: Naqd pul to'lovi with amount confirmation and receipt acknowledgment
- **Debt Management Flow**: Multi-step debt creation with debtor name, amount, reason, and payment date
- **Detailed Admin Notifications**: Payment method-specific admin alerts with full transaction details
- **Employee Confirmation**: Method-specific success messages with payment status and details

## Recent Changes (August 2025)

### Employee Motivation and Entertainment System
- **Post-Task Motivation**: Random congratulatory messages after task completion with entertainment options
- **Movie Download Feature**: Employees can search and get movie download links after completing tasks
- **Music Streaming System**: Access to latest monthly music and search functionality for specific songs
- **Daily News Integration**: Web scraping for Uzbekistan and world news using trafilatura package
- **Three Entertainment Categories**: Cinema, music, and news with "skip" option
- **Restaurant System Removed**: Dining/restaurant recommendations completely removed from system

### Enhanced Data Management System
- **Complete Ma'lumotlar Section**: Full activation with direct data insertion capabilities
- **Data Overview**: Comprehensive statistics showing tasks, debts, messages, employees, and active sessions
- **Data Manipulation**: Direct data addition and deletion functionality for all system components

### Extended Debt Management
- **Boshqalar Category**: Added support for non-employee debts alongside employee debts
- **Enhanced Debt Creation**: Two-path workflow supporting both staff members and external individuals
- **Improved Error Handling**: Robust session management with comprehensive error recovery

### Dynamic Employee Management
- **Direct Employee Addition**: Admin interface for adding employees with name and Telegram ID
- **Automatic Config Updates**: Real-time updates to config.py with immediate system recognition
- **Employee Notification**: Automatic welcome messages to newly added employees

### Enhanced Task Payment System
- **Optional Payment Amounts**: Tasks can have specific payment amounts or remain unset
- **Clear Payment Status**: Employees receive either payment amount or "payment not set" notification
- **Flexible Payment Workflow**: Admin choice between setting payment or marking as unspecified

### Complete Employee Panel System (August 2025)
- **Task History**: Full 📂 Vazifalar tarixi functionality with detailed completion records
- **Comprehensive Reports**: 📊 Hisobotlar with weekly, monthly, and overall statistics
- **Excel Export**: Text-based detailed reports with task summaries and earnings
- **Performance Analytics**: Task completion rates, earnings tracking, and performance metrics

### Advanced Entertainment System (August 2025)
- **Enhanced Movie Download System**: 🎬 Kino ko'rish with actual downloadable movie files, not just streaming links
- **Download-focused Interface**: Direct movie download options with quality selection (4K, 1080p, 720p, 480p)
- **Multi-platform Download Links**: Telegram bots, Google Drive, Mega.nz, MediaFire integration
- **Sample Movie Integration**: Downloadable demo movies for immediate access
- **Comprehensive Music System**: 🎵 Musiqa tinglash with Uzbek/foreign music collections, genre-based playlists, smart search
- **News System**: 📰 Yangiliklar with web scraping for real-time news from multiple sources
- **Download Guidance System**: Step-by-step download instructions and platform recommendations
- **Cultural Content**: Uzbek artists (Shahzoda, Rayhon) and international hits with detailed descriptions
- **User-friendly Downloads**: Wi-Fi recommendations, file size info, and quality options for optimal user experience

### Technical Improvements
- **Session Management**: Enhanced admin_data dictionary initialization preventing KeyError exceptions
- **Error Recovery**: Comprehensive error handling throughout all conversation flows
- **Data Integrity**: Robust validation and error recovery for all user interactions

## File System Dependencies
- **Local Storage**: Persistent SQLite database and organized file structure
- **Directory Management**: Automatic creation and management of:
  - `reports/` - Excel report storage
  - `media/` - Media file storage (photos, videos, voice)
- **File Operations**: Advanced media processing, Excel generation, and cleanup operations