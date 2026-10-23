import sqlite3
from datetime import datetime, timedelta

def get_user_data(user_id):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT state, habit_name, habit_frequency, habit_time FROM user_states WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"state": row, "name": row, "frequency": row, "time": row}
    return {"state": None, "name": None, "frequency": None, "time": None}

def update_user_state(user_id, state=None, name=None, frequency=None, time=None):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO user_states (user_id, state, habit_name, habit_frequency, habit_time)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            state = COALESCE(?, state),
            habit_name = COALESCE(?, habit_name),
            habit_frequency = COALESCE(?, habit_frequency),
            habit_time = COALESCE(?, habit_time)
    ''', (user_id, state, name, frequency, time, state, name, frequency, time))
    conn.commit()
    conn.close()

def clear_user_state(user_id):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM user_states WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def add_habit_to_db(user_id, name, frequency, time, timezone_offset=0):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO habits (user_id, name, frequency, time, timezone_offset, is_active) VALUES (?, ?, ?, ?, ?, 1)",
                   (user_id, name, frequency, time, timezone_offset))
    conn.commit()
    conn.close()

def get_user_habits(user_id):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM habits WHERE user_id = ? AND is_active = 1", (user_id,))
    habits = cursor.fetchall()
    conn.close()
    return habits

def is_habit_done_today(habit_id):
    today = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM habit_logs WHERE habit_id = ? AND date = ?", (habit_id, today))
    row = cursor.fetchone()
    conn.close()
    return row is not None

def log_habit_completion(habit_id):
    today = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO habit_logs (habit_id, date) VALUES (?, ?)", (habit_id, today))
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        success = False
    conn.close()
    return success

def check_habit_owner(habit_id, user_id):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM habits WHERE id = ? AND user_id = ? AND is_active = 1", (habit_id, user_id))
    row = cursor.fetchone()
    conn.close()
    return row is not None

def get_all_habits_for_reminders():
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, user_id, name, time, timezone_offset FROM habits WHERE is_active = 1")
    rows = cursor.fetchall()
    conn.close()
    return rows

def deactivate_user_habits(user_id):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE habits SET is_active = 0 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def delete_all_user_habits(user_id):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM habits WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def calculate_streak(logs_dates_list, target_date_str):
    if not logs_dates_list:
        return 0
    sorted_dates = sorted([datetime.strptime(d, "%Y-%m-%d") for d in logs_dates_list], reverse=True)
    target_date = datetime.strptime(target_date_str, "%Y-%m-%d")
    streak = 0
    current_check = target_date
    if current_check in sorted_dates:
        pass
    elif (current_check - timedelta(days=1)) in sorted_dates:
        current_check = current_check - timedelta(days=1)
    else:
        return 0
    while current_check in sorted_dates:
        streak += 1
        current_check -= timedelta(days=1)
    return streak