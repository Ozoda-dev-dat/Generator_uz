# 🌐 RENDER.COM DEPLOY QO'LLANMASI

## 🆓 Tekin hosting uchun Render.com sozlamalari

### 📋 RENDER.COM DEPLOY BOSQICHLARI:

#### 1. **Render.com hisobini oching**
- https://render.com ga kiring
- GitHub hisobingiz bilan ro'yxatdan o'ting

#### 2. **New Web Service yarating**
- Dashboard da "New +" tugmasini bosing
- "Web Service" tanlang
- GitHub repository ni ulang

#### 3. **Deploy sozlamalari:**

**Build Command:**
```
pip install flask openpyxl pytelegrambotapi requests trafilatura gunicorn
```

**Start Command:**
```
python start_render.py
```

**Environment:**
- Python 3

#### 4. **Environment Variables qo'shing:**

**Required (majburiy):**
- `BOT_TOKEN` - Sizning Telegram bot token

**Optional (avtomatik):**
- `ADMIN_CHAT_ID` - 7792775986
- `ADMIN_CODE` - 1234
- `PORT` - 10000 (avtomatik)

#### 5. **Advanced Settings:**
- Auto-Deploy: OFF (ixtiyoriy)
- Health Check Path: `/health`

### 🔧 **RENDER UCHUN MAXSUS FAYLLAR:**

✅ **start_render.py** - Render uchun optimallashtirilgan startup script
✅ **render.yaml** - Render konfiguratsiya fayli
✅ **Gunicorn** qo'shildi

### 📊 **RENDER.COM XUSUSIYATLARI:**

**🆓 Free Tier:**
- 750 soat/oy tekin
- Avtomatik sleep (30 daqiqa ishlamaslik)
- 512MB RAM
- Shared CPU

**💳 Paid Plans:**
- $7/oy - doimiy ishlash
- 1GB+ RAM
- Dedicated CPU

### 🚀 **DEPLOY JARAYONI:**

1. Render.com da Web Service yarating
2. GitHub repository ulang
3. Build Command: `pip install flask openpyxl pytelegrambotapi requests trafilatura gunicorn`
4. Start Command: `python start_render.py`
5. BOT_TOKEN environment variable qo'shing
6. Deploy tugmasini bosing

### ⚡ **RENDER VS REPLIT:**

| Xususiyat | Render.com | Replit |
|-----------|------------|--------|
| Tekin vaqt | 750 soat/oy | Development only |
| Sleep | 30 daqiqa | Darhol |
| Pullik plan | $7/oy | $25/oy |
| Setup | Oson | Juda oson |

### 🔍 **MONITORING:**

**Health Check URL:**
```
https://your-app-name.onrender.com/health
```

**Main Page:**
```
https://your-app-name.onrender.com/
```

### 🚨 **TROUBLESHOOTING:**

**Bot ishlamasa:**
1. Logs panelini tekshiring
2. BOT_TOKEN to'g'riligini tasdiqlang
3. Health check endpoint `/health` ga kiring

**Sleep muammosi:**
- Free tier 30 daqiqa ishlamaslik keyin uxlaydi
- Paid plan ($7/oy) doimiy ishlaydi

### 💡 **TAVSIYALAR:**

1. **Free tier** - test va development uchun
2. **Paid plan** - production uchun (24/7 ishlatish)
3. GitHub orqali avtomatik deploy qiling
4. Environment variables ni to'g'ri sozlang

### 📞 **QOLLAB-QUVVATLASH:**

Deploy jarayonida muammo bo'lsa:
- Render logs panelini tekshiring
- Build va runtime loglarni ko'ring
- Environment variables holatini tasdiqlang