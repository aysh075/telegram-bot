import unittest
from datetime import datetime , timedelta
from database import calculate_streak

class TestHabitStreak(unittest.TestCase):

    def test_empty_logs(self):
        """Тест: Если отметок нет вообще, серия дней должна быть 0."""
        logs = []
        result = calculate_streak(logs, "2026-10-23")
        self.assertEqual(result, 0)

    def test_single_day_streak(self):
        """Тест: Если отметка есть только за сегодня, серия должна быть 1."""
        logs = ["2026-10-23"]
        result = calculate_streak(logs, "2026-10-23")
        self.assertEqual(result, 1)

    def test_continuous_streak(self):
        """Тест: Обычная непрерывная серия за 3 дня подряд."""
        logs = ["2026-10-21", "2026-10-22", "2026-10-23"]
        result = calculate_streak(logs, "2026-10-23")
        self.assertEqual(result, 3)

    def test_broken_streak(self):
        """Тест: Если был пропуск, серия дней должна сброситься."""
        logs = ["2026-10-20", "2026-10-21", "2026-10-23"] # 22-е число пропущено
        result = calculate_streak(logs, "2026-10-23")
        self.assertEqual(result, 1)
    def test_timezone_local_time_calculation(self):
        """Тест: Проверка расчета локального времени на основе смещения часового пояса."""
        utc_now = datetime(2026, 10, 24, 12, 0) # 12:00 UTC
        tz_offset = 3 # Məsələn, Bakı vaxtı üçün offset

        user_local_time = utc_now + timedelta(hours=tz_offset)
        current_time_str = user_local_time.strftime("%H:%M")

        # Yoxlayırıq ki, yerli vaxt şəbəkə olmadan 15:00 olaraq düzgün hesablanır
        self.assertEqual(current_time_str, "15:00")
    if __name__ == "__main__":
        unittest.main()