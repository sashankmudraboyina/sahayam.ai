import unittest
from handlers.start import get_home_keyboard, get_welcome_text
import config


class TestBotComponents(unittest.TestCase):
    def test_keyboards(self):
        home_kb = get_home_keyboard()
        self.assertIsNotNone(home_kb.inline_keyboard)
        self.assertTrue(len(home_kb.inline_keyboard) >= 2)

    def test_welcome_text(self):
        text = get_welcome_text("రాము")
        self.assertIn("రాము", text)
        self.assertIn("సహాయం", text)

    def test_uptime_str(self):
        uptime = config.get_uptime_str()
        self.assertIsInstance(uptime, str)
        self.assertTrue(uptime.endswith("s"))


if __name__ == "__main__":
    unittest.main()
