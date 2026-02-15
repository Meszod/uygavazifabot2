import telebot
from telebot import types
import sqlite3
from datetime import datetime, date, timedelta
import logging
import traceback
import time
import requests
import json
import html
import telebot.apihelper
from PIL import Image
import pytesseract
import io
from difflib import SequenceMatcher
import os
import sys

# ==================== LOGGING SOZLAMALARI ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==================== SQLITE ADAPTER/CONVERTER ====================
def adapt_datetime(dt):
    return dt.isoformat()

def adapt_date(dt):
    return dt.isoformat()

def convert_datetime(s):
    try:
        return datetime.fromisoformat(s.decode('utf-8')) if s else None
    except (ValueError, AttributeError):
        return None

def convert_date(s):
    try:
        return date.fromisoformat(s.decode('utf-8')) if s else None
    except (ValueError, AttributeError):
        return None

sqlite3.register_adapter(datetime, adapt_datetime)
sqlite3.register_adapter(date, adapt_date)
sqlite3.register_converter("TIMESTAMP", convert_datetime)
sqlite3.register_converter("DATE", convert_date)

# ==================== BOT KONFIGURATSIYASI ====================
BOT_TOKEN = '8523430941:AAGtv-UXLK_qDA-83YpdEMW-WZbPvH-RJU0'
CHANNEL_ID = '-1003543686638'

# ADMINLAR RO'YXATI - qo'shimcha admin ID larini qo'shing
ADMIN_IDS = [
    8517530604,  # Asosiy admin
    # 123456789,  # Qo'shimcha admin 1 (izohdagi # ni olib tashlang)
    # 987654321,  # Qo'shimcha admin 2
]

DB_NAME = 'students.db'
GROQ_API_KEY = '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'
GROQ_API_URL = 'https://api.groq.com/openai/v1/chat/completions'

# Yordamchi funksiya - admin tekshirish
def is_admin(user_id):
    """Foydalanuvchi admin ekanligini tekshirish"""
    return user_id in ADMIN_IDS

# ==================== GLOBAL O'ZGARUVCHILAR ====================
active_contest = None
user_states = {}
bot = None  # Global bot o'zgaruvchisi

# ==================== XAVFSIZ FUNKSIYALAR ====================
def safe_execute(func, *args, max_retries=3, default_return=None, **kwargs):
    """Har qanday funksiyani xavfsiz bajarish"""
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except telebot.apihelper.ApiTelegramException as e:
            error_msg = str(e).lower()
            # Ignore ediladigan xatolar
            if any(x in error_msg for x in ['query is too old', 'timeout', 'invalid', 'blocked', 'chat not found']):
                logger.warning(f"⚠️ Ignored Telegram error: {e}")
                return default_return
            
            if attempt == max_retries - 1:
                logger.error(f"❌ {func.__name__} failed after {max_retries} attempts: {e}")
                return default_return
            
            wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
            logger.warning(f"⚠️ {func.__name__} attempt {attempt + 1} failed, retrying in {wait_time}s...")
            time.sleep(wait_time)
            
        except (ConnectionError, ConnectionResetError, requests.exceptions.ConnectionError) as e:
            logger.warning(f"⚠️ Connection error in {func.__name__}: {e}")
            if attempt == max_retries - 1:
                return default_return
            time.sleep(2 ** attempt)
            
        except Exception as e:
            logger.error(f"❌ Unexpected error in {func.__name__}: {e}")
            logger.error(traceback.format_exc())
            if attempt == max_retries - 1:
                return default_return
            time.sleep(1)
    
    return default_return

def safe_send_message(chat_id, text, **kwargs):
    """Xavfsiz xabar yuborish"""
    return safe_execute(bot.send_message, chat_id, text, **kwargs)

def safe_send_document(chat_id, document, **kwargs):
    """Xavfsiz fayl yuborish"""
    return safe_execute(bot.send_document, chat_id, document, **kwargs)

def safe_send_photo(chat_id, photo, **kwargs):
    """Xavfsiz rasm yuborish"""
    return safe_execute(bot.send_photo, chat_id, photo, **kwargs)

def safe_edit_message_text(text, chat_id, message_id, **kwargs):
    """Xavfsiz xabar tahrirlash"""
    return safe_execute(bot.edit_message_text, text, chat_id, message_id, **kwargs)

def safe_answer_callback_query(callback_query_id, text="", show_alert=False, **kwargs):
    """Xavfsiz callback javob berish"""
    return safe_execute(bot.answer_callback_query, callback_query_id, text=text, show_alert=show_alert, **kwargs)

def escape_html(text):
    """HTML xavfsizligi"""
    if text is None:
        return ""
    text = str(text)
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    text = text.replace('"', '&quot;')
    text = text.replace("'", "'")
    return text

# ==================== DATABASE FUNKSIYALARI ====================
def get_db_connection():
    """Xavfsiz database connection"""
    try:
        conn = sqlite3.connect(
            DB_NAME, 
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
            timeout=10,
            check_same_thread=False
        )
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        logger.error(f"❌ DB connection error: {e}")
        return None

