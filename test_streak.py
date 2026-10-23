import unittest
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

if __name__ == "__main__":
    unittest.main()