# Overview

This is an Enhanced Telegram Task Management Bot built in Python that facilitates comprehensive task assignment and tracking between administrators and employees. The bot provides a complete workflow for creating tasks, assigning them to specific employees, tracking completion status with media attachments, and generating detailed reports. It includes advanced features like location sharing, real-time employee tracking, Excel-based reporting, debt management (including "Boshqalar" category), media file handling (photos, videos, voice), direct employee management, comprehensive data management capabilities, and multi-step task completion workflows. The system is designed for small to medium-sized teams requiring sophisticated work assignment management through Telegram with professional reporting capabilities.

# User Preferences

Preferred communication style: Simple, everyday language.

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
- **Complete Movie System**: 🎬 Kino ko'rish with 10+ popular movies, real streaming links, genre-based recommendations
- **Comprehensive Music System**: 🎵 Musiqa tinglash with Uzbek/foreign music collections, genre-based playlists, smart search
- **News System**: 📰 Yangiliklar with web scraping for real-time news from multiple sources
- **Real Platform Integration**: Netflix, Spotify, YouTube Music, Apple Music, Amazon Prime links
- **Cultural Content**: Uzbek artists (Shahzoda, Rayhon) and international hits with detailed descriptions
- **Streamlined Design**: Restaurant system removed for simplified entertainment experience

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