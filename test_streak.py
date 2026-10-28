import unittest
from datetime import datetime, timedelta
from database import calculate_streak

class TestHabitStreak(unittest.TestCase):

    def test_empty_logs(self):
        """Тест 1: Если отметок нет вообще, серия дней должна быть 0."""
        logs = []
        result = calculate_streak(logs, "2026-10-23")
        self.assertEqual(result, 0)

    def test_single_day_streak(self):
        """Тест 2: Если отметка есть только сегодня, серия должна быть 1."""
        logs = ["2026-10-23"]
        result = calculate_streak(logs, "2026-10-23")
        self.assertEqual(result, 1)

    def test_continuous_streak(self):
        """Тест 3: Обычная непрерывная серия за 3 дня подряд."""
        logs = ["2026-10-21", "2026-10-22", "2026-10-23"]
        result = calculate_streak(logs, "2026-10-23")
        self.assertEqual(result, 3)

    def test_broken_streak(self):
        """Тест 4: Если был пропуск, серия дней должна сброситься."""
        logs = ["2026-10-20", "2026-10-21", "2026-10-23"] # 22-е число пропущено
        result = calculate_streak(logs, "2026-10-23")
        self.assertEqual(result, 1)

    def test_future_date_logic(self):
        """Тест 5: Проверка обработки дат из будущего."""
        logs = ["2026-10-23"]
        result = calculate_streak(logs, "2026-10-25")
        self.assertEqual(result, 0)

    def test_unsorted_logs_order(self):
        """Тест 6: Логи в разнобой не должны ломать расчет серии."""
        logs = ["2026-10-23", "2026-10-21", "2026-10-22"]
        result = calculate_streak(logs, "2026-10-23")
        self.assertEqual(result, 3)

    def test_duplicate_logs_handling(self):
        """Тест 7: Дублирующиеся логи за один день не должны удваивать серию."""
        logs = ["2026-10-22", "2026-10-23", "2026-10-23"]
        result = calculate_streak(logs, "2026-10-23")
        self.assertEqual(result, 2)

    def test_streak_with_yesterday_start(self):
        """Тест 8: Если сегодня отметки еще нет, но вчера была непрерывная серия."""
        logs = ["2026-10-21", "2026-10-22"]
        result = calculate_streak(logs, "2026-10-23")
        self.assertEqual(result, 2)

    def test_timezone_local_time_calculation(self):
        """Тест 9: Проверка расчета локального времени на основе смещения часового пояса."""
        utc_now = datetime(2026, 10, 24, 12, 0)
        tz_offset = 3
        user_local_time = utc_now + timedelta(hours=tz_offset)
        current_time_str = user_local_time.strftime("%H:%M")
        self.assertEqual(current_time_str, "15:00")

if __name__ == "__main__":
    unittest.main()

