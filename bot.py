#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
بوت تيليجرام لتنزيل الفيديوهات من TikTok وInstagram وFacebook.
يتحقق من اشتراك المستخدم في القناة المطلوبة قبل السماح بالاستخدام.
يدعم الاستخدام في الدردشة الخاصة والمجموعات، ويقوم بتخزين المستخدمين في قاعدة بيانات SQLite.
"""

import telebot
from telebot import types
from telebot.apihelper import ApiTelegramException
import sqlite3
import re
import os
from datetime import datetime

# بيانات التكوين
BOT_TOKEN = "7737032600:AAGdNbC1xMFo6rTUIXX_oe287zdQPlHLck4"
FORCE_CHANNEL = "@M_H_O_D7"
OWNER_ID = 5401358805
DEVELOPER_USERNAME = "@VENOM_L99"

# تهيئة البوت وقاعدة البيانات
bot = telebot.TeleBot(BOT_TOKEN)
conn = sqlite3.connect("users.db", check_same_thread=False)
cur = conn.cursor()
cur.execute("""CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    full_name TEXT,
    join_date TEXT
)""")
conn.commit()

def add_user_to_db(user):
    if user is None:
        return
    user_id = user.id
    username = user.username or ""
    full_name = user.first_name or ""
    if getattr(user, 'last_name', None):
        full_name += " " + user.last_name
    join_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        cur.execute("INSERT OR IGNORE INTO users (user_id, username, full_name, join_date) VALUES (?, ?, ?, ?)",
                    (user_id, username, full_name, join_date))
        conn.commit()
    except Exception as e:
        print("DB Error:", e)

def is_user_subscribed(user_id):
    try:
        bot.get_chat_member(FORCE_CHANNEL, user_id)
        return True
    except ApiTelegramException:
        return False
    except Exception:
        return False

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    user = message.from_user
    chat_id = message.chat.id
    if message.chat.type != "private":
        try:
            bot.send_message(user.id, "📩 يُرجى مراسلتي في الخاص لبدء استخدام البوت.")
        except:
            bot.reply_to(message, "⚠️ يرجى بدء المحادثة مع البوت في الخاص أولاً.")
        return
    if not is_user_subscribed(user.id):
        markup = types.InlineKeyboardMarkup()
        btn = types.InlineKeyboardButton("📢 اشترك في القناة", url=f"https://t.me/{FORCE_CHANNEL.replace('@', '')}")
        markup.add(btn)
        bot.send_message(chat_id, f"عذرًا {user.first_name}، يجب عليك الاشتراك في قناة الدعم أولًا.\n"
                                  f"🔸 القناة: {FORCE_CHANNEL}\n"
                                  "بعد الاشتراك اضغط /start مرة أخرى.", reply_markup=markup)
        return
    add_user_to_db(user)
    welcome_text = (f"مرحبًا {user.first_name}! ✨\n"
                    "أرسل رابط أي فيديو من TikTok أو Instagram أو Facebook وسأقوم بتحميله لك.\n"
                    "ℹ️ بدون علامات مائية.\n"
                    f"⚙️ المطوّر: {DEVELOPER_USERNAME}")
    bot.send_message(chat_id, welcome_text)

@bot.message_handler(func=lambda message: message.content_type == 'text' and 
                    ("tiktok.com" in message.text.lower() or "instagram.com" in message.text.lower() 
                     or "facebook.com" in message.text.lower() or "fb.watch" in message.text.lower()))
def handle_video_link(message):
    user = message.from_user
    chat_id = message.chat.id
    text = message.text.strip()
    if not is_user_subscribed(user.id):
        try:
            bot.send_message(user.id, f"⚠️ عذرًا، يجب الاشتراك في القناة {FORCE_CHANNEL} أولًا.")
        except:
            bot.reply_to(message, f"⚠️ يرجى الاشتراك في القناة {FORCE_CHANNEL} لاستخدام البوت.")
        return
    add_user_to_db(user)
    url_match = re.search(r'(https?://(?:[\w\-]+\.)?(?:tiktok\.com|instagram\.com|facebook\.com|fb\.watch)[^\s]+)', text)
    video_url = url_match.group(1) if url_match else None
    if not video_url:
        bot.reply_to(message, "❗ لم أتعرف على رابط صالح. أرسل رابط مباشر لفيديو.")
        return
    notice_msg = bot.reply_to(message, "⏳ جاري تنزيل الفيديو...")
    ydl_opts = {
        "format": "best[ext=mp4]+bestaudio/best[ext=mp4]/best",
        "quiet": True,
        "outtmpl": "video.%(ext)s",
        "no_warnings": True
    }
    success = False
    video_file = None
    try:
        import yt_dlp
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            video_file = ydl.prepare_filename(info)
        success = True
    except Exception as e:
        print("Download error:", e)
        bot.edit_message_text("❌ حدث خطأ أثناء التنزيل. تحقق من الرابط وحاول مجددًا.", chat_id, notice_msg.message_id)
    if success and video_file and os.path.isfile(video_file):
        try:
            with open(video_file, "rb") as video:
                bot.send_video(chat_id, video, reply_to_message_id=message.message_id)
        except Exception as e:
            print("Send video failed, trying document:", e)
            try:
                with open(video_file, "rb") as video:
                    bot.send_document(chat_id, video, caption="📹 الفيديو المطلوب", reply_to_message_id=message.message_id)
            except Exception as e:
                print("Sending failed:", e)
                bot.edit_message_text("❌ تعذر إرسال الفيديو.", chat_id, notice_msg.message_id)
        finally:
            os.remove(video_file)
            try:
                bot.edit_message_text("✅ تم الإرسال بنجاح.", chat_id, notice_msg.message_id)
            except:
                pass

@bot.message_handler(func=lambda m: m.chat.type == "private" and m.from_user.id == OWNER_ID and 
                    (m.text.startswith("/broadcast") or m.text.startswith("/sendtoall")))
def broadcast_message(message):
    if message.from_user.id != OWNER_ID:
        return
    try:
        broadcast_text = message.text.split(' ', 1)[1]
    except IndexError:
        bot.send_message(message.chat.id, "❗ اكتب نص الرسالة بعد الأمر.")
        return
    cur.execute("SELECT user_id FROM users")
    rows = cur.fetchall()
    sent_count = 0
    removed_count = 0
    for (uid,) in rows:
        try:
            bot.send_message(uid, broadcast_text)
            sent_count += 1
        except ApiTelegramException as e:
            if e.result_json.get('description', '').startswith("Forbidden"):
                cur.execute("DELETE FROM users WHERE user_id=?", (uid,))
                conn.commit()
                removed_count += 1
        except Exception as e:
            print(f"فشل الإرسال إلى {uid}: {e}")
    bot.send_message(message.chat.id, f"✔️ أُرسلت إلى {sent_count} مستخدم.\n🗑️ تم حذف {removed_count} من قاعدة البيانات.")

@bot.message_handler(func=lambda m: m.chat.type == "private" and m.from_user.id == OWNER_ID and m.text == "/stats")
def send_stats(message):
    if message.from_user.id != OWNER_ID:
        return
    cur.execute("SELECT COUNT(*) FROM users")
    count = cur.fetchone()[0]
    bot.reply_to(message, f"👥 عدد المستخدمين المسجلين: {count}")

# تشغيل البوت
print("Bot is running...")
bot.infinity_polling(timeout=60, long_polling_timeout=60)
