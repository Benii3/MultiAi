import os
import sqlite3
import threading
import requests
from http.server import BaseHTTPRequestHandler, HTTPServer
from dotenv import load_dotenv
import telebot
from telebot import types
from telebot.types import ReplyKeyboardMarkup
from openai import OpenAI
from google import genai

load_dotenv()

bot_token = os.getenv("main_token_bot")
bot = telebot.TeleBot(bot_token)

openrouter_key = os.getenv("OPENROUTER_API_KEY")

client = OpenAI(
    api_key=openrouter_key,
    base_url="https://openrouter.ai/api/v1"
)

groq_key = os.getenv("GROQ_API_KEY")

groq_client = OpenAI(
    api_key=groq_key,
    base_url="https://api.groq.com/openai/v1"
)

gemini_key = os.getenv("GEMINI_API_KEY")
gemini_client = genai.Client(api_key=gemini_key)

pollinations_key = os.getenv("POLLINATIONS_API_KEY")

connection = sqlite3.connect(
    "users.db",
    check_same_thread=False
)

connection.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER UNIQUE
)
""")

connection.commit()

FILES_FOLDER = "files"

os.makedirs(FILES_FOLDER, exist_ok=True)

waiting_for_gpt = {}
gpt_timers = {}

waiting_for_gemini = {}
gemini_timers = {}

waiting_for_groq = {}
groq_timers = {}

waiting_for_image = {}
image_timers = {}


def main():

    reply_keyboard = ReplyKeyboardMarkup(
        resize_keyboard=True,
        one_time_keyboard=False
    )

    button1 = types.KeyboardButton("انتخاب هوش مصنوعی 🤖")
    button2 = types.KeyboardButton("تنظیمات ⚙️")
    button3 = types.KeyboardButton("راهنما 📚")

    reply_keyboard.add(button1)
    reply_keyboard.add(button2)
    reply_keyboard.add(button3)

    return reply_keyboard


def back_menu():

    reply_keyboard = ReplyKeyboardMarkup(
        resize_keyboard=True,
        one_time_keyboard=False
    )

    button = types.KeyboardButton("بازگشت 🔙")

    reply_keyboard.add(button)

    return reply_keyboard


def ai_chose():

    ai_keyboard = ReplyKeyboardMarkup(
        resize_keyboard=True,
        one_time_keyboard=False
    )

    button1 = types.KeyboardButton("Chat GPT")
    button2 = types.KeyboardButton("Gemini")
    button3 = types.KeyboardButton("Groq")
    button4 = types.KeyboardButton("Claude")
    button5 = types.KeyboardButton("پاسخ از همه مدل‌ها")
    button6 = types.KeyboardButton("بازگشت 🔙")

    ai_keyboard.add(button1, button2)
    ai_keyboard.add(button3, button4)
    ai_keyboard.add(button5)
    ai_keyboard.add(button6)

    return ai_keyboard


def gemini_menu():

    keyboard = ReplyKeyboardMarkup(
        resize_keyboard=True,
        one_time_keyboard=False
    )

    button1 = types.KeyboardButton("چت متنی Gemini 💬")
    button2 = types.KeyboardButton("ساخت تصویر 🎨")
    button3 = types.KeyboardButton("بازگشت 🔙")

    keyboard.add(button1)
    keyboard.add(button2)
    keyboard.add(button3)

    return keyboard


def image_back_menu():

    keyboard = ReplyKeyboardMarkup(
        resize_keyboard=True,
        one_time_keyboard=False
    )

    button = types.KeyboardButton("بازگشت 🔙")

    keyboard.add(button)

    return keyboard


@bot.message_handler(commands=['start'])
def start(message):

    telegram_id = message.chat.id

    connection.execute(
        "INSERT OR IGNORE INTO users (telegram_id) VALUES (?)",
        (telegram_id,)
    )

    connection.commit()

    bot.send_message(
        message.chat.id,
        "Welcome to Bot 👋",
        reply_markup=main()
    )


@bot.message_handler(
    func=lambda message: message.text == "انتخاب هوش مصنوعی 🤖"
)
def ai_menu(message):

    bot.send_message(
        message.chat.id,
        "شما وارد بخش هوش مصنوعی شدید 🤖\n\n"
        "هوش مصنوعی مورد نظر خود را انتخاب کنید:",
        reply_markup=ai_chose()
    )


@bot.message_handler(
    func=lambda message: message.text == "تنظیمات ⚙️"
)
def settings(message):

    bot.send_message(
        message.chat.id,
        "شما وارد بخش تنظیمات شدید ⚙️",
        reply_markup=back_menu()
    )


@bot.message_handler(
    func=lambda message: message.text == "راهنما 📚"
)
def help_menu(message):

    bot.send_message(
        message.chat.id,
        "راهنمای ربات 📚\n\n"
        "از منوی اصلی می‌توانید بخش‌های مختلف ربات را انتخاب کنید.",
        reply_markup=back_menu()
    )


@bot.message_handler(
    func=lambda message: message.text == "بازگشت 🔙"
)
def back_to_main(message):

    chat_id = message.chat.id

    waiting_for_gpt.pop(chat_id, None)
    waiting_for_gemini.pop(chat_id, None)
    waiting_for_groq.pop(chat_id, None)
    waiting_for_image.pop(chat_id, None)

    if chat_id in gpt_timers:
        gpt_timers[chat_id].cancel()
        gpt_timers.pop(chat_id, None)

    if chat_id in gemini_timers:
        gemini_timers[chat_id].cancel()
        gemini_timers.pop(chat_id, None)

    if chat_id in groq_timers:
        groq_timers[chat_id].cancel()
        groq_timers.pop(chat_id, None)

    if chat_id in image_timers:
        image_timers[chat_id].cancel()
        image_timers.pop(chat_id, None)

    bot.send_message(
        chat_id,
        "به منوی اصلی برگشتید 🏠",
        reply_markup=main()
    )


@bot.message_handler(
    func=lambda message: message.text == "Chat GPT"
)
def chat_gpt(message):

    chat_id = message.chat.id

    waiting_for_gpt[chat_id] = True
    waiting_for_gemini.pop(chat_id, None)
    waiting_for_groq.pop(chat_id, None)
    waiting_for_image.pop(chat_id, None)

    if chat_id in gpt_timers:
        gpt_timers[chat_id].cancel()

    gpt_timers[chat_id] = threading.Timer(
        300,
        gpt_timeout,
        args=[chat_id]
    )

    gpt_timers[chat_id].start()

    bot.send_message(
        chat_id,
        "🤖 Chat GPT\n\n"
        "لطفاً پیام متنی خود را ارسال کنید ✍️\n\n"
        "⚠️ در این بخش فقط ارسال متن امکان‌پذیر است.",
        reply_markup=back_menu()
    )


def gpt_timeout(chat_id):

    waiting_for_gpt.pop(chat_id, None)
    gpt_timers.pop(chat_id, None)

    bot.send_message(
        chat_id,
        "زمان استفاده از Chat GPT به پایان رسید ⏰\n\n"
        "برای استفاده دوباره، Chat GPT را انتخاب کنید.",
        reply_markup=ai_chose()
    )


def send_to_gpt(text):

    response = client.chat.completions.create(
        model="openrouter/free",
        messages=[
            {
                "role": "user",
                "content": text
            }
        ]
    )

    return response.choices[0].message.content


@bot.message_handler(
    func=lambda message: message.text == "Gemini"
)
def gemini(message):

    chat_id = message.chat.id

    waiting_for_gpt.pop(chat_id, None)
    waiting_for_gemini.pop(chat_id, None)
    waiting_for_groq.pop(chat_id, None)
    waiting_for_image.pop(chat_id, None)

    bot.send_message(
        chat_id,
        "✨ Gemini\n\n"
        "لطفاً قابلیت مورد نظر خود را انتخاب کنید:",
        reply_markup=gemini_menu()
    )


@bot.message_handler(
    func=lambda message: message.text == "چت متنی Gemini 💬"
)
def gemini_text_mode(message):

    chat_id = message.chat.id

    waiting_for_gemini[chat_id] = True
    waiting_for_gpt.pop(chat_id, None)
    waiting_for_groq.pop(chat_id, None)
    waiting_for_image.pop(chat_id, None)

    if chat_id in gemini_timers:
        gemini_timers[chat_id].cancel()

    gemini_timers[chat_id] = threading.Timer(
        300,
        gemini_timeout,
        args=[chat_id]
    )

    gemini_timers[chat_id].start()

    bot.send_message(
        chat_id,
        "✨ Gemini\n\n"
        "لطفاً پیام متنی خود را ارسال کنید ✍️\n\n"
        "⚠️ در این بخش فقط ارسال متن امکان‌پذیر است.",
        reply_markup=back_menu()
    )


def gemini_timeout(chat_id):

    waiting_for_gemini.pop(chat_id, None)
    gemini_timers.pop(chat_id, None)

    bot.send_message(
        chat_id,
        "زمان استفاده از Gemini به پایان رسید ⏰\n\n"
        "برای استفاده دوباره، Gemini را انتخاب کنید.",
        reply_markup=ai_chose()
    )


def send_to_gemini(text):

    models = [
        "gemini-3.5-flash-lite",
        "gemini-3.5-flash",
        "gemini-3.6-flash",
        "gemini-3.7-flash",
        "gemini-3.8-flash",
        "gemini-3-flash-preview",
        "gemini-3.1-flash-lite",
        "gemini-3.1-flash-lite-preview",
        "gemini-flash-lite-latest",
        "gemini-flash-latest",
        "gemini-2.5-flash",
        "gemini-2.5-pro",
        "gemini-pro-latest",
        "gemma-4-26b-a4b-it",
        "gemma-4-31b-it"
    ]

    last_error = None

    for model in models:

        try:

            print(f"Trying Gemini model: {model}")

            response = gemini_client.models.generate_content(
                model=model,
                contents=text
            )

            print(f"SUCCESS: {model}")

            if response.text:
                return response.text

        except Exception as error:

            last_error = error

            print(f"FAILED: {model}")
            print(error)

            error_text = str(error)

            if "404" in error_text or "NOT_FOUND" in error_text:
                continue

            if "429" in error_text or "RESOURCE_EXHAUSTED" in error_text:
                continue

            if "503" in error_text or "UNAVAILABLE" in error_text:
                continue

            if "500" in error_text or "INTERNAL" in error_text:
                continue

            if "502" in error_text or "BAD_GATEWAY" in error_text:
                continue

            raise error

    if last_error:
        raise last_error

    return "Gemini پاسخی تولید نکرد ❌"


@bot.message_handler(
    func=lambda message: message.text == "Groq"
)
def groq(message):

    chat_id = message.chat.id

    waiting_for_groq[chat_id] = True

    waiting_for_gpt.pop(chat_id, None)
    waiting_for_gemini.pop(chat_id, None)
    waiting_for_image.pop(chat_id, None)

    if chat_id in groq_timers:
        groq_timers[chat_id].cancel()

    groq_timers[chat_id] = threading.Timer(
        300,
        groq_timeout,
        args=[chat_id]
    )

    groq_timers[chat_id].start()

    bot.send_message(
        chat_id,
        "⚡ Groq\n\n"
        "لطفاً پیام متنی خود را ارسال کنید ✍️\n\n"
        "⚠️ در این بخش فقط ارسال متن امکان‌پذیر است.",
        reply_markup=back_menu()
    )


def groq_timeout(chat_id):

    waiting_for_groq.pop(chat_id, None)
    groq_timers.pop(chat_id, None)

    bot.send_message(
        chat_id,
        "زمان استفاده از Groq به پایان رسید ⏰\n\n"
        "برای استفاده دوباره، Groq را انتخاب کنید.",
        reply_markup=ai_chose()
    )


def send_to_groq(text):

    response = groq_client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {
                "role": "user",
                "content": text
            }
        ]
    )

    return response.choices[0].message.content


def translate_image_prompt(text):

    prompt = f"""
