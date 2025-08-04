# Overview

This is an Enhanced Telegram Task Management Bot built in Python that facilitates comprehensive task assignment and tracking between administrators and employees. The bot provides a complete workflow for creating tasks, assigning them to specific employees, tracking completion status with media attachments, and generating detailed reports. It includes advanced features like location sharing, real-time employee tracking, Excel-based reporting, debt management, media file handling (photos, videos, voice), and multi-step task completion workflows. The system is designed for small to medium-sized teams requiring sophisticated work assignment management through Telegram with professional reporting capabilities.

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
- **Task Management**: Complete lifecycle tracking (pending → in_progress → completed)
- **Media Integration**: Full support for task completion with photo/video proof and voice reports
- **Location Services**: GPS location sharing for task assignments and employee tracking
- **Reporting System**: Professional Excel generation with multi-sheet reports and statistics
- **Debt Management**: Integrated debt tracking with task completion workflows
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

## File System Dependencies
- **Local Storage**: Persistent SQLite database and organized file structure
- **Directory Management**: Automatic creation and management of:
  - `reports/` - Excel report storage
  - `media/` - Media file storage (photos, videos, voice)
- **File Operations**: Advanced media processing, Excel generation, and cleanup operations