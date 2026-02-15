# 🚀 TEZKOR ISHGA TUSHIRISH

## 1-QADAM: Fayllarni yuklab oling
✅ main_fixed.py
✅ requirements.txt
✅ README.md
✅ homework_bot.service (ixtiyoriy)

## 2-QADAM: Kutubxonalarni o'rnating
```bash
pip install -r requirements.txt
```

## 3-QADAM: Tesseract OCR o'rnating

### Ubuntu/Debian:
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr tesseract-ocr-uzb tesseract-ocr-eng tesseract-ocr-rus
```

### Windows:
https://github.com/UB-Mannheim/tesseract/wiki dan yuklab oling

### MacOS:
```bash
brew install tesseract tesseract-lang
```

## 4-QADAM: Bot sozlamalarini o'zgartiring

`main_fixed.py` faylini oching va quyidagilarni o'zgartiring:

```python
# 22-qator atrofida:
BOT_TOKEN = '8523430941:AAGtv-UXLK_qDA-83YpdEMW-WZbPvH-RJU0'  # O'zgartiring
CHANNEL_ID = '-1003543686638'  # O'zgartiring
ADMIN_ID = 8517530604  # O'zgartiring
GROQ_API_KEY = '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'  # O'zgartiring
```

**Qanday olish:**
- BOT_TOKEN: @BotFather dan
- CHANNEL_ID: Botni kanalga qo'shing, @userinfobot orqali ID oling
- ADMIN_ID: @userinfobot dan o'z ID ingizni oling
- GROQ_API_KEY: https://console.groq.com dan

## 5-QADAM: Botni ishga tushiring

### Test rejimida:
```bash
python main_fixed.py
```

### Background rejimida (Linux):
```bash
nohup python main_fixed.py > bot.log 2>&1 &
```

### Screen bilan (tavsiya etiladi):
```bash
screen -S homework_bot
python main_fixed.py
# Ctrl+A, D - detach qilish
# screen -r homework_bot - qayta ulash
```

### Systemd service (eng yaxshi):
```bash
# homework_bot.service faylini tahrirlang:
# - YOUR_USERNAME ni o'z username ingizga o'zgartiring
# - /path/to/bot ni to'g'ri yo'lga o'zgartiring

# Service faylini nusxalash:
sudo cp homework_bot.service /etc/systemd/system/

# Ishga tushirish:
sudo systemctl daemon-reload
sudo systemctl enable homework_bot
sudo systemctl start homework_bot

# Holatni tekshirish:
sudo systemctl status homework_bot

# Loglarni ko'rish:
sudo journalctl -u homework_bot -f
```

## 6-QADAM: Botni tekshirish

1. Telegram da botni toping
2. /start bosing
3. Ro'yxatdan o'ting
4. Test vazifa yuboring

## 🔍 MONITORING

### Loglarni kuzatish:
```bash
tail -f bot.log
```

### Xatolarni topish:
```bash
grep "ERROR" bot.log | tail -20
```

### Bot ishlab turganini tekshirish:
```bash
ps aux | grep main_fixed.py
```

### Bot ni to'xtatish:
```bash
# Screen bilan:
screen -r homework_bot
# Ctrl+C

# Systemd bilan:
sudo systemctl stop homework_bot

# Process ID bilan:
kill $(ps aux | grep 'main_fixed.py' | grep -v grep | awk '{print $2}')
```

### Bot ni qayta ishga tushirish:
```bash
# Systemd:
sudo systemctl restart homework_bot

# Yoki oddiy:
killall python3
nohup python3 main_fixed.py > bot.log 2>&1 &
```

## ⚠️ MUAMMOLAR VA YECHIMLAR

### "Bot token is invalid"
- BOT_TOKEN to'g'ri kiritilganini tekshiring
- @BotFather dan yangi token oling

### "Chat not found" (CHANNEL_ID)
- Botni kanalga admin qilib qo'shing
- Channel ID to'g'ri yozilganini tekshiring (minus bilan: -1001234567890)

### "Tesseract is not installed"
- 3-qadamni qayta bajaring
- `tesseract --version` bilan tekshiring

### Database xatolari
```bash
# Backup va qayta yaratish:
mv students.db students.db.backup
python main_fixed.py
```

### Memory to'lib ketsa
- Systemd service faylida MemoryLimit ni oshiring
- Yoki botni restart qiling

### Connection errors
- Internet aloqani tekshiring
- Bot avtomatik qayta urinadi, kuting

## 📞 YORDAM

Boshqa muammolar yoki savollar:
1. README.md ni to'liq o'qing
2. Loglarni tekshiring: `tail -100 bot.log`
3. Google da qidiring
4. GitHub Issues ochim

## ✅ TAYYOR!

Bot ishga tushdi va barcha xatolarni avtomatik tuzatadi. 
Hostingda ishlash uchun Systemd service variantini tanlang.

Omad! 🎉
