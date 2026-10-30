"""Unit tests for the Step-by-Step Eligibility Questioning Flow."""

import unittest
from services.eligibility_flow import (
    DOMAIN_SCHOLARSHIP,
    DOMAIN_AGRICULTURE,
    detect_domain,
    extract_slots_from_text,
    get_missing_slots,
    get_slot_question_and_buttons,
    match_eligible_schemes_for_profile,
    format_final_eligibility_report,
)


class TestEligibilityFlow(unittest.TestCase):
    def test_scholarship_domain_detection(self):
        self.assertEqual(detect_domain("నాకు స్కాలర్‌షిప్ కావాలి"), DOMAIN_SCHOLARSHIP)
        self.assertEqual(detect_domain("నేను బీటెక్ చదువుతున్నాను ఫీజు రీయింబర్స్మెంట్ ఎలా వస్తుంది?"), DOMAIN_SCHOLARSHIP)
        self.assertEqual(detect_domain("college student scholarship details"), DOMAIN_SCHOLARSHIP)

    def test_missing_slots_asked_one_by_one(self):
        # Turn 1: Vague initial query
        q1 = "నాకు స్కాలర్‌షిప్ కావాలి"
        domain = detect_domain(q1)
        slots = extract_slots_from_text(q1)
        missing = get_missing_slots(domain, slots)

        self.assertEqual(domain, DOMAIN_SCHOLARSHIP)
        self.assertEqual(missing, ["state", "course_level", "caste_category", "income_or_ration"])

        # Ask question 1: State
        next_slot = missing[0]
        self.assertEqual(next_slot, "state")
        q_text, buttons = get_slot_question_and_buttons(domain, next_slot)
        self.assertIn("రాష్ట్ర వివరాలు", q_text)
        self.assertTrue(any("తెలంగాణ" in b[0] for row in buttons for b in row))
        self.assertTrue(any("ఆంధ్రప్రదేశ్" in b[0] for row in buttons for b in row))

        # Turn 2: User answers State = Telangana
        slots = extract_slots_from_text("తెలంగాణ", slots)
        self.assertEqual(slots.get("state"), "Telangana")
        missing = get_missing_slots(domain, slots)
        self.assertEqual(missing[0], "course_level")

        # Ask question 2: Course
        next_slot = missing[0]
        q_text, buttons = get_slot_question_and_buttons(domain, next_slot)
        self.assertIn("చదువు వివరాలు", q_text)
        self.assertTrue(any("ఇంజనీరింగ్" in b[0] for row in buttons for b in row))

        # Turn 3: User answers Course = B.Tech / Engineering
        slots = extract_slots_from_text("నేను బీటెక్ ఇంజనీరింగ్ చదువుతున్నాను", slots)
        self.assertEqual(slots.get("course_level"), "engineering")
        missing = get_missing_slots(domain, slots)
        self.assertEqual(missing[0], "caste_category")

        # Ask question 3: Caste Category
        next_slot = missing[0]
        q_text, buttons = get_slot_question_and_buttons(domain, next_slot)
        self.assertIn("సామాజిక వర్గం", q_text)

        # Turn 4: User answers Caste = BC
        slots = extract_slots_from_text("మాది BC కేటగిరీ", slots)
        self.assertEqual(slots.get("caste_category"), "BC")
        missing = get_missing_slots(domain, slots)
        self.assertEqual(missing[0], "income_or_ration")

        # Ask question 4: Income
        next_slot = missing[0]
        q_text, buttons = get_slot_question_and_buttons(domain, next_slot)
        self.assertIn("ఆదాయ వివరాలు", q_text)

        # Turn 5: User answers White Ration Card = Yes
        slots = extract_slots_from_text("అవును తెల్ల రేషన్ కార్డు ఉంది", slots)
        self.assertEqual(slots.get("income_or_ration"), "eligible")
        missing = get_missing_slots(domain, slots)
        self.assertEqual(len(missing), 0, "All criteria must be collected now!")

        # Final match
        eligible = match_eligible_schemes_for_profile(domain, slots)
        self.assertTrue(len(eligible) >= 2)
        eligible_ids = [s["id"] for s in eligible]
        self.assertIn("ts_epass_scholarship", eligible_ids)

        report = format_final_eligibility_report(domain, slots, eligible)
        self.assertIn("స్కాలర్‌షిప్‌లు", report)
        self.assertIn("Telangana", report)
        self.assertIn("BC", report)
        self.assertIn("TS ePASS", report)

    def test_andhra_pradesh_scholarships_flow(self):
        slots = {
            "state": "Andhra Pradesh",
            "course_level": "engineering",
            "caste_category": "BC",
            "income_or_ration": "eligible",
        }
        eligible = match_eligible_schemes_for_profile(DOMAIN_SCHOLARSHIP, slots)
        eligible_ids = [s["id"] for s in eligible]
        self.assertIn("jagananna_vidya_deevena", eligible_ids)
        self.assertIn("ap_jagananna_vasathi_deevena", eligible_ids)

    def test_all_details_given_upfront(self):
        full_query = "నేను తెలంగాణలో బీటెక్ చదువుతున్నాను, మాది BC కేటగిరీ, తెల్ల రేషన్ కార్డు ఉంది, నాకు ఏ స్కాలర్‌షిప్ వస్తుంది?"
        domain = detect_domain(full_query)
        slots = extract_slots_from_text(full_query)
        missing = get_missing_slots(domain, slots)

        self.assertEqual(domain, DOMAIN_SCHOLARSHIP)
        self.assertEqual(len(missing), 0, "Should have zero missing slots when given upfront")

        eligible = match_eligible_schemes_for_profile(domain, slots)
        self.assertTrue(len(eligible) >= 2)


    def test_user_degree_student_query(self):
        # The user's query:
        q = "నేను 20 సంవత్సరాల అబ్బాయిని డిగ్రీ చేస్తున్నాను నాకు ఎలాంటి స్కాలర్షిప్స్ వస్తాయి"
        domain = detect_domain(q)
        self.assertEqual(domain, DOMAIN_SCHOLARSHIP)
        slots = extract_slots_from_text(q)
        self.assertEqual(slots.get("course_level"), "degree")

        missing = get_missing_slots(domain, slots)
        self.assertIn("state", missing)

        # Question 1: State
        next_slot = missing[0]
        q_text, buttons = get_slot_question_and_buttons(domain, next_slot, slots)
        self.assertIn("డిగ్రీ / డిప్లొమా", q_text)  # Recap present!

        # User replies "మాది ఏపీ"
        slots = extract_slots_from_text("మాది ఏపీ", slots, expected_slot="state")
        self.assertEqual(slots.get("state"), "Andhra Pradesh")

        # Question 2: Caste
        missing = get_missing_slots(domain, slots)
        self.assertEqual(missing[0], "caste_category")
        q_text, buttons = get_slot_question_and_buttons(domain, missing[0], slots)
        self.assertIn("Andhra Pradesh", q_text)

        # User replies "బీసీ"
        slots = extract_slots_from_text("నేను బీసీ", slots, expected_slot="caste_category")
        self.assertEqual(slots.get("caste_category"), "BC")

        # Question 3: Income / Ration card
        missing = get_missing_slots(domain, slots)
        self.assertEqual(missing[0], "income_or_ration")

        # User replies "తెల్ల రేషన్ కార్డు ఉంది"
        slots = extract_slots_from_text("తెల్ల రేషన్ కార్డు ఉంది", slots, expected_slot="income_or_ration")
        self.assertEqual(slots.get("income_or_ration"), "eligible")

        # Now all slots collected!
        missing = get_missing_slots(domain, slots)
        self.assertEqual(len(missing), 0)

        eligible = match_eligible_schemes_for_profile(domain, slots)
        eligible_ids = [s["id"] for s in eligible]
        self.assertIn("jagananna_vidya_deevena", eligible_ids)

    def test_ration_card_negative_cue(self):
        # Ensure "రేషన్ కార్డు లేదు" is NOT marked eligible
        slots = extract_slots_from_text("మాకు రేషన్ కార్డు లేదు")
        self.assertEqual(slots.get("income_or_ration"), "ineligible")

        slots_yes = extract_slots_from_text("మాకు తెల్ల రేషన్ కార్డు ఉంది")
        self.assertEqual(slots_yes.get("income_or_ration"), "eligible")

    def test_general_domain_prompt(self):
        from services.eligibility_flow import DOMAIN_GENERAL
        q = "నాకు ఏ ప్రభుత్వ పథకాలు వర్తిస్తాయి?"
        d = detect_domain(q)
        self.assertEqual(d, DOMAIN_GENERAL)
        q_text, buttons = get_slot_question_and_buttons(DOMAIN_GENERAL, "category")
        self.assertIn("నమస్కారం", q_text)
        self.assertTrue(any("రైతులు" in b[0] for row in buttons for b in row))
        self.assertTrue(len(buttons) >= 3)


if __name__ == "__main__":
    unittest.main()
