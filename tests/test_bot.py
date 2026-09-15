import unittest
from handlers.tools import safe_calculate, SUPPORTED_OPERATORS
from handlers.start import get_main_menu_keyboard, get_welcome_text
from handlers.tools import get_tools_keyboard
from handlers.feedback import get_category_keyboard
import config


class TestBotComponents(unittest.TestCase):
    def test_safe_calculate_basic_arithmetic(self):
        self.assertEqual(safe_calculate("2 + 2"), 4)
        self.assertEqual(safe_calculate("10 - 3"), 7)
        self.assertEqual(safe_calculate("6 * 7"), 42)
        self.assertEqual(safe_calculate("15 / 3"), 5.0)
        self.assertEqual(safe_calculate("7 // 2"), 3)
        self.assertEqual(safe_calculate("7 % 3"), 1)
        self.assertEqual(safe_calculate("2 ** 4"), 16)
        self.assertEqual(safe_calculate("-5 + 12"), 7)

    def test_safe_calculate_precedence_and_grouping(self):
        self.assertEqual(safe_calculate("(2 + 3) * 4"), 20)
        self.assertEqual(safe_calculate("2 + 3 * 4"), 14)
        self.assertAlmostEqual(safe_calculate("3.5 * 2 + 1.5"), 8.5)

    def test_safe_calculate_division_by_zero(self):
        with self.assertRaises(ZeroDivisionError):
            safe_calculate("5 / 0")
        with self.assertRaises(ZeroDivisionError):
            safe_calculate("10 // 0")
        with self.assertRaises(ZeroDivisionError):
            safe_calculate("8 % 0")

    def test_safe_calculate_security_rejections(self):
        # Disallow arbitrary code or function calls
        with self.assertRaises(ValueError):
            safe_calculate("__import__('os').system('ls')")
        with self.assertRaises(ValueError):
            safe_calculate("open('/etc/passwd').read()")
        with self.assertRaises(ValueError):
            safe_calculate("x + 1")
        with self.assertRaises(ValueError):
            safe_calculate("'hello' + 'world'")

    def test_keyboards(self):
        main_kb = get_main_menu_keyboard()
        self.assertIsNotNone(main_kb.inline_keyboard)
        self.assertTrue(len(main_kb.inline_keyboard) >= 3)

        tools_kb = get_tools_keyboard()
        self.assertIsNotNone(tools_kb.inline_keyboard)
        self.assertTrue(len(tools_kb.inline_keyboard) >= 2)

        cat_kb = get_category_keyboard()
        self.assertIsNotNone(cat_kb.inline_keyboard)

    def test_welcome_text(self):
        text = get_welcome_text("Alice")
        self.assertIn("Alice", text)
        self.assertIn("Welcome", text)

    def test_uptime_str(self):
        uptime = config.get_uptime_str()
        self.assertIsInstance(uptime, str)
        self.assertTrue(uptime.endswith("s"))


if __name__ == "__main__":
    unittest.main()
