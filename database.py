import sqlite3

def init_db():
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()

# İstifadəçinin cari vəziyyətini (state) və müvəqqəti daxil etdiyi məlumatları saxlayan cədvəl
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_states (
            user_id INTEGER PRIMARY KEY,
            state TEXT,
            habit_name TEXT,
            habit_frequency TEXT,
            habit_time TEXT
        )
    ''')
    conn.commit()
    conn.close()

def get_user_data(user_id):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT state, habit_name, habit_frequency, habit_time FROM user_states WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"state": row[0], "name": row[1], "frequency": row[2], "time": row[3]}
    return {"state": None, "name": None, "frequency": None, "time": None}

def update_user_state(user_id, state=None, name=None, frequency=None, time=None):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()

# Əgər istifadəçi yoxdursa yaradır, varsa yeniləyir
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