Convert the following Persian description into a detailed English prompt for an AI image generator.

Rules:
- Keep the exact meaning of the user's request.
- Do not add unrelated objects or details.
- Preserve the requested style, colors, people, objects, environment and actions.
- Make the prompt clear and suitable for image generation.
- Return ONLY the English image prompt.
- Do not explain anything.

Persian description:
{text}
"""

    return send_to_gemini(prompt)


def generate_image(prompt):

    try:

        english_prompt = translate_image_prompt(prompt)

        print("ORIGINAL PROMPT:", prompt)
        print("ENGLISH PROMPT:", english_prompt)

        url = (
            "https://gen.pollinations.ai/image/"
            + requests.utils.quote(english_prompt)
        )

        response = requests.get(
            url,
            params={
                "model": "flux",
                "key": pollinations_key
            },
            timeout=120
        )

        if response.status_code != 200:

            print("IMAGE ERROR:", response.status_code)
            print(response.text)

            return None

        file_path = os.path.join(
            FILES_FOLDER,
            f"generated_{threading.get_ident()}.jpg"
        )

        with open(file_path, "wb") as file:
            file.write(response.content)

        return file_path

    except Exception as error:

        print("IMAGE ERROR:", error)

        return None


@bot.message_handler(
    func=lambda message: message.text == "ساخت تصویر 🎨"
)
def image_generator(message):

    chat_id = message.chat.id

    waiting_for_image[chat_id] = True
    waiting_for_gpt.pop(chat_id, None)
    waiting_for_gemini.pop(chat_id, None)
    waiting_for_groq.pop(chat_id, None)

    if chat_id in image_timers:
        image_timers[chat_id].cancel()

    image_timers[chat_id] = threading.Timer(
        300,
        image_timeout,
        args=[chat_id]
    )

    image_timers[chat_id].start()

    bot.send_message(
        chat_id,
        "🎨 ساخت تصویر\n\n"
        "توضیح تصویری که می‌خواهید بسازم را ارسال کنید ✍️\n\n"
        "مثال:\n"
        "یک گربه نارنجی روی ماه که به زمین نگاه می‌کند 🌙🐈",
        reply_markup=image_back_menu()
    )


def image_timeout(chat_id):

    waiting_for_image.pop(chat_id, None)
    image_timers.pop(chat_id, None)

    bot.send_message(
        chat_id,
        "زمان ساخت تصویر به پایان رسید ⏰\n\n"
        "برای ساخت تصویر دوباره، گزینه ساخت تصویر را انتخاب کنید.",
        reply_markup=gemini_menu()
    )


@bot.message_handler(content_types=['text'])
def handel_text(message):

    chat_id = message.chat.id

    if chat_id in waiting_for_gpt:

        if chat_id in gpt_timers:
            gpt_timers[chat_id].cancel()

        gpt_timers[chat_id] = threading.Timer(
            300,
            gpt_timeout,
            args=[chat_id]
        )

        gpt_timers[chat_id].start()

        text = message.text

        try:

            answer = send_to_gpt(text)

            bot.send_message(
                chat_id,
                answer,
                reply_markup=back_menu()
            )

        except Exception as error:

            bot.send_message(
                chat_id,
                "متأسفانه در ارتباط با Chat GPT مشکلی پیش آمد ❌",
                reply_markup=back_menu()
            )

            print("GPT ERROR:", error)

        return

    if chat_id in waiting_for_gemini:

        if chat_id in gemini_timers:
            gemini_timers[chat_id].cancel()

        gemini_timers[chat_id] = threading.Timer(
            300,
            gemini_timeout,
            args=[chat_id]
        )

        gemini_timers[chat_id].start()

        text = message.text

        try:

            answer = send_to_gemini(text)

            bot.send_message(
                chat_id,
                answer,
                reply_markup=back_menu()
            )

        except Exception as error:

            bot.send_message(
                chat_id,
                "متأسفانه در ارتباط با Gemini مشکلی پیش آمد ❌",
                reply_markup=back_menu()
            )

            print("GEMINI ERROR:", error)

        return

    if chat_id in waiting_for_groq:

        if chat_id in groq_timers:
            groq_timers[chat_id].cancel()

        groq_timers[chat_id] = threading.Timer(
            300,
            groq_timeout,
            args=[chat_id]
        )

        groq_timers[chat_id].start()

        text = message.text

        try:

            answer = send_to_groq(text)

            bot.send_message(
                chat_id,
                answer,
                reply_markup=back_menu()
            )

        except Exception as error:

            bot.send_message(
                chat_id,
                "متأسفانه در ارتباط با Groq مشکلی پیش آمد ❌",
                reply_markup=back_menu()
            )

            print("GROQ ERROR:", error)

        return

    if chat_id in waiting_for_image:

        if chat_id in image_timers:
            image_timers[chat_id].cancel()

        image_timers[chat_id] = threading.Timer(
            300,
            image_timeout,
            args=[chat_id]
        )

        image_timers[chat_id].start()

        text = message.text

        bot.send_message(
            chat_id,
            "🎨 در حال ساخت تصویر هستم...\n"
            "لطفاً کمی صبر کنید ⏳"
        )

        try:

            image_path = generate_image(text)

            if image_path:

                with open(image_path, "rb") as image_file:

                    bot.send_photo(
                        chat_id,
                        image_file,
                        caption="تصویر شما آماده شد 🎨✨",
                        reply_markup=back_menu()
                    )

                try:
                    os.remove(image_path)
                except:
                    pass

            else:

                bot.send_message(
                    chat_id,
                    "متأسفانه ساخت تصویر با مشکل مواجه شد ❌",
                    reply_markup=back_menu()
                )

        except Exception as error:

            print("IMAGE ERROR:", error)

            bot.send_message(
                chat_id,
                "متأسفانه هنگام ساخت تصویر مشکلی پیش آمد ❌",
                reply_markup=back_menu()
            )

        return


@bot.message_handler(content_types=['document'])
def handle_file(message):

    document_file = message.document.file_name
    file_extension = document_file.lower()

    if file_extension.endswith((".pdf", ".txt", ".png", ".pptx")):

        file_info = bot.get_file(
            message.document.file_id
        )

        file_data = bot.download_file(
            file_info.file_path
        )

        file_path = os.path.join(
            FILES_FOLDER,
            document_file
        )

        with open(file_path, "wb") as file:
            file.write(file_data)

        if file_extension.endswith(".pdf"):
            file_type = "PDF 📄"

        elif file_extension.endswith(".txt"):
            file_type = "TXT 📄"

        elif file_extension.endswith(".png"):
            file_type = "PNG 🖼"

        elif file_extension.endswith(".pptx"):
            file_type = "PPTX 📊"

        bot.reply_to(
            message,
            f"نوع فایل: {file_type}\n"
            f"فایل {document_file} با موفقیت دریافت و ذخیره شد ✅"
        )

    else:

        bot.reply_to(
            message,
            "این نوع فایل پشتیبانی نمی‌شود ❌"
        )


@bot.message_handler(content_types=['photo'])
def photo_finder(message):

    photo = message.photo[-1]

    file_info = bot.get_file(
        photo.file_id
    )

    file_data = bot.download_file(
        file_info.file_path
    )

    file_name = f"photo_{message.message_id}.jpg"

    file_path = os.path.join(
        FILES_FOLDER,
        file_name
    )

    with open(file_path, "wb") as file:
        file.write(file_data)

    bot.reply_to(
        message,
        f"عکس با موفقیت دریافت و ذخیره شد ✅\n"
        f"📁 {file_name}"
    )


@bot.message_handler(content_types=['audio'])
def audio_finder(message):

    file_info = bot.get_file(
        message.audio.file_id
    )

    file_data = bot.download_file(
        file_info.file_path
    )

    file_name = message.audio.file_name

    file_path = os.path.join(
        FILES_FOLDER,
        file_name
    )

    with open(file_path, "wb") as file:
        file.write(file_data)

    bot.reply_to(
        message,
        f"فایل صوتی با موفقیت دریافت و ذخیره شد ✅\n"
        f"📁 {file_name}"
    )


class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):

        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"MultiAI is running")

    def log_message(self, format, *args):
        return


def run_server():

    port = int(os.environ.get("PORT", 10000))

    server = HTTPServer(
        ("0.0.0.0", port),
        HealthHandler
    )

    server.serve_forever()


threading.Thread(
    target=run_server,
    daemon=True
).start()


bot.infinity_polling(
    timeout=60,
    long_polling_timeout=60
)
