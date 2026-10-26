import telebot
import os
import logging
import re
import time
import threading
import shutil
import schedule
import datetime as dt
from datetime import datetime, timedelta
from telebot import types
from telebot.apihelper import ApiTelegramException
from dotenv import load_dotenv
from migrations import run_migrations
from database import (
    get_user_data, update_user_state, clear_user_state,
    add_habit_to_db, get_user_habits, is_habit_done_today, log_habit_completion,
    check_habit_owner, get_all_habits_for_reminders, delete_all_user_habits,
    deactivate_user_habits
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot_activity.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

run_migrations()

DB_NAME = "bot_database.db"
BACKUP_NAME = "bot_database_backup.db"

def create_backup():
    try:
        if os.path.exists(DB_NAME):
            shutil.copyfile(DB_NAME, BACKUP_NAME)
            logging.info("Резервная копия базы данных успешно создана.")
    except Exception as e:
        logging.error(f"Ошибка бэкапа: {e}")

def safe_send_reminder(user_id, text, habit_id=None):
    delays = [1,5,15] 
    for attempt, delay in enumerate(delays, start=1):
        try:
            bot.send_message(user_id, text, parse_mode="Markdown")
            logging.info(f"Напоминание пользователю {user_id} успешно доставлено.")
            return True
        except ApiTelegramException as e:
            if e.error_code == 403:
                logging.warning(f"Ошибка 403:Пользователь {user_id} заблокировал бота. Отключаем напоминания.")
                deactivate_user_habits(user_id)
                return False
            logging.error(f"Сбой сети для пользователя {user_id} (Попытка {attempt}): {e}")
            if attempt < len(delays):
                time.sleep(delay)
        except Exception as e:
            logging.error(f"Ошибка отправки пользователю {user_id}: {e}")
            time.sleep(delay)
    logging.warning(f"Сетъ недоступна.Переносим отправку напоминания пользователю{user_id} на 5 минут. ")
    threading.Timer(300,safe_send_reminder, args=[user_id, text, habit_id]).start()
    return False

def send_reminders():
    try
        utc_now = datetime.now(dt.timezone.utc).replace(tzinfo=None)
        habits = get_all_habits_for_reminders()
        for habit_id, user_id, name, habit_time, tz_offset in habits:
            if is_habit_done_today(habit_id):
                continue
            user_local_time = utc_now + timedelta(hours=tz_offset)
            current_time_str = user_local_time.strftime("%H:%M")
            if habit_time == current_time_str:
                reminder_text = f"🕒 Время {current_time_str}! Пора выполнить вашу привычку: **{name}**!\nОтметьте её через /list."
                threading.Thread(target=safe_send_reminder, args=(user_id, reminder_text, habit_id), daemon=True).start()
    except Exception as e:
        logging.error(f"Ошибка в планировщике: {e}")

def scheduler_loop():
    schedule.every().minute.do(send_reminders)
    schedule.every().hour.do(create_backup)
    create_backup()
    while True:
        schedule.run_pending()
        time.sleep(1)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    try:
        clear_user_state(message.from_user.id)
        logging.info(f"Пользователь {message.from_user.id} вызвал старт.")
        help_text = (
            "Привет! Я помогу тебе управлять полезными привычками.\n\n"
            "📌 /add - Создать новую привычку\n"
            "📌 /list - Показать список привычек на сегодня\n"
            "📌 /off - Отключить все напоминания разом\n"
            "📌 /cancel - Отменить текущий диалог"
        )
        bot.reply_to(message, help_text)
    except Exception as e:
        logging.error(f"Ошибка команды start/help: {e}")

@bot.message_handler(commands=['off'])
def turn_off_all_reminders(message):
    try:
        user_id = message.from_user.id
        delete_all_user_habits(user_id)
        logging.info(f"Пользователь {user_id} вызвал /off.")
        bot.reply_to(message, "📴 Все ваши привычки и напоминания успешно удалены!")
    except Exception as e:
        logging.error(f"Ошибка команды /off: {e}")

@bot.message_handler(commands=['cancel'])
def cancel_process(message):
    try:
        user_id = message.from_user.id
        user_data = get_user_data(user_id)
        if user_data["state"]:
            clear_user_state(user_id)
            bot.reply_to(message, "❌ Процесс создания привычки отменен.")
        else:
            bot.reply_to(message, "У вас нет активного процесса создания привычки.")
    except Exception as e:
        logging.error(f"Ошибка команды cancel: {e}")

@bot.message_handler(commands=['add'])
def start_add_habit(message):
    try:
        user_id = message.from_user.id
        update_user_state(user_id, state="WAITING_NAME")
        bot.reply_to(message, "📝 Шаг 1/4: Введите название новой привычки:")
    except Exception as e:
        logging.error(f"Ошибка команды add: {e}")

@bot.message_handler(commands=['list'])
def list_habits(message):
    try:
        user_id = message.from_user.id
        habits = get_user_habits(user_id)
        if not habits:
            bot.reply_to(message, "У вас пока нет созданных привычек. Добавьте их с помощью /add!")
            return
        markup = types.InlineKeyboardMarkup()
        text_lines = ["📋 **Твои привычки на сегодня:**\n"]
        for index, habit in enumerate(habits, start=1):
            habit_id, name = habit
            done = is_habit_done_today(habit_id)
            status_emoji = "✅ отмечено" if done else "❌ нет"
            text_lines.append(f"{index}. {name} — {status_emoji}")
            if not done:
                button = types.InlineKeyboardButton(text=f"Отметить: {name}", callback_data=f"done_{habit_id}")
                markup.add(button)
        bot.send_message(message.chat.id, "\n".join(text_lines), reply_markup=markup, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Ошибка команды list: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith('done_'))
def handle_habit_click(call):
    try:
        user_id = call.from_user.id
        habit_id = int(call.data.split('_')[1])
        if not check_habit_owner(habit_id, user_id):
            bot.answer_callback_query(call.id, text="⚠️ Ошибка доступа!", show_alert=True)
            return
        if is_habit_done_today(habit_id):
            bot.answer_callback_query(call.id, text="⚠️ Эта привычка уже отмечена сегодня!", show_alert=True)
            return
        success = log_habit_completion(habit_id)
        if success:
            bot.answer_callback_query(call.id, text="🎉 Привычка успешно отмечена!")
            logging.info(f"Пользователь {user_id} отметил привычку {habit_id}.")
            habits = get_user_habits(user_id)
            markup = types.InlineKeyboardMarkup()
            text_lines = ["📋 **Твои привычки на сегодня:**\n"]
            for index, habit in enumerate(habits, start=1):
                h_id, name = habit
                done = is_habit_done_today(h_id)
                status_emoji = "✅ отмечено" if done else "❌ нет"
                text_lines.append(f"{index}. {name} — {status_emoji}")
                if not done:
                    button = types.InlineKeyboardButton(text=f"Отметить: {name}", callback_data=f"done_{h_id}")
                    markup.add(button)
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.id,
                text="\n".join(text_lines),
                reply_markup=markup,
                parse_mode="Markdown"
            )
    except Exception as e:
        logging.error(f"Ошибка клика инлайн-кнопки: {e}")

