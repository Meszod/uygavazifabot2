# 🤖 Uyga Vazifa Bot - Barqaror Versiya

## ✨ Asosiy O'zgarishlar

### 🛡️ Xavfsizlik va Barqarorlik
- ✅ **Avtomatik xato tuzatish** - barcha xatolar avtomatik qayta uriniladi
- ✅ **Connection errors** - aloqa uzilsa avtomatik qayta ulanadi
- ✅ **SQL xatolari** - to'g'rilangan va xavfsiz SQL so'rovlar
- ✅ **Callback timeout** - eski callbacklar ignore qilinadi
- ✅ **Exponential backoff** - zararli retry strategiyasi
- ✅ **Skip pending** - eski xabarlar skip qilinadi
- ✅ **Safe execution** - har bir API chaqiruv xavfsiz

### 🔧 Tuzatilgan Muammolar
1. **ConnectionResetError** - avtomatik retry va backoff
2. **SQLite aggregate xatosi** - to'g'rilangan COUNT() so'rovlar
3. **Callback query timeout** - ignore qilinadi, crash yo'q
4. **Database lock** - timeout va safe connection
5. **API rate limit** - exponential backoff strategiyasi

## 📦 O'rnatish

### 1. Kerakli kutubxonalar
```bash
pip install pyTelegramBotAPI pillow pytesseract requests openpyxl
```

### 2. Tesseract OCR (rasmdan matn o'qish uchun)

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr tesseract-ocr-uzb tesseract-ocr-eng tesseract-ocr-rus
```

**Windows:**
- [Tesseract installer](https://github.com/UB-Mannheim/tesseract/wiki) dan yuklab oling
- `pytesseract.pytesseract.tesseract_cmd` yo'lini sozlang

**MacOS:**
```bash
brew install tesseract tesseract-lang
```

### 3. Bot sozlamalari
`main_fixed.py` faylida quyidagilarni o'zgartiring:
```python
BOT_TOKEN = 'YOUR_BOT_TOKEN'
CHANNEL_ID = 'YOUR_CHANNEL_ID'
ADMIN_ID = YOUR_ADMIN_USER_ID
GROQ_API_KEY = 'YOUR_GROQ_API_KEY'
```

## 🚀 Ishga Tushirish

### Local (Test uchun)
```bash
python main_fixed.py
```

### Hostingda (Production)

#### 1. PythonAnywhere
```bash
# Files bo'limida main_fixed.py yuklang
# Consoles > Bash
pip install --user pyTelegramBotAPI pillow pytesseract requests openpyxl
python main_fixed.py
```

#### 2. Heroku
```bash
# Procfile yarating:
worker: python main_fixed.py

# requirements.txt:
pyTelegramBotAPI
pillow
pytesseract
requests
openpyxl

# Deploy:
git push heroku main
```

#### 3. VPS (Ubuntu)
```bash
# Screen sessiyasida ishga tushirish
sudo apt-get install screen
screen -S homework_bot
python3 main_fixed.py
# Ctrl+A, D - detach
# screen -r homework_bot - qayta ulash
```

#### 4. Systemd Service (avtomatik restart)
`/etc/systemd/system/homework_bot.service` yarating:
```ini
[Unit]
Description=Homework Bot
After=network.target

[Service]
Type=simple
User=yourusername
WorkingDirectory=/path/to/bot
ExecStart=/usr/bin/python3 /path/to/bot/main_fixed.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Ishga tushirish:
```bash
sudo systemctl daemon-reload
sudo systemctl enable homework_bot
sudo systemctl start homework_bot
sudo systemctl status homework_bot
```

## 🔍 Monitoring

### Log fayllarini kuzatish
```bash
tail -f bot.log
```

### Xatolarni tekshirish
```bash
grep "ERROR" bot.log
grep "CRITICAL" bot.log
```

### Bot holatini tekshirish
```bash
# Systemd service
sudo systemctl status homework_bot

# Process
ps aux | grep main_fixed.py
```

## 🛠️ Muammolarni Hal Qilish

### Bot ishlamayapti
1. Loglarni tekshiring: `tail -100 bot.log`
2. Internet aloqasini tekshiring
3. Token to'g'riligini tekshiring
4. Database faylini tekshiring: `ls -la students.db`

### Database xatolari
```bash
# Database ni qayta yaratish (ehtiyotkorlik bilan!)
mv students.db students.db.backup
python main_fixed.py  # Yangi DB yaratiladi
```

### Memory to'lib ketsa
```bash
# Bot ni restart qilish
sudo systemctl restart homework_bot

# Yoki
killall python3
python3 main_fixed.py
```

### OCR ishlamayapti
```bash
# Tesseract o'rnatilganligini tekshirish
tesseract --version

# Til paketlarini tekshirish
tesseract --list-langs
```

## 📊 Xususiyatlar

### ✅ Mavjud Funksiyalar
- 📝 Uyga vazifa topshirish (matn, rasm, fayl, video, audio)
- 🤖 AI tekshiruv (Groq Llama 3.3 70B)
- 🖼️ OCR - rasmdan matn o'qish
- 🏆 IT misol musobaqasi
- 📊 Statistika (individual va umumiy)
- 📥 Excel export
- 👨‍💼 Admin panel
- 🔔 Avtomatik bildirishnomalar

### 🛡️ Xavfsizlik Xususiyatlari
- ✅ SQL injection himoyasi
- ✅ HTML injection himoyasi
- ✅ Rate limiting (API)
- ✅ Error recovery
- ✅ Safe database operations
- ✅ Timeout handling

## 📝 Yangilanish Jurnali

### v2.0 (2026-02-15)
- ✅ To'liq xato tuzatish sistemasi
- ✅ Avtomatik recovery
- ✅ Safe execution wrapper
- ✅ Exponential backoff
- ✅ SQL xatolarini tuzatish
- ✅ Callback timeout handling
- ✅ Skip pending messages
- ✅ Connection error recovery

### v1.0 (2026-02-14)
- ✅ Asosiy funksiyalar
- ✅ AI tekshiruv
- ✅ Contest tizimi
- ✅ Statistika

## 🆘 Yordam

Muammolar yoki savollar bo'lsa:
1. Loglarni tekshiring
2. README ni qayta o'qing
3. GitHub Issues ochim
4. Telegram: @your_username

## 📄 Litsenziya
MIT License

## 🙏 Minnatdorchilik
- pyTelegramBotAPI
- Groq AI
- Tesseract OCR