def safe_db_execute(query, params=(), fetch_one=False, fetch_all=False, commit=False):
    """Xavfsiz database operatsiyalari"""
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            return None
        
        cursor = conn.cursor()
        cursor.execute(query, params)
        
        result = None
        if fetch_one:
            result = cursor.fetchone()
        elif fetch_all:
            result = cursor.fetchall()
        elif commit:
            conn.commit()
            result = cursor.lastrowid if 'INSERT' in query.upper() else True
        
        return result
    except sqlite3.OperationalError as e:
        logger.error(f"❌ SQL error: {e} | Query: {query[:100]}")
        return None
    except Exception as e:
        logger.error(f"❌ DB execute error: {e}")
        return None
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass

def init_db():
    """Database yaratish"""
    try:
        conn = get_db_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        
        # Students jadvali
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS students (
                user_id INTEGER PRIMARY KEY,
                full_name TEXT NOT NULL,
                username TEXT,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER DEFAULT 1
            )
        ''')
        
        # Assignments jadvali
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                homework_text TEXT NOT NULL,
                assignment_date DATE NOT NULL DEFAULT (date('now')),
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER DEFAULT 1
            )
        ''')
        
        # Submissions jadvali
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                full_name TEXT NOT NULL,
                homework_text TEXT,
                homework_file TEXT,
                file_type TEXT,
                assignment_id INTEGER,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'pending',
                reviewed_at TIMESTAMP,
                reviewer_id INTEGER,
                ai_check_result TEXT,
                ai_checked_at TIMESTAMP,
                rejection_reason TEXT,
                FOREIGN KEY (user_id) REFERENCES students (user_id),
                FOREIGN KEY (assignment_id) REFERENCES assignments (id)
            )
        ''')
        
        # Statistics jadvali
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS statistics (
                date TEXT PRIMARY KEY,
                total_submissions INTEGER DEFAULT 0,
                approved_submissions INTEGER DEFAULT 0,
                rejected_submissions INTEGER DEFAULT 0
            )
        ''')
        
        # Contests jadvali
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS contests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                problem_text TEXT NOT NULL,
                correct_answer TEXT NOT NULL,
                deadline TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER DEFAULT 1
            )
        ''')
        
        # Contest submissions jadvali
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS contest_submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contest_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                full_name TEXT NOT NULL,
                answer TEXT NOT NULL,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_correct INTEGER DEFAULT 0,
                rank_position INTEGER,
                FOREIGN KEY (contest_id) REFERENCES contests(id),
                FOREIGN KEY (user_id) REFERENCES students(user_id)
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("✅ Database muvaffaqiyatli yaratildi")
        return True
    except Exception as e:
        logger.error(f"❌ Database init error: {e}")
        return False

# ==================== YORDAMCHI FUNKSIYALAR ====================
def clear_user_state(user_id):
    """Foydalanuvchi holatini tozalash"""
    if user_id in user_states:
        del user_states[user_id]

def is_registered(user_id):
    """Ro'yxatdan o'tganligini tekshirish"""
    result = safe_db_execute(
        'SELECT user_id FROM students WHERE user_id = ? AND is_active = 1',
        (user_id,),
        fetch_one=True
    )
    return result is not None

def get_student_info(user_id):
    """O'quvchi ma'lumotlari"""
    result = safe_db_execute(
        'SELECT * FROM students WHERE user_id = ?',
        (user_id,),
        fetch_one=True
    )
    return dict(result) if result else None

def get_all_students():
    """Barcha o'quvchilar"""
    results = safe_db_execute(
        'SELECT * FROM students WHERE is_active = 1 ORDER BY registered_at DESC',
        fetch_all=True
    )
    return [dict(row) for row in results] if results else []

def get_current_assignment():
    """Joriy uyga vazifa"""
    today = date.today().strftime('%Y-%m-%d')
    result = safe_db_execute(
        'SELECT * FROM assignments WHERE assignment_date = ? AND is_active = 1 ORDER BY sent_at DESC LIMIT 1',
        (today,),
        fetch_one=True
    )
    return result

def get_retry_count(user_id, assignment_id):
    """Qayta topshirish soni"""
    result = safe_db_execute(
        'SELECT COUNT(*) as count FROM submissions WHERE user_id = ? AND assignment_id = ?',
        (user_id, assignment_id),
        fetch_one=True
    )
    return result['count'] if result else 0

def update_statistics(status):
    """Statistika yangilash"""
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Bugungi statistika mavjudligini tekshirish
    exists = safe_db_execute(
        'SELECT date FROM statistics WHERE date = ?',
        (today,),
        fetch_one=True
    )
    
    if not exists:
        safe_db_execute(
            'INSERT INTO statistics (date, total_submissions, approved_submissions, rejected_submissions) VALUES (?, 1, 0, 0)',
            (today,),
            commit=True
        )
    
    # Statistika yangilash
    if status == 'approved':
        safe_db_execute(
            'UPDATE statistics SET approved_submissions = approved_submissions + 1 WHERE date = ?',
            (today,),
            commit=True
        )
    elif status == 'rejected':
        safe_db_execute(
            'UPDATE statistics SET rejected_submissions = rejected_submissions + 1 WHERE date = ?',
            (today,),
            commit=True
        )

# ==================== KLAVIATURALAR ====================
def get_main_keyboard():
    """O'quvchi klaviaturasi"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton('📝 Uyga vazifa topshirish'),
        types.KeyboardButton('📊 Statistika'),
        types.KeyboardButton('✍️ Javob yuborish'),
        types.KeyboardButton('🏆 Reyting'),
        types.KeyboardButton('❓ Yordam')
    )
    return markup

def get_admin_keyboard():
    """Admin klaviaturasi"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton('📤 Uyga vazifa yuborish'),
        types.KeyboardButton('📊 Statistika'),
        types.KeyboardButton('🏆 IT Misol'),
        types.KeyboardButton('🏆 Reyting'),
        types.KeyboardButton('📥 Excel'),
        types.KeyboardButton('👨‍💼 Admin panel'),
        types.KeyboardButton('❓ Yordam')
    )
    return markup

# ==================== OCR VA AI ====================
def extract_text_from_image(file_id):
    """OCR - rasmdan matn o'qish"""
    try:
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        image = Image.open(io.BytesIO(downloaded_file))
        text = pytesseract.image_to_string(image, lang='uzb+eng+rus')
        logger.info(f"✅ OCR: {len(text)} belgi")
        return text.strip()
    except Exception as e:
        logger.error(f"❌ OCR error: {e}")
        return None

def check_homework_with_ai(homework_text, student_name, submission_id):
    """AI tekshiruv (Groq)"""
    try:
        assignment = get_current_assignment()
        if not assignment:
            return {'status': 'error', 'message': "❌ Joriy vazifa topilmadi"}
        
        assignment_text = assignment[1]
        
        # O'xshash vazifalarni tekshirish
        duplicates = safe_db_execute(
            'SELECT full_name FROM submissions WHERE homework_text = ? AND full_name != ? AND status != "rejected" LIMIT 5',
            (homework_text, student_name),
            fetch_all=True
        )
        
        duplicate_msg = ""
        if duplicates:
            duplicate_msg = "⚠️ DIQQAT! O'xshash vazifalar topildi:\n"
            for dup in duplicates:
                duplicate_msg += f"• {escape_html(dup['full_name'])}\n"
            duplicate_msg += "\n"
        
        # Groq API chaqiruv
        prompt = f"""Siz uyga vazifa tekshiruvchisiz. Quyidagi o'quvchi javobini standart vazifaga nisbatan tekshiring:

Standart vazifa:
{assignment_text}

O'quvchi: {student_name}
Javob:
{homework_text}

Tekshiring:
1. Grammatika (xatolar ko'rsating)
2. Mazmun mosligi (0-100% foiz)
3. Tuzilish va tartib
4. Umumiy baho (70% dan past bo'lsa rad eting)

Format (HTML yo'q, oddiy matn):
✅/❌ Baho: [Qabul/Rad] (70% dan past rad)
📊 To'g'rilik: [0-100]%
📝 Tahlil:
- Grammatika: [xatolar]
- Mazmun: [baholash]
- Tuzilish: [baholash]
💡 Tavsiyalar: [qisqa]"""

        headers = {
            'Authorization': f'Bearer {GROQ_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': 'llama-3.3-70b-versatile',
            'messages': [
                {'role': 'system', 'content': 'Professional o\'qituvchi. Qattiq tekshiring, foiz bilan baholang, konstruktiv fikr bering. HTML yo\'q.'},
                {'role': 'user', 'content': prompt}
            ],
            'temperature': 0.7,
            'max_tokens': 1000
        }
        
        response = requests.post(GROQ_API_URL, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            ai_response = result['choices'][0]['message']['content']
            
            # AI javobni saqlash
            safe_db_execute(
                'UPDATE submissions SET ai_check_result = ?, ai_checked_at = ? WHERE id = ?',
                (ai_response, datetime.now(), submission_id),
                commit=True
            )
            
            full_response = f"{duplicate_msg}{ai_response}\n\n🤖 <i>AI: Groq Llama 3.3 70B</i>"
            return {'status': 'success', 'message': full_response}
        else:
            logger.error(f"❌ AI API error: {response.status_code}")
            return {'status': 'error', 'message': f"❌ AI xatolik: {response.status_code}"}
    
    except Exception as e:
        logger.error(f"❌ AI check error: {e}")
        return {'status': 'error', 'message': f"❌ Xatolik: {str(e)}"}

# ==================== BROADCAST ====================
def broadcast_assignment(assignment_text, assignment_id, assignment_date):
    """Barcha o'quvchilarga yuborish"""
    students = get_all_students()
    sent_count = 0
    
    for student in students:
        if not is_admin(student['user_id']):
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add(types.KeyboardButton('📝 Ushbu vazifani topshirish'))
            
            success = safe_send_message(
                student['user_id'],
                f"📚 <b>Yangi uyga vazifa! ({assignment_date})</b>\n\n"
                f"{escape_html(assignment_text)}\n\n"
                f"🔢 ID: #{assignment_id}\n\n"
                f"📝 'Ushbu vazifani topshirish' tugmasini bosing.",
                parse_mode='HTML',
                reply_markup=markup
            )
            if success:
                sent_count += 1
    
    logger.info(f"✅ Broadcast: {sent_count} ta o'quvchiga")
    return sent_count

# ==================== BOT HANDLERS ====================
def register_handlers(bot_instance):
    """Barcha handlerlarni ro'yxatdan o'tkazish"""
    global bot
    bot = bot_instance
    
    # /start
    @bot.message_handler(commands=['start'])
    def start(message):
        user_id = message.from_user.id
        first_name = message.from_user.first_name or "Noma'lum"
        last_name = message.from_user.last_name or ""
        username = message.from_user.username
        
        logger.info(f"▶️ /start - User: {user_id}")
        
        # Admin auto-register
        if is_admin(user_id):
            if not is_registered(user_id):
                full_name = f"{first_name} {last_name}".strip()
                safe_db_execute(
                    'INSERT OR REPLACE INTO students (user_id, full_name, username, registered_at) VALUES (?, ?, ?, ?)',
                    (user_id, full_name, username, datetime.now()),
                    commit=True
                )
            
            student = get_student_info(user_id)
            safe_send_message(
                message.chat.id,
                f"🎓 Salom, Admin {student['full_name']}! 👨‍💼\n\nQuyidagi bo'limlardan birini tanlang:",
                reply_markup=get_admin_keyboard()
            )
            return
        
        # Oddiy foydalanuvchi
        student = get_student_info(user_id)
        if student:
            safe_send_message(
                message.chat.id,
                f"🎓 Salom, {student['full_name']}!\n\nQuyidagi bo'limlardan birini tanlang:",
                reply_markup=get_main_keyboard()
            )
        else:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add(types.KeyboardButton('✅ Ro\'yxatdan o\'tish'))
            safe_send_message(
                message.chat.id,
                "👋 Assalomu alaykum!\n\nBotdan foydalanish uchun avval ro'yxatdan o'ting.\n\n"
                "📝 Ism va familiyangizni to'liq kiriting\n(Masalan: Muhammad Aliyev)",
                reply_markup=markup
            )
    
    # Yordam
    @bot.message_handler(func=lambda m: m.text == '❓ Yordam')
    def help_command(message):
        user_id = message.from_user.id
        
        if is_admin(user_id):
            help_text = """👨‍💼 <b>Admin Panel - Yordam</b>

📤 <b>Uyga vazifa yuborish:</b> Barcha o'quvchilarga vazifa yuborish
🏆 <b>IT Misol:</b> Musobaqa yaratish (5-60 daqiqa)
📊 <b>Statistika:</b> Kunlik va umumiy hisobot
📥 <b>Excel:</b> Ma'lumotlarni yuklab olish
👨‍💼 <b>Admin panel:</b> O'quvchilar, statistika, tozalash
🤖 <b>AI tekshiruv:</b> Avtomatik grammatika va mazmun tahlili"""
        else:
            help_text = """📚 <b>Bot haqida</b>

📝 <b>Qanday foydalanish:</b>
1️⃣ Ro'yxatdan o'ting
2️⃣ Vazifani topshiring (matn/rasm/fayl)
3️⃣ AI tekshiradi (foiz bilan)
4️⃣ O'qituvchi tasdiqlaydi

🤖 <b>AI:</b> Grammatika, o'xshashlik, foiz baholash
🏆 <b>Contest:</b> Tez yechish musobaqalari
🔔 <b>Bildirishnoma:</b> Natija bo'yicha xabar
📊 <b>Statistika:</b> Shaxsiy natijalaringiz"""
        
        safe_send_message(message.chat.id, help_text, parse_mode='HTML')
    
    # Ro'yxatdan o'tish
    @bot.message_handler(func=lambda m: m.text in ['✅ Ro\'yxatdan o\'tish', 'Ro\'yxatdan o\'tish'])
    def register_start(message):
        user_id = message.from_user.id
        
        if is_admin(user_id) or is_registered(user_id):
            safe_send_message(message.chat.id, "✅ Siz allaqachon ro'yxatdan o'tgansiz!")
            return
        
        user_states[user_id] = 'registering_name'
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton('❌ Bekor qilish'))
        safe_send_message(
            message.chat.id,
            "✍️ Ism va familiyangizni to'liq kiriting:\n\nMasalan: Muhammad Aliyev (10 harfdan ko'p)",
            reply_markup=markup
        )
    
    @bot.message_handler(func=lambda m: m.from_user.id in user_states and user_states[m.from_user.id] == 'registering_name')
    def register_complete(message):
        user_id = message.from_user.id
        full_name = message.text.strip()
        username = message.from_user.username
        
        if full_name == '❌ Bekor qilish':
            clear_user_state(user_id)
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add(types.KeyboardButton('✅ Ro\'yxatdan o\'tish'))
            safe_send_message(message.chat.id, "❌ Bekor qilindi.", reply_markup=markup)
            return
        
        if len(full_name) < 10:
            safe_send_message(message.chat.id, "❌ Juda qisqa. 10 harfdan ko'p bo'lishi kerak.")
            return
        
        safe_db_execute(
            'INSERT OR REPLACE INTO students (user_id, full_name, username, registered_at) VALUES (?, ?, ?, ?)',
            (user_id, full_name, username, datetime.now()),
            commit=True
        )
        
        clear_user_state(user_id)
        safe_send_message(
            message.chat.id,
            f"✅ Ro'yxatdan muvaffaqiyatli o'tdingiz!\n\n👤 Ism: {full_name}\n"
            f"📅 Sana: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
            f"Endi uyga vazifalaringizni topshirishingiz mumkin! 📚",
            reply_markup=get_main_keyboard()
        )
        logger.info(f"✅ Ro'yxat: {full_name} (ID: {user_id})")
    
    # Statistika
    @bot.message_handler(func=lambda m: m.text in ['📊 Statistika', 'Statistika'])
    def show_statistics(message):
        user_id = message.from_user.id
        
        if not is_registered(user_id):
            safe_send_message(message.chat.id, "❌ Avval ro'yxatdan o'ting!")
            return
        
        student = get_student_info(user_id)
        
        # Individual statistika (TUZATILGAN SQL)
        total_result = safe_db_execute(
            'SELECT COUNT(*) as count FROM submissions WHERE user_id = ?',
            (user_id,),
            fetch_one=True
        )
        total = total_result['count'] if total_result else 0
        
        approved_result = safe_db_execute(
            'SELECT COUNT(*) as count FROM submissions WHERE user_id = ? AND status = "approved"',
            (user_id,),
            fetch_one=True
        )
        approved = approved_result['count'] if approved_result else 0
        
        rejected_result = safe_db_execute(
            'SELECT COUNT(*) as count FROM submissions WHERE user_id = ? AND status = "rejected"',
            (user_id,),
            fetch_one=True
        )
        rejected = rejected_result['count'] if rejected_result else 0
        
        # Bugungi statistika
        today = datetime.now().strftime('%Y-%m-%d')
        today_stats = safe_db_execute(
            'SELECT total_submissions, approved_submissions, rejected_submissions FROM statistics WHERE date = ?',
            (today,),
            fetch_one=True
        )
        
        stats_text = f"📊 <b>{student['full_name']} - Statistika</b>\n\n"
        stats_text += f"📈 Umumiy: {total}\n"
        stats_text += f"✅ Tasdiqlangan: {approved}\n"
        stats_text += f"❌ Rad etilgan: {rejected}\n\n"
        
        if today_stats:
            stats_text += f"📅 Bugun:\n"
            stats_text += f"• Topshirilgan: {today_stats['total_submissions'] or 0}\n"
            stats_text += f"• Tasdiqlangan: {today_stats['approved_submissions'] or 0}\n"
            stats_text += f"• Rad etilgan: {today_stats['rejected_submissions'] or 0}\n"
        else:
            stats_text += "📅 Bugun: Hech narsa yo'q\n"
        
        if total > 0:
            success_rate = (approved / total) * 100
            stats_text += f"\n📈 Muvaffaqiyat: {success_rate:.1f}%"
        
        safe_send_message(message.chat.id, stats_text, parse_mode='HTML')
    
    # Broadcast - Admin
    @bot.message_handler(func=lambda m: m.text == '📤 Uyga vazifa yuborish' and is_admin(m.from_user.id))
    def broadcast_start(message):
        user_id = message.from_user.id
        user_states[user_id] = 'broadcasting_homework'
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton('❌ Bekor qilish'))
        safe_send_message(
            message.chat.id,
            "📤 Yangi uyga vazifani kiriting (matn sifatida):\n\n"
            "Yuborganingizdan keyin barcha o'quvchilarga yuboriladi.",
            reply_markup=markup
        )
    
    @bot.message_handler(func=lambda m: m.from_user.id in user_states and user_states[m.from_user.id] == 'broadcasting_homework')
    def broadcast_complete(message):
        user_id = message.from_user.id
        assignment_text = message.text.strip()
        
        if assignment_text == '❌ Bekor qilish':
            clear_user_state(user_id)
            safe_send_message(message.chat.id, "❌ Broadcast bekor qilindi.", reply_markup=get_admin_keyboard())
            return
        
        if len(assignment_text) < 10:
            safe_send_message(message.chat.id, "❌ Juda qisqa. Batafsilroq kiriting.")
            return
        
        today = date.today().strftime('%Y-%m-%d')
        
        # Vazifani saqlash
        assignment_id = safe_db_execute(
            'INSERT INTO assignments (homework_text, assignment_date) VALUES (?, ?)',
            (assignment_text, today),
            commit=True
        )
        
        if not assignment_id:
            safe_send_message(message.chat.id, "❌ Saqlashda xatolik!")
            return
        
        # Oldingi vazifalarni deaktiv qilish
        safe_db_execute(
            'UPDATE assignments SET is_active = 0 WHERE assignment_date = ? AND id != ?',
            (today, assignment_id),
            commit=True
        )
        
        # Broadcast
        sent_count = broadcast_assignment(assignment_text, assignment_id, today)
        
        clear_user_state(user_id)
        safe_send_message(
            message.chat.id,
            f"✅ Broadcast muvaffaqiyatli!\n\n📝 Vazifa: {assignment_text[:50]}...\n"
            f"🔢 ID: #{assignment_id}\n📅 Sana: {today}\n📢 Yuborildi: {sent_count} ta o'quvchi",
            reply_markup=get_admin_keyboard()
        )
        
        # Kanalga xabar
        safe_send_message(
            CHANNEL_ID,
            f"📚 <b>Yangi vazifa ({today})</b>\n\n📝 {escape_html(assignment_text)}\n"
            f"🔢 ID: #{assignment_id}\n📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            parse_mode='HTML'
        )
    
    # Homework submission
    @bot.message_handler(func=lambda m: m.text in ['📝 Ushbu vazifani topshirish', '📝 Uyga vazifa topshirish'])
    def submit_homework_start(message):
        user_id = message.from_user.id
        
        if not is_registered(user_id):
            safe_send_message(message.chat.id, "❌ Avval ro'yxatdan o'ting!")
            return
        
        current_assignment = get_current_assignment()
        if not current_assignment:
            safe_send_message(message.chat.id, "❌ Hozircha yangi vazifa yo'q!")
            return
        
        retry_count = get_retry_count(user_id, current_assignment[0])
        if retry_count >= 3:
            safe_send_message(message.chat.id, f"❌ Maksimal 3 marta topshirish mumkin! Siz {retry_count} marta topshirdingiz.")
            return
        
        user_states[user_id] = 'submitting_homework'
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton('❌ Bekor qilish'))
        
        retry_msg = f"\n🔄 Topshirish: {retry_count + 1}/3" if retry_count > 0 else ""
        safe_send_message(
            message.chat.id,
            f"📤 Joriy vazifa ({current_assignment[2]}):\n\n{escape_html(current_assignment[1])}\n\n"
            f"📝 Vazifangizni yuboring:\n• 📄 Matn\n• 🖼 Rasm (OCR)\n• 📎 Fayl\n• 🎥 Video\n• 🎵 Audio\n\n"
            f"🤖 AI foiz bilan tekshiradi!{retry_msg}\n🔢 ID: #{current_assignment[0]}",
            parse_mode='HTML',
            reply_markup=markup
        )
    
    @bot.message_handler(content_types=['text', 'document', 'photo', 'video', 'audio', 'voice'],
                         func=lambda m: m.from_user.id in user_states and user_states[m.from_user.id] == 'submitting_homework')
    def receive_homework(message):
        user_id = message.from_user.id
        
        if not is_registered(user_id):
            safe_send_message(message.chat.id, "❌ Avval ro'yxatdan o'ting!")
            return
        
        # Bekor qilish
        if message.text and message.text.strip() == '❌ Bekor qilish':
            clear_user_state(user_id)
            safe_send_message(message.chat.id, "❌ Bekor qilindi.", reply_markup=get_main_keyboard())
            return
        
        student = get_student_info(user_id)
        current_assignment = get_current_assignment()
        
        if not current_assignment:
            safe_send_message(message.chat.id, "❌ Joriy vazifa topilmadi!")
            return
        
        assignment_id = current_assignment[0]
        retry_count = get_retry_count(user_id, assignment_id)
        
        if retry_count >= 3:
            safe_send_message(message.chat.id, "❌ Maksimal limit!")
            return
        
        # Fayl turini aniqlash
        homework_text = message.text if message.text else None
        homework_file = None
        file_type = None
        
        if message.document:
            homework_file = message.document.file_id
            file_type = 'document'
            homework_text = "📎 Fayl yuborildi"
        elif message.photo:
            homework_file = message.photo[-1].file_id
            file_type = 'photo'
            extracted_text = extract_text_from_image(homework_file)
            homework_text = extracted_text if extracted_text else "🖼 Rasm (OCR muvaffaqiyatsiz)"
        elif message.video:
            homework_file = message.video.file_id
            file_type = 'video'
            homework_text = "🎥 Video yuborildi"
        elif message.audio:
            homework_file = message.audio.file_id
            file_type = 'audio'
            homework_text = "🎵 Audio yuborildi"
        elif message.voice:
            homework_file = message.voice.file_id
            file_type = 'voice'
            homework_text = "🎤 Voice yuborildi"
        
        if not homework_text or not homework_text.strip():
            safe_send_message(message.chat.id, "❌ Hech narsa yuborilmadi!")
            return
        
        # Database ga saqlash
        submission_id = safe_db_execute(
            'INSERT INTO submissions (user_id, full_name, homework_text, homework_file, file_type, assignment_id, submitted_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (user_id, student['full_name'], homework_text, homework_file, file_type, assignment_id, datetime.now()),
            commit=True
        )
        
        if not submission_id:
            safe_send_message(message.chat.id, "❌ Saqlashda xatolik!")
            return
        
        # Statistika
        today = datetime.now().strftime('%Y-%m-%d')
        safe_db_execute(
            'INSERT OR IGNORE INTO statistics (date, total_submissions) VALUES (?, 0)',
            (today,),
            commit=True
        )
        safe_db_execute(
            'UPDATE statistics SET total_submissions = total_submissions + 1 WHERE date = ?',
            (today,),
            commit=True
        )
        
        # Kanalga yuborish
        retry_msg = f"\n🔄 Topshirish: {retry_count + 1}/3" if retry_count > 0 else ""
        post_text = f"""📚 <b>Yangi topshiriq</b>
👤 O'quvchi: {escape_html(student['full_name'])}
🆔 User ID: <code>{user_id}</code>
📅 Sana: {datetime.now().strftime('%d.%m.%Y %H:%M')}
📝 Vazifa (#{assignment_id}):
{escape_html(homework_text[:500])}{'...' if len(homework_text) > 500 else ''}
🔢 ID: #{submission_id}{retry_msg}"""
        
        # Inline tugmalar
        markup = types.InlineKeyboardMarkup(row_width=2)
        btn_approve = types.InlineKeyboardButton('✅ Tasdiqlash', callback_data=f'approve_{submission_id}')
        btn_reject = types.InlineKeyboardButton('❌ Rad (izoh)', callback_data=f'reject_with_reason_{submission_id}')
        btn_ai = types.InlineKeyboardButton('🤖 AI tekshirish', callback_data=f'ai_check_{submission_id}')
        
        if file_type == 'photo':
            btn_ai_ocr = types.InlineKeyboardButton('🤖 OCR+AI', callback_data=f'ai_check_ocr_{submission_id}')
            markup.add(btn_approve, btn_reject)
            markup.add(btn_ai, btn_ai_ocr)
        else:
            markup.add(btn_approve, btn_reject)
            markup.add(btn_ai)
        
        # Kanalga media bilan yuborish
        if homework_file:
            if file_type == 'document':
                safe_send_document(CHANNEL_ID, homework_file, caption=post_text, reply_markup=markup, parse_mode='HTML')
            elif file_type == 'photo':
                safe_send_photo(CHANNEL_ID, homework_file, caption=post_text, reply_markup=markup, parse_mode='HTML')
            elif file_type == 'video':
                safe_execute(bot.send_video, CHANNEL_ID, homework_file, caption=post_text, reply_markup=markup, parse_mode='HTML')
            elif file_type == 'audio':
                safe_execute(bot.send_audio, CHANNEL_ID, homework_file, caption=post_text, reply_markup=markup, parse_mode='HTML')
            elif file_type == 'voice':
                safe_execute(bot.send_voice, CHANNEL_ID, homework_file, caption=post_text, reply_markup=markup, parse_mode='HTML')
        else:
            safe_send_message(CHANNEL_ID, post_text, reply_markup=markup, parse_mode='HTML')
        
        clear_user_state(user_id)
        safe_send_message(
            message.chat.id,
            f"✅ Vazifangiz yuborildi!\n\n🤖 AI tekshiruvi mavjud\n"
            f"📢 O'qituvchi tasdiqlashini kuting.{retry_msg}\n🔢 ID: #{submission_id} (Assignment #{assignment_id})",
            reply_markup=get_main_keyboard()
        )
    
    # Inline callback handlers
    @bot.callback_query_handler(func=lambda call: call.data.startswith(('approve_', 'reject_with_reason_', 'ai_check_')))
    def handle_inline_buttons(call):
        user_id = call.from_user.id
        
        if not is_admin(user_id):
            safe_answer_callback_query(call.id, "❌ Ruxsat yo'q!", show_alert=True)
            return
        
        data = call.data
        submission_id = int(data.split('_')[-1])
        
        submission = safe_db_execute(
            'SELECT * FROM submissions WHERE id = ?',
            (submission_id,),
            fetch_one=True
        )
        
        if not submission:
            safe_answer_callback_query(call.id, "❌ Topilmadi!", show_alert=True)
            return
        
        status = submission['status']
        if status != 'pending':
            safe_answer_callback_query(call.id, f"❌ Allaqachon: {status}", show_alert=True)
            return
        
        # AI tekshiruv
        if data.startswith('ai_check_') and not data.startswith('ai_check_ocr_'):
            safe_answer_callback_query(call.id, "🤖 AI tekshiruv...")
            
            ai_result = check_homework_with_ai(submission['homework_text'], submission['full_name'], submission_id)
            
            if ai_result['status'] == 'success':
                new_text = f"{call.message.text}\n\n{ai_result['message']}"
                safe_edit_message_text(new_text, call.message.chat.id, call.message.message_id, parse_mode='HTML', disable_web_page_preview=True)
            else:
                safe_send_message(call.message.chat.id, ai_result['message'])
            
            # Tugmalarni yangilash
            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(
                types.InlineKeyboardButton('✅ Tasdiqlash', callback_data=f'approve_{submission_id}'),
                types.InlineKeyboardButton('❌ Rad (izoh)', callback_data=f'reject_with_reason_{submission_id}')
            )
            safe_execute(bot.edit_message_reply_markup, call.message.chat.id, call.message.message_id, reply_markup=markup)
        
        # OCR + AI
        elif data.startswith('ai_check_ocr_'):
            if submission['file_type'] != 'photo':
                safe_answer_callback_query(call.id, "❌ Faqat rasm uchun!", show_alert=True)
                return
            
            safe_answer_callback_query(call.id, "🤖 OCR + AI...")
            extracted_text = extract_text_from_image(submission['homework_file'])
            
            if extracted_text:
                ai_result = check_homework_with_ai(extracted_text, submission['full_name'], submission_id)
                if ai_result['status'] == 'success':
                    new_text = f"{call.message.text}\n\n📄 <b>OCR:</b>\n{escape_html(extracted_text[:200])}...\n\n{ai_result['message']}"
                    safe_edit_message_text(new_text, call.message.chat.id, call.message.message_id, parse_mode='HTML', disable_web_page_preview=True)
            else:
                safe_send_message(call.message.chat.id, "❌ OCR muvaffaqiyatsiz!")
            
            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(
                types.InlineKeyboardButton('✅ Tasdiqlash', callback_data=f'approve_{submission_id}'),
                types.InlineKeyboardButton('❌ Rad (izoh)', callback_data=f'reject_with_reason_{submission_id}')
            )
            safe_execute(bot.edit_message_reply_markup, call.message.chat.id, call.message.message_id, reply_markup=markup)
        
        # Tasdiqlash
        elif data.startswith('approve_'):
            safe_db_execute(
                'UPDATE submissions SET status = "approved", reviewed_at = ?, reviewer_id = ? WHERE id = ?',
                (datetime.now(), user_id, submission_id),
                commit=True
            )
            
            update_statistics('approved')
            
            new_text = f"{call.message.text}\n\n✅ <b>Tasdiqlandi!</b> 👨‍💼 Admin: {escape_html(call.from_user.first_name)}"
            safe_edit_message_text(new_text, call.message.chat.id, call.message.message_id, parse_mode='HTML')
            
            # O'quvchiga xabar
            safe_send_message(
                submission['user_id'],
                f"🎉 Tabriklaymiz, {submission['full_name']}!\n\n✅ Vazifangiz tasdiqlandi!\n"
                f"📅 Sana: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n🔢 ID: #{submission_id}"
            )
            
            safe_answer_callback_query(call.id, "✅ Tasdiqlandi!")
        
        # Rad etish (izoh so'rash)
        elif data.startswith('reject_with_reason_'):
            user_states[user_id] = f'rejecting_reason_{submission_id}'
            safe_answer_callback_query(call.id, "✍️ Sabab yozing...")
            
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add(types.KeyboardButton('❌ Bekor qilish'))
            
            safe_send_message(
                call.message.chat.id,
                f"📝 <b>Rad etish sababini yozing:</b>\n\nO'quvchi: {submission['full_name']}\n"
                f"ID: #{submission_id}\n\nBu izoh o'quvchiga yuboriladi.",
                parse_mode='HTML',
                reply_markup=markup
            )
    
    # Rad etish sababi
    @bot.message_handler(func=lambda m: m.from_user.id in user_states and user_states[m.from_user.id].startswith('rejecting_reason_'))
    def save_rejection_reason(message):
        user_id = message.from_user.id
        submission_id = int(user_states[user_id].split('_')[-1])
        reason = message.text.strip()
        
        if reason == '❌ Bekor qilish':
            clear_user_state(user_id)
            safe_send_message(message.chat.id, "❌ Bekor qilindi.", reply_markup=get_admin_keyboard())
            return
        
        if len(reason) < 5:
            safe_send_message(message.chat.id, "❌ Juda qisqa. Batafsilroq yozing.")
            return
        
        # Rad etish
        safe_db_execute(
            'UPDATE submissions SET status = "rejected", reviewed_at = ?, reviewer_id = ?, rejection_reason = ? WHERE id = ?',
            (datetime.now(), user_id, reason, submission_id),
            commit=True
        )
        
        submission = safe_db_execute(
            'SELECT user_id, full_name FROM submissions WHERE id = ?',
            (submission_id,),
            fetch_one=True
        )
        
        update_statistics('rejected')
        
        # O'quvchiga xabar
        if submission:
            safe_send_message(
                submission['user_id'],
                f"😔 Kechirasiz, {submission['full_name']}!\n\n❌ Vazifangiz rad etildi.\n"
                f"📝 <b>Sabab:</b> {escape_html(reason)}\n\n🔢 ID: #{submission_id}\n"
                f"📅 Sana: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
                f"🔄 Qayta topshirishingiz mumkin (maksimal 3 marta)!",
                parse_mode='HTML'
            )
        
        clear_user_state(user_id)
        safe_send_message(
            message.chat.id,
            f"✅ Rad etildi va xabar yuborildi!\n\n👤 O'quvchi: {submission['full_name'] if submission else 'Noma\'lum'}\n"
            f"🔢 ID: #{submission_id}\n📝 Sabab: {reason[:50]}...",
            reply_markup=get_admin_keyboard()
        )
    
    # Bekor qilish - universal handler
    @bot.message_handler(func=lambda m: m.text == '❌ Bekor qilish')
    def handle_cancel(message):
        user_id = message.from_user.id
        clear_user_state(user_id)
        
        keyboard = get_admin_keyboard() if is_admin(user_id) else get_main_keyboard()
        safe_send_message(message.chat.id, "❌ Operatsiya bekor qilindi.", reply_markup=keyboard)
    
    logger.info("✅ Barcha handlerlar ro'yxatdan o'tdi")

# ==================== BOT ISHGA TUSHIRISH ====================
def start_bot():
    """Botni ishga tushirish"""
    global bot
    
    logger.info("🚀 Bot ishga tushmoqda...")
    
    # Database init
    if not init_db():
        logger.critical("❌ Database yaratish muvaffaqiyatsiz!")
        return False
    
    # Bot instance yaratish
    bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)
    
    # Handlerlarni ro'yxatdan o'tkazish
    register_handlers(bot)
    
    logger.info("✅ Bot tayyor, polling boshlandi...")
    
    # Infinity polling with error recovery
    while True:
        try:
            bot.infinity_polling(
                timeout=30,
                long_polling_timeout=60,
                allowed_updates=["message", "callback_query"],
                skip_pending=True  # Eski xabarlarni skip qilish
            )
        except KeyboardInterrupt:
            logger.info("⏹ Bot to'xtatildi (KeyboardInterrupt)")
            break
        except Exception as e:
            logger.error(f"❌ Polling xato: {e}")
            logger.error(traceback.format_exc())
            logger.info("🔄 5 soniyadan keyin qayta uriniladi...")
            time.sleep(5)
            # Bot instance ni qayta yaratish
            bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)
            register_handlers(bot)
    
    return True

# ==================== MAIN ====================
if __name__ == '__main__':
    try:
        start_bot()
    except Exception as e:
        logger.critical(f"❌ Fatal error: {e}")
        logger.critical(traceback.format_exc())
        sys.exit(1)
