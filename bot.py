import telebot
import os
import logging
import re
from telebot import types
from dotenv import load_dotenv
from database import (
    init_db, get_user_data, update_user_state, clear_user_state,
    add_habit_to_db, get_user_habits, is_habit_done_today, log_habit_completion
)

# Səhvlərin loq faylına yazılması
logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='bot_errors.log'
)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

init_db()

# /start və /help komandaları
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    try:
        clear_user_state(message.from_user.id)
        help_text = (
            "Привет! Я помогу тебе управлять полезными привычками.\n\n"
            "📌 /add - Создать новую привычку\n"
            "📌 /list - Показать список моих привычек на сегодня\n"
            "📌 /cancel - Отменить текущий диалог"
        )
        bot.reply_to(message, help_text)
    except Exception as e:
        logging.error(f"Ошибка в команде start/help: {e}")

# /cancel komandası
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
        logging.error(f"Ошибка в команде cancel: {e}")

# /add komandası
@bot.message_handler(commands=['add'])
def start_add_habit(message):
    try:
        user_id = message.from_user.id
        update_user_state(user_id, state="WAITING_NAME")
        bot.reply_to(message, "📝 Шаг 1/3: Введите название новой привычки:")
    except Exception as e:
        logging.error(f"Ошибка в начале команды add: {e}")

# YENİ: /list komandası - Vərdişlərin siyahısı və Inline düymələr (Mərhələ 1 və 2)
@bot.message_handler(commands=['list'])
def list_habits(message):
    try:
        user_id = message.from_user.id
        habits = get_user_habits(user_id) # Məlumatların izolyasiyası - yalnız özününkülər gəlir

        if not habits:
            bot.reply_to(message, "У вас пока нет созданных привычек. Добавьте их с помощью /add!")
            return

        # Klaviatura düymələri və mətnin qurulması
        markup = types.InlineKeyboardMarkup()
        text_lines = ["📋 **Твои привычки на сегодня:**\n"]

        for index, habit in enumerate(habits, start=1):
            habit_id, name = habit
            done = is_habit_done_today(habit_id)

            # Status işarəsi (Meyar 1)
            status_emoji = "✅ отмечено" if done else "❌ нет"
            text_lines.append(f"{index}. {name} — {status_emoji}")

            # Əgər bu gün qeyd edilməyibsə düymə yaradılır (Meyar 2)
            if not done:     
                button = types.InlineKeyboardButton(text=f"Отметить: {name}", callback_data=f"done_{habit_id}")
                markup.add(button)

        bot.send_message(message.chat.id, "\n".join(text_lines), reply_markup=markup, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Ошибка в команде list: {e}")

# YENİ: İncə toxunuşla işarələmə (Callback query handler) və İkiqat klik qoruması (Meyar 2 və 4)
@bot.callback_query_handler(func=lambda call: call.data.startswith('done_'))
def handle_habit_click(call):
    try:
        habit_id = int(call.data.split('_')[1])

        # Bu gün artıq kliklənib-kliklənmədiyini yoxlayırıq (Daxili qoruma)
        if is_habit_done_today(habit_id):
            bot.answer_callback_query(call.id, text="⚠️ Эта привычка уже была отмечена сегодня!", show_alert=True)
            return

        # Bazada qeyd edirik
        success = log_habit_completion(habit_id)

        if success:
            bot.answer_callback_query(call.id, text="🎉 Привычка успешно отмечена!")

            # Ekranda siyahını dərhal yeniləyirik ki, status "✅ отмечено" olsun
            user_id = call.from_user.id
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
        else:
            bot.answer_callback_query(call.id, text="⚠️ Ошибка: Двойная отметка за день невозможна!", show_alert=True)

    except Exception as e:
        logging.error(f"Ошибка в обработке клика inline-кнопки: {e}")

# Naməlum komandaların tutulması
@bot.message_handler(func=lambda message: message.text and message.text.startswith('/'))
def unknown_command(message):
    try:
        bot.reply_to(message, "Ой, я не знаю такой команды. 🧐 Введите /help для подсказки.")
    except Exception as e:
        logging.error(f"Ошибка неизвестной команды: {e}")

# FSM Dialoq mətn ötürücüsü
@bot.message_handler(func=lambda message: True)
def handle_dialogue(message):
    try:
        user_id = message.from_user.id
        user_data = get_user_data(user_id)
        current_state = user_data["state"]

        if not current_state:
            bot.reply_to(message, "Я вижу твое сообщение, но давай начнем с главного: введи команду /add, чтобы завести привычку!")
            return

        text = message.text.strip() if message.text else ""

        if current_state == "WAITING_NAME":
            if not text:
                bot.reply_to(message, "❌ Название привычки не может быть пустым.")
                return
            update_user_state(user_id, state="WAITING_FREQUENCY", name=text)
            bot.reply_to(message, "🔄 Шаг 2/3: Как часто вы хотите этим заниматься?:")

        elif current_state == "WAITING_FREQUENCY":
            if not text:
                bot.reply_to(message, "❌ Пожалуйста, укажите частоту:")
                return
            update_user_state(user_id, state="WAITING_TIME", frequency=text)
            bot.reply_to(message, "🕒 Шаг 3/3: Укажите время для напоминания в формате ЧЧ:ММ:")

        elif current_state == "WAITING_TIME":
            time_match = re.match(r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$", text)
            if not time_match:
                bot.reply_to(message, "❌ Неверный формат времени! Пожалуйста, введите ЧЧ:ММ:")
                return

            # FSM bitəndə məlumatı həqiqi "habits" cədvəlinə yazırıq
            add_habit_to_db(user_id, user_data["name"], user_data["frequency"], text)

            bot.reply_to(message, f"🎉 Привычка **{user_data['name']}** успешно создана и сохранена! Проверьте список через /list.", parse_mode="Markdown")
            clear_user_state(user_id)

    except Exception as e:
        logging.error(f"Критическая ошибка в диалоге: {e}")

if __name__ == "__main__":
    print("Бот успешно запущен...")
    bot.infinity_polling()