#!/usr/bin/env python3
"""
Website Integration API for Customer Inquiries
Provides API endpoints for website to submit customer requests
"""

from flask import Flask, request, jsonify
import json
import os
from datetime import datetime
from database import add_customer_inquiry, init_database
from config import ADMIN_CHAT_ID
import telebot

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "website_api_secret_key")

# Initialize bot for notifications
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
if BOT_TOKEN:
    bot = telebot.TeleBot(BOT_TOKEN)
else:
    bot = None

@app.route('/api/submit_inquiry', methods=['POST'])
def submit_inquiry():
    """API endpoint for website to submit customer inquiries"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data or 'customer_name' not in data or 'inquiry_text' not in data:
            return jsonify({
                'success': False,
                'error': 'customer_name va inquiry_text majburiy maydonlar'
            }), 400
        
        # Extract data
        customer_name = data.get('customer_name', '').strip()
        inquiry_text = data.get('inquiry_text', '').strip()
        customer_phone = data.get('customer_phone', '').strip() or None
        customer_email = data.get('customer_email', '').strip() or None
        location_address = data.get('location_address', '').strip() or None
        
        # Validate data
        if len(customer_name) < 2:
            return jsonify({
                'success': False,
                'error': 'Mijoz ismi kamida 2 ta belgidan iborat bo\'lishi kerak'
            }), 400
        
        if len(inquiry_text) < 10:
            return jsonify({
                'success': False,
                'error': 'So\'rov matni kamida 10 ta belgidan iborat bo\'lishi kerak'
            }), 400
        
        # Add inquiry to database
        inquiry_id = add_customer_inquiry(
            customer_name=customer_name,
            customer_phone=customer_phone,
            customer_username=customer_email,  # Using email field for username
            chat_id=None,  # No chat ID for website inquiries
            inquiry_text=inquiry_text,
            location_address=location_address,
            inquiry_type='website_request',
            source='website'
        )
        
        # Send notification to admin
        if bot and ADMIN_CHAT_ID:
            try:
                admin_message = f"""
🌐 **YANGI WEBSITE SO'ROVI**

📋 So'rov ID: #{inquiry_id}
👤 Mijoz: {customer_name}
📞 Telefon: {customer_phone or 'Kiritilmagan'}
📧 Email: {customer_email or 'Kiritilmagan'}
📍 Manzil: {location_address or 'Kiritilmagan'}

💬 **So'rov:**
{inquiry_text}

📅 Vaqt: {datetime.now().strftime('%Y-%m-%d %H:%M')}
🌐 Manba: Website

💡 Javob berish: 👥 Mijozlar so'rovlari → 🌐 Website dan kelgan so'rovlar
"""
                bot.send_message(ADMIN_CHAT_ID, admin_message)
            except Exception as e:
                print(f"Admin notification error: {e}")
        
        return jsonify({
            'success': True,
            'inquiry_id': inquiry_id,
            'message': 'So\'rovingiz muvaffaqiyatli qabul qilindi! Tez orada javob beramiz.'
        })
        
    except Exception as e:
        print(f"API Error: {e}")
        return jsonify({
            'success': False,
            'error': 'Server xatosi yuz berdi. Iltimos, qayta urinib ko\'ring.'
        }), 500

@app.route('/api/inquiry_status/<int:inquiry_id>', methods=['GET'])
def get_inquiry_status(inquiry_id):
    """Get inquiry status by ID"""
    try:
        from database import get_inquiry_by_id
        
        inquiry = get_inquiry_by_id(inquiry_id)
        
        if not inquiry:
            return jsonify({
                'success': False,
                'error': 'So\'rov topilmadi'
            }), 404
        
        inquiry_id, customer_name, customer_phone, customer_username, chat_id, inquiry_text, inquiry_type, location_lat, location_lon, location_address, status, admin_response, created_at, responded_at, source = inquiry
        
        return jsonify({
            'success': True,
            'inquiry': {
                'id': inquiry_id,
                'customer_name': customer_name,
                'status': status,
                'created_at': created_at,
                'admin_response': admin_response,
                'responded_at': responded_at
            }
        })
        
    except Exception as e:
        print(f"Status API Error: {e}")
        return jsonify({
            'success': False,
            'error': 'Server xatosi'
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/', methods=['GET'])
def home():
    """Home page with API documentation"""
    return """
<!DOCTYPE html>
<html>
<head>
    <title>Customer Inquiry API</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .endpoint { background: #f5f5f5; padding: 15px; margin: 10px 0; border-radius: 5px; }
        .method { background: #007bff; color: white; padding: 5px 10px; border-radius: 3px; }
        code { background: #e9ecef; padding: 2px 5px; border-radius: 3px; }
    </style>
</head>
<body>
    <h1>🌐 Customer Inquiry API</h1>
    <p>Bu API website dan mijozlar so'rovlarini qabul qilish uchun mo'ljallangan.</p>
    
    <div class="endpoint">
        <h3><span class="method">POST</span> /api/submit_inquiry</h3>
        <p>Yangi mijoz so'rovini yuborish</p>
        <h4>Request Body (JSON):</h4>
        <pre><code>{
  "customer_name": "Ism Familiya",
  "customer_phone": "+998901234567",
  "customer_email": "email@example.com",
  "inquiry_text": "So'rov matni...",
  "location_address": "Manzil (ixtiyoriy)"
}</code></pre>
    </div>
    
    <div class="endpoint">
        <h3><span class="method">GET</span> /api/inquiry_status/{inquiry_id}</h3>
        <p>So'rov holatini tekshirish</p>
    </div>
    
    <div class="endpoint">
        <h3><span class="method">GET</span> /api/health</h3>
        <p>API holati</p>
    </div>
    
    <h3>📞 Telegram Bot Komandalar:</h3>
    <ul>
        <li><code>/contact</code> - Mijozlar uchun so'rov yuborish</li>
        <li><code>/sorov</code> - So'rov yuborish (alternativ)</li>
        <li><code>/murojaat</code> - Murojaat qilish</li>
    </ul>
</body>
</html>
"""

if __name__ == '__main__':
    # Initialize database
    init_database()
    
    # Run Flask app
    port = int(os.environ.get('PORT', 8081))
    app.run(host='0.0.0.0', port=port, debug=False)