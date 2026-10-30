"""Unit tests for Bilingual Support (Telugu and English) across the Sahayam bot."""

import unittest
from unittest.mock import AsyncMock, MagicMock
from telegram import Update, Message
from data.schemes import get_scheme_by_id, get_all_categories
from handlers.start import language_command, get_home_keyboard, get_welcome_text
from services.eligibility_flow import (
    DOMAIN_SCHOLARSHIP,
    get_slot_question_and_buttons,
    format_collected_profile_badges,
    format_final_eligibility_report,
    match_eligible_schemes_for_profile,
)
from services.matcher import (
    format_scheme_detailed_telugu,
    format_multiple_schemes_summary,
)


class TestBilingualSupport(unittest.IsolatedAsyncioTestCase):
    def test_slot_question_and_buttons_bilingual(self):
        # Telugu (default)
        q_te, btns_te = get_slot_question_and_buttons(DOMAIN_SCHOLARSHIP, "state", lang="te")
        self.assertIn("రాష్ట్ర వివరాలు", q_te)
        self.assertTrue(any("తెలంగాణ" in b[0] for row in btns_te for b in row))

        # English
        q_en, btns_en = get_slot_question_and_buttons(DOMAIN_SCHOLARSHIP, "state", lang="en")
        self.assertIn("State Details", q_en)
        self.assertTrue(any("Telangana" in b[0] for row in btns_en for b in row))
        self.assertTrue(any("Andhra Pradesh" in b[0] for row in btns_en for b in row))

    def test_badges_bilingual(self):
        slots = {"state": "Telangana", "caste_category": "BC"}
        badge_te = format_collected_profile_badges(slots, lang="te")
        self.assertIn("రాష్ట్రం:", badge_te)
        self.assertIn("వర్గం:", badge_te)

        badge_en = format_collected_profile_badges(slots, lang="en")
        self.assertIn("State:", badge_en)
        self.assertIn("Category:", badge_en)

    def test_final_report_english(self):
        slots = {
            "state": "Telangana",
            "course_level": "engineering",
            "caste_category": "BC",
            "income_or_ration": "eligible",
        }
        eligible = match_eligible_schemes_for_profile(DOMAIN_SCHOLARSHIP, slots)
        report_en = format_final_eligibility_report(DOMAIN_SCHOLARSHIP, slots, eligible, lang="en")
        self.assertIn("Eligible Scholarships for You", report_en)
        self.assertIn("Why you qualify", report_en)
        self.assertIn("Benefits:", report_en)
        self.assertIn("Official Website:", report_en)

    def test_format_scheme_detailed_english(self):
        pm_kisan = get_scheme_by_id("pm_kisan")
        self.assertIsNotNone(pm_kisan)
        output_en = format_scheme_detailed_telugu(pm_kisan, "You qualify as a small farmer.", lang="en")
        self.assertIn("Pradhan Mantri Kisan Samman Nidhi", output_en)
        self.assertIn("Category:", output_en)
        self.assertIn("Benefits:", output_en)
        self.assertIn("Required Documents:", output_en)
        self.assertIn("How to Apply", output_en)

    def test_format_multiple_schemes_summary_english(self):
        pm_kisan = get_scheme_by_id("pm_kisan")
        summary_en = format_multiple_schemes_summary([(pm_kisan, 10.0, "Eligible small farmer.")], lang="en")
        self.assertIn("Sahayam (సహాయం.ai) - Matching Welfare Schemes:", summary_en)
        self.assertIn("Benefit:", summary_en)
        self.assertIn("Eligibility:", summary_en)

    def test_get_all_categories_has_english(self):
        cats = get_all_categories()
        for c in cats:
            self.assertIn("name_en", c)
            self.assertIn("name_te", c)
            self.assertIn("key", c)

    def test_home_keyboard_bilingual(self):
        kb_te = get_home_keyboard(lang="te")
        kb_en = get_home_keyboard(lang="en")
        self.assertTrue(any("Language" in btn.text for row in kb_te.inline_keyboard for btn in row))
        self.assertTrue(any("Language" in btn.text for row in kb_en.inline_keyboard for btn in row))
        self.assertTrue(any("Eligibility Wizard" in btn.text for row in kb_en.inline_keyboard for btn in row))

    def test_welcome_text_bilingual(self):
        w_te = get_welcome_text("Ravi", lang="te")
        w_en = get_welcome_text("Ravi", lang="en")
        self.assertIn("నమస్కారం", w_te)
        self.assertIn("Welcome", w_en)
        self.assertIn("Sahayam.ai", w_en)

    async def test_language_command_sends_keyboard(self):
        update = MagicMock(spec=Update)
        message = MagicMock(spec=Message)
        message.reply_text = AsyncMock()
        update.message = message

        context = MagicMock()
        context.user_data = {}

        await language_command(update, context)
        message.reply_text.assert_called_once()
        args, kwargs = message.reply_text.call_args
        markup = kwargs.get("reply_markup")
        self.assertIsNotNone(markup)
        all_cb_data = [btn.callback_data for row in markup.inline_keyboard for btn in row]
        self.assertIn("lang:te", all_cb_data)
        self.assertIn("lang:en", all_cb_data)

    def test_marriage_utterance_flow(self):
        from services.eligibility_flow import detect_domain, extract_slots_from_text, get_missing_slots, match_eligible_schemes_for_profile, DOMAIN_WOMEN
        user_utterance = "నాకు ఇప్పుడే పెళ్లి అయింది నాకు ఏమేం స్కీమ్స్ గవర్నమెంట్ నుండి వస్తాయో చెప్పు"
        domain = detect_domain(user_utterance)
        self.assertEqual(domain, DOMAIN_WOMEN)

        slots = extract_slots_from_text(user_utterance)
        self.assertEqual(slots.get("welfare_type"), "marriage")
        missing = get_missing_slots(domain, slots)
        self.assertEqual(missing, ["state"])

        # After user selects state
        slots["state"] = "Telangana"
        eligible = match_eligible_schemes_for_profile(domain, slots)
        ids = [s["id"] for s in eligible]
        self.assertIn("kalyana_lakshmi", ids)

    def test_voice_recognized_header(self):
        from handlers.schemes_handler import format_voice_recognized_header
        from services.tts_service import prepare_text_for_speech

        hdr_te = format_voice_recognized_header("నాకు ఇప్పుడే పెళ్లి అయింది", lang="te")
        self.assertIn("మీరు మాట్లాడినది (గుర్తించబడింది):", hdr_te)
        self.assertIn("నాకు ఇప్పుడే పెళ్లి అయింది", hdr_te)

        hdr_en = format_voice_recognized_header("I just got married", lang="en")
        self.assertIn("Understood voice query:", hdr_en)
        self.assertIn("I just got married", hdr_en)

        full_msg = hdr_te + "📍 రాష్ట్ర వివరాలు:\nదయచేసి మీ రాష్ట్రాన్ని ఎంచుకోండి."
        clean_speech = prepare_text_for_speech(full_msg)
        self.assertNotIn("మీరు మాట్లాడినది", clean_speech)
        self.assertIn("రాష్ట్ర వివరాలు", clean_speech)


if __name__ == "__main__":
    unittest.main()
