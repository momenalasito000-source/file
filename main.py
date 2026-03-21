import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import yt_dlp
import os
from keep_alive import keep_alive 

TOKEN = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)

# دالة بتجيب القنوات وبتتأكد إن فيها علامة @
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

# دالة بتعمل الأزرار الشفافة
def get_sub_keyboard(unsub_channels):
    markup = InlineKeyboardMarkup()
    for i, ch in enumerate(unsub_channels):
        ch_username = ch.replace('@', '')
        btn = InlineKeyboardButton(text=f"📢 اشترك في القناة {i+1}", url=f"https://t.me/{ch_username}")
        markup.add(btn)
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    unsub = get_unsubscribed_channels(message.from_user.id)
    if unsub:
        markup = get_sub_keyboard(unsub)
        bot.reply_to(message, "عذراً عزيزي ✋\nيجب عليك الاشتراك في قنوات البوت أولاً لتتمكن من استخدامه.\n\n👇 اضغط على الأزرار بالأسفل للاشتراك:", reply_markup=markup)
        return
        
    bot.reply_to(message, "أهلاً بك! أرسل لي أي رابط من يوتيوب أو تيك توك وسأقوم بتحميله لك.")

@bot.message_handler(func=lambda message: True)
def download_video(message):
    unsub = get_unsubscribed_channels(message.from_user.id)
    if unsub:
        markup = get_sub_keyboard(unsub)
        bot.reply_to(message, "عذراً عزيزي ✋\nيجب عليك الاشتراك في قنوات البوت أولاً لتتمكن من التحميل.\n\n👇 اضغط على الأزرار بالأسفل للاشتراك:", reply_markup=markup)
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
                with open(file, 'rb') as video:
                    bot.send_video(message.chat.id, video)
                os.remove(file)
                bot.delete_message(message.chat.id, msg.message_id)
                break
                
    except Exception as e:
        bot.reply_to(message, "حدث خطأ أثناء التحميل، تأكد من الرابط.")

keep_alive()
print("البوت يعمل الآن...")
bot.infinity_polling()
