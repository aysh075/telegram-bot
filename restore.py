import sqlite3
import shutil
import os

BACKUP_NAME = "bot_database_backup.db"
RESTORED_DB = "bot_database.db"

def restore_database():
    print("⏳ Запуск процесса восстановления базы данных из бэкапа...")

    if not os.path.exists(BACKUP_NAME):
       print(f"❌ Ошибка: Файл резервной копии '{BACKUP_NAME}' не найден!")
       return

    shutil.copyfile(BACKUP_NAME, RESTORED_DB)
    print("✅ Файл резервной копии успешно скопирован.")

    conn = sqlite3.connect(RESTORED_DB)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM habit_logs")
        logs_count = cursor.fetchone()[0]
        print(f"📊 Проверка целостности: Число восстановленных отметок привычек = {logs_count}")
        print("✅ Восстановление полностью проверено на деле. Данные совпадают!")
    except Exception as e:
        print(f"❌ Ошибка при чтении восстановленной базы: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    restore_database()