@bot.message_handler(func=lambda message: message.text and message.text.startswith('/'))
def unknown_command(message):
    try:
        bot.reply_to(message, "Ой, я не знаю такой команды. 🧐 Введите /help для подсказки.")
    except Exception as e:
        logging.error(f"Ошибка неизвестной команды: {e}")

@bot.message_handler(func=lambda message: True)
def handle_dialogue(message):
    try:
        user_id = message.from_user.id
        user_data = get_user_data(user_id)
        current_state = user_data["state"]
        if not current_state:
            bot.reply_to(message, "Используйте /add, чтобы завести привычку!")
            return
        text = message.text.strip() if message.text else ""
        if current_state == "WAITING_NAME":
            if not text:
                bot.reply_to(message, "❌ Название не может быть пустым.")
                return
            update_user_state(user_id, state="WAITING_FREQUENCY", name=text)
            bot.reply_to(message, "🔄 Шаг 2/4: Как часто вы хотите этим заниматься?:")
        elif current_state == "WAITING_FREQUENCY":
            if not text:
                bot.reply_to(message, "❌ Укажите частоту:")
                return
            update_user_state(user_id, state="WAITING_TIME", frequency=text)
            bot.reply_to(message, "🕒 Шаг 3/4: Укажите местное время напоминания в формате ЧЧ:ММ:")
        elif current_state == "WAITING_TIME":
            time_match = re.match(r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$", text)
            if not time_match:
                bot.reply_to(message, "❌ Неверный формат! Введите ЧЧ:ММ:")
                return
            update_user_state(user_id, state="WAITING_TZ", time=text)
            bot.reply_to(message, "🌍 Шаг 4/4: Введите смещение вашего часового пояса от UTC (например, +3):")
        elif current_state == "WAITING_TZ":
            try:
                tz_offset = int(text.replace("+", ""))
                if not (-12 <= tz_offset <= 14):
                    raise ValueError
            except ValueError:
                bot.reply_to(message, "❌ Неверный часовой пояс! Введите число от -12 до +14:")
                return
            add_habit_to_db(user_id, user_data["name"], user_data["frequency"], user_data["time"], tz_offset)
            logging.info(f"Создана новая привычка для пользователя {user_id}.")
            bot.reply_to(message, f"🎉 Привычка успешно создана!", parse_mode="Markdown")
            clear_user_state(user_id)
    except Exception as e:
        logging.error(f"Критическая ошибка в диалоге: {e}")
if __name__ == "__main__":
    if threading.current_thread() is threading.main_thread():
        threading.Thread(target=scheduler_loop, daemon=True).start()
    logging.info("Бот успешно инициализирован в системе.")
    bot.infinity_polling()   