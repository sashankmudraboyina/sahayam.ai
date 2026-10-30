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


    def test_voice_requested_detection(self):
        from handlers.schemes_handler import is_voice_requested
        self.assertTrue(is_voice_requested("నాకు వాయిస్‌లో సమాధానం చెప్పండి"))
        self.assertTrue(is_voice_requested("ఆడియో రూపంలో కావాలి"))
        self.assertTrue(is_voice_requested("వినాలని ఉంది"))
        self.assertTrue(is_voice_requested("please reply in voice"))
        self.assertTrue(is_voice_requested("audio message"))
        self.assertFalse(is_voice_requested("నాకు 2 ఎకరాల పొలం ఉంది"))

    def test_tts_text_preparation(self):
        from services.tts_service import prepare_text_for_speech
        raw = "<b>పీఎం కిసాన్ పథకం</b>: రైతులకు రూ. 6,000. వెబ్‌సైట్: https://pmkisan.gov.in/ • ఆధార్ అవసరం."
        prepared = prepare_text_for_speech(raw)
        self.assertNotIn("<b>", prepared)
        self.assertNotIn("https://", prepared)
        self.assertNotIn("•", prepared)
        self.assertIn("పీఎం కిసాన్ పథకం", prepared)

    def test_scheme_keyboard_has_voice_button(self):
        from handlers.schemes_handler import build_scheme_actions_keyboard
        kb = build_scheme_actions_keyboard()
        callbacks = [btn.callback_data for row in kb.inline_keyboard for btn in row if btn.callback_data]
        self.assertIn("voice:speak", callbacks)


    def test_transcribe_voice_empty(self):
        from services.ai_engine import transcribe_voice
        self.assertIsNone(transcribe_voice(b""))


if __name__ == "__main__":
    unittest.main()
