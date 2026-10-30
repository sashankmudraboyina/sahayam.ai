"""Unit tests ensuring the bot asks questions only when needed and avoids redundant questions."""

import unittest
from unittest.mock import AsyncMock, MagicMock
from telegram import Update, Message
from data.schemes import get_scheme_by_id
from services.matcher import find_scheme_by_name_or_query
from services.eligibility_flow import (
    DOMAIN_AGRICULTURE,
    DOMAIN_WOMEN,
    detect_domain,
    extract_slots_from_text,
    get_missing_slots,
)
from handlers.schemes_handler import process_citizen_utterance


class TestNonRedundantQuestioning(unittest.IsolatedAsyncioTestCase):
    def test_direct_scheme_identified_without_quiz(self):
        # A query mentioning PM Kisan directly must match the scheme and not require a quiz
        scheme = find_scheme_by_name_or_query("Tell me about PM Kisan")
        self.assertIsNotNone(scheme)
        self.assertEqual(scheme["id"], "pm_kisan")

        # Query mentioning Kalyana Lakshmi
        scheme2 = find_scheme_by_name_or_query("కళ్యాణ లక్ష్మి పత్రాలు వివరాలు")
        self.assertIsNotNone(scheme2)
        self.assertEqual(scheme2["id"], "kalyana_lakshmi")

    def test_full_information_upfront_requires_zero_questions(self):
        # When citizen gives all required info in Turn 1
        query = "మాది తెలంగాణ, నాకు ఇప్పుడే పెళ్లి అయింది. ఏమైనా పథకాలు వర్తిస్తాయా?"
        domain = detect_domain(query)
        self.assertEqual(domain, DOMAIN_WOMEN)

        slots = extract_slots_from_text(query)
        self.assertEqual(slots.get("state"), "Telangana")
        self.assertEqual(slots.get("welfare_type"), "marriage")

        missing = get_missing_slots(domain, slots)
        self.assertEqual(len(missing), 0, "No questions should be asked when all info is present!")

    def test_persistent_profile_prevents_duplicate_state_questions(self):
        # If user previously stated they are from Telangana
        citizen_profile = {"state": "Telangana"}

        # Now they ask for marriage assistance without mentioning state
        query = "నాకు ఇప్పుడే పెళ్లి అయింది, ఏమైనా పథకాలు ఉన్నాయా?"
        slots = extract_slots_from_text(query, current_slots=citizen_profile)
        self.assertEqual(slots.get("state"), "Telangana")
        self.assertEqual(slots.get("welfare_type"), "marriage")

        missing = get_missing_slots(DOMAIN_WOMEN, slots)
        self.assertEqual(len(missing), 0, "State must not be asked again if already known!")

    async def test_process_citizen_utterance_direct_scheme_answers_without_session(self):
        update = MagicMock(spec=Update)
        message = MagicMock(spec=Message)
        message.reply_text = AsyncMock()
        message.message_id = 101
        update.message = message
        update.effective_chat = MagicMock()
        update.effective_chat.id = 12345

        context = MagicMock()
        context.bot.send_chat_action = AsyncMock()
        context.user_data = {"language": "en"}

        await process_citizen_utterance(update, context, user_text="Tell me about PM Kisan")

        # Must not initiate an eligibility questionnaire session
        self.assertIsNone(context.user_data.get("eligibility_session"))
        message.reply_text.assert_called()
        args, kwargs = message.reply_text.call_args
        reply = kwargs.get("text") or args[0]
        self.assertIn("Pradhan Mantri Kisan Samman Nidhi", reply)


if __name__ == "__main__":
    unittest.main()
