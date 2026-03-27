import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import yt_dlp
import os
import subprocess
from keep_alive import keep_alive 
import static_ffmpeg
static_ffmpeg.add_paths()

TOKEN = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)

# قاموس لتخزين روابط الفيديوهات عشان لما المستخدم يطلب ترجمتها بعدين
video_cache = {}

def get_required_channels():
    channels = []
    for i in range(1, 11):
        ch = os.environ.get(f'CHANNEL_{i}')
        if ch:
            ch = ch.strip()
            if not ch.startswith('@'):
                ch = '@' + ch
            channels.append(ch)
    return channels

def get_unsubscribed_channels(user_id):
    channels = get_required_channels()
    unsubscribed = []
    for channel in channels:
        try:
            status = bot.get_chat_member(channel, user_id).status
            if status not in ['member', 'administrator', 'creator']:
                unsubscribed.append(channel)
        except Exception as e:
            print(f"Error checking sub for {channel}: {e}")
            unsubscribed.append(channel) 
    return unsubscribed

def get_sub_keyboard(unsub_channels):
    markup = InlineKeyboardMarkup()
    for i, ch in enumerate(unsub_channels):
        ch_username = ch.replace('@', '')
        btn = InlineKeyboardButton(text=f"📢 اشترك في القناة {i+1}", url=f"https://t.me/{ch_username}")
        markup.add(btn)
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    if message.chat.type != 'private':
        return
        
    unsub = get_unsubscribed_channels(message.from_user.id)
    if unsub:
        markup = get_sub_keyboard(unsub)
        bot.reply_to(message, "عذراً عزيزي ✋\nيجب عليك الاشتراك في قنوات البوت أولاً لتتمكن من استخدامه.\n\n👇 اضغط على الأزرار بالأسفل للاشتراك:", reply_markup=markup)
        return
        
    bot.reply_to(message, "أهلاً بك! أرسل لي أي رابط وسأقوم بتحميله لك.")

@bot.message_handler(func=lambda message: message.chat.type == 'private' and ('http://' in message.text or 'https://' in message.text))
def download_video(message):
    unsub = get_unsubscribed_channels(message.from_user.id)
    if unsub:
        markup = get_sub_keyboard(unsub)
        bot.reply_to(message, "عذراً عزيزي ✋\nيجب الاشتراك أولاً.", reply_markup=markup)
        return

    url = message.text
    msg = bot.reply_to(message, "جاري معالجة الرابط والتحميل، يرجى الانتظار قليلاً... ⏳")
    
    ydl_opts = {
        'outtmpl': 'downloaded_video.%(ext)s',
        'format': 'best[ext=mp4]/best'
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        for file in os.listdir('.'):
            if file.startswith('downloaded_video'):
                # عمل زرار الترجمة
                markup = InlineKeyboardMarkup()
                trans_btn = InlineKeyboardButton(text="ترجمة الفيديو 🌍", callback_data="trans_menu")
                markup.add(trans_btn)
                
                with open(file, 'rb') as video:
                    sent_msg = bot.send_video(message.chat.id, video, reply_markup=markup)
                    # حفظ الرابط في الذاكرة عشان لو طلب ترجمته
                    video_cache[sent_msg.message_id] = url
                
                os.remove(file)
                bot.delete_message(message.chat.id, msg.message_id)
                break
                
    except Exception as e:
        bot.reply_to(message, f"حدث خطأ أثناء التحميل:\n\n{str(e)}")

# التعامل مع ضغطات الأزرار (الترجمة واختيار اللغة)
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    # لو ضغط على زرار ترجمة الفيديو الرئيسي
    if call.data == "trans_menu":
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("العربية 🇪🇬", callback_data="lang_ar"),
            InlineKeyboardButton("English 🇺🇸", callback_data="lang_en")
        )
        markup.add(
            InlineKeyboardButton("Español 🇪🇸", callback_data="lang_es"),
            InlineKeyboardButton("Français 🇫🇷", callback_data="lang_fr")
        )
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=markup)

    # لو اختار لغة معينة
    elif call.data.startswith("lang_"):
        target_lang = call.data.split("_")[1]
        url = video_cache.get(call.message.message_id)
        
        if not url:
            bot.answer_callback_query(call.id, "عذراً، الرابط قديم. يرجى إرسال الفيديو من جديد.", show_alert=True)
            return

        bot.answer_callback_query(call.id, "جاري تجهيز الترجمة... ⏳")
        bot.send_message(call.message.chat.id, "جاري سحب الصوت ودمج الترجمة، قد يستغرق هذا دقيقة... ⚙️")

        # هنا البوت بينزل الفيديو تاني عشان يدمج عليه الترجمة
        ydl_opts = {'outtmpl': 'temp_vid.%(ext)s', 'format': 'best[ext=mp4]/best'}
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            # 1. إنشاء ملف ترجمة تجريبي (لحين ربطه بالذكاء الاصطناعي)
            srt_content = """1
00:00:01,000 --> 00:00:07,000
تمت الترجمة بنجاح بواسطة @MyVidDownloader_bot!
"""
            with open("subtitles.srt", "w", encoding="utf-8") as f:
                f.write(srt_content)
            
            # 2. دمج الترجمة على الفيديو باستخدام FFmpeg
            subprocess.run(['ffmpeg', '-i', 'temp_vid.mp4', '-vf', 'subtitles=subtitles.srt', 'final_video.mp4', '-y'])
            
            # 3. إرسال الفيديو المترجم
            with open('final_video.mp4', 'rb') as translated_vid:
                bot.send_video(call.message.chat.id, translated_vid, caption=f"✅ تم دمج الترجمة بنجاح!")
            
            # تنظيف السيرفر من الملفات المؤقتة
            os.remove('temp_vid.mp4')
            os.remove('final_video.mp4')
            os.remove('subtitles.srt')
            
        except Exception as e:
            bot.send_message(call.message.chat.id, f"حدث خطأ أثناء الترجمة: {e}")

keep_alive()
print("البوت يعمل الآن ومستعد للترجمة...")
bot.infinity_polling()
