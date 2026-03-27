import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import yt_dlp
import os
import subprocess
import time
from keep_alive import keep_alive 
import static_ffmpeg
import assemblyai as aai
from deep_translator import GoogleTranslator

static_ffmpeg.add_paths()

TOKEN = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)

# مفتاح الذكاء الاصطناعي بتاعك
aai.settings.api_key = '574d2294a8cf4590b594b4cae9ad59b5'

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

def translate_srt_text(srt_text, target_lang):
    """نظام الترجمة المكافح: محاولات متعددة لتجنب حظر جوجل وضمان ترجمة كل كلمة"""
    lines = srt_text.split('\n')
    translator = GoogleTranslator(source='auto', target=target_lang)
    
    for i in range(len(lines)):
        line = lines[i].strip()
        if line and not line.isdigit() and '-->' not in line:
            # هنحاول نترجم الجملة 3 مرات لو جوجل رفض
            for attempt in range(3):
                try:
                    translated = translator.translate(line)
                    lines[i] = translated
                    time.sleep(0.3) # نريح جوجل شوية
                    break # لو نجح يخرج من المحاولات ويدخل ع الجملة اللي بعدها
                except Exception as e:
                    time.sleep(1) # لو فشل، يستنى ثانية ويحاول تاني
    return '\n'.join(lines)

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
        'outtmpl': 'downloaded_vid_%(id)s.%(ext)s',
        'format': 'best'
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
        
        markup = InlineKeyboardMarkup()
        trans_btn = InlineKeyboardButton(text="ترجمة الفيديو 🌍", callback_data="trans_menu")
        markup.add(trans_btn)
        
        with open(filename, 'rb') as video:
            sent_msg = bot.send_video(message.chat.id, video, reply_markup=markup)
            video_cache[sent_msg.message_id] = url
        
        os.remove(filename)
        bot.delete_message(message.chat.id, msg.message_id)
                
    except Exception as e:
        bot.reply_to(message, f"حدث خطأ أثناء التحميل:\n\n{str(e)}")

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
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

    elif call.data.startswith("lang_"):
        target_lang = call.data.split("_")[1]
        url = video_cache.get(call.message.message_id)
        
        if not url:
            bot.answer_callback_query(call.id, "عذراً، الرابط قديم. يرجى إرسال الفيديو من جديد.", show_alert=True)
            return

        bot.answer_callback_query(call.id, "بدأنا العمل... ⏳")
        status_msg = bot.send_message(call.message.chat.id, "1️⃣ جاري تحميل الفيديو لاستخراج الصوت... ⚙️")

        ydl_opts = {
            'outtmpl': 'temp_vid_%(id)s.%(ext)s',
            'format': 'best'
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                vid_filename = ydl.prepare_filename(info)
            
            bot.edit_message_text("2️⃣ جاري الاستماع للفيديو وتفريغ الصوت (الذكاء الاصطناعي يعمل)... 🧠", call.message.chat.id, status_msg.message_id)
            
            subprocess.run(['ffmpeg', '-i', vid_filename, '-q:a', '0', '-map', 'a', 'temp_audio.mp3', '-y'])
            
            config = aai.TranscriptionConfig(
                speech_models=["universal-2"],
                language_detection=True
            )
            
            transcriber = aai.Transcriber(config=config)
            transcript = transcriber.transcribe("temp_audio.mp3")
            
            if transcript.error:
                bot.edit_message_text(f"حدث خطأ في الذكاء الاصطناعي: {transcript.error}", call.message.chat.id, status_msg.message_id)
                return
                
            original_srt = transcript.export_subtitles_srt()
            
            bot.edit_message_text("3️⃣ جاري الترجمة الدقيقة للغة المطلوبة... 🌍", call.message.chat.id, status_msg.message_id)
            
            translated_srt = translate_srt_text(original_srt, target_lang)
            
            with open("translated.srt", "w", encoding="utf-8") as f:
                f.write(translated_srt)
            
            bot.edit_message_text("4️⃣ جاري حقن الترجمة داخل الفيديو بلمح البصر! ⚡", call.message.chat.id, status_msg.message_id)
            
            # الحل الثالث: حقن الترجمة كـ Stream منفصل (Soft Subtitle) سريع جداً ولا يؤثر على جودة الفيديو
            ffmpeg_cmd = [
                'ffmpeg', '-i', vid_filename, '-i', 'translated.srt',
                '-c', 'copy', '-c:s', 'mov_text', 'final_video.mp4', '-y'
            ]
            result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                bot.edit_message_text(f"⚠️ خطأ في برنامج الدمج:\n{result.stderr[-300:]}", call.message.chat.id, status_msg.message_id)
            else:
                with open('final_video.mp4', 'rb') as translated_vid:
                    # هنبعتله الفيديو ونفهمه يشغل الترجمة إزاي
                    bot.send_video(
                        call.message.chat.id, 
                        translated_vid, 
                        caption=f"✅ تمت الترجمة بنجاح بواسطة @MyVidDownloader_bot\n\n💡 *تلميح:* اضغط على زرار (CC) أو (الترجمة) في مشغل الفيديو لتفعيلها."
                    )
                bot.delete_message(call.message.chat.id, status_msg.message_id)
            
            # تنظيف الملفات
            for f_name in [vid_filename, 'temp_audio.mp3', 'final_video.mp4', 'translated.srt']:
                if os.path.exists(f_name):
                    os.remove(f_name)
            
        except Exception as e:
            bot.edit_message_text(f"حدث خطأ غير متوقع: {e}", call.message.chat.id, status_msg.message_id)

keep_alive()
print("البوت جاهز للاستماع والترجمة السريعة!")
bot.infinity_polling()
