import unittest
from services.matcher import extract_entities, match_schemes, format_scheme_detailed_telugu
from data.schemes import SCHEMES, get_scheme_by_id, get_all_categories


class TestTeluguSchemePlatform(unittest.TestCase):
    def test_farmer_two_acres_example(self):
        """Tests the exact prompt given in the user description:
        'నాకు రెండు ఎకరాల పొలం ఉంది. నేను చిన్న రైతును. నాకు ఏ ప్రభుత్వ పథకాలు వర్తిస్తాయి?'
        """
        query = "నాకు రెండు ఎకరాల పొలం ఉంది. నేను చిన్న రైతును. నాకు ఏ ప్రభుత్వ పథకాలు వర్తిస్తాయి?"
        entities = extract_entities(query)

        # 1. Entity extraction verification
        self.assertEqual(entities["land_acres"], 2.0)
        self.assertTrue(entities["is_small_farmer"])
        self.assertIn("agriculture", entities["categories"])

        # 2. Scheme matching verification
        matched = match_schemes(query)
        self.assertTrue(len(matched) >= 3, "Should match at least 3 agricultural schemes")

        top_scheme, score, reason = matched[0]
        self.assertEqual(top_scheme["id"], "pm_kisan")
        self.assertIn("2.0 ఎకరాల", reason)
        self.assertIn("పూర్తి అర్హులు", reason)

        # 3. Verify all 7 required components are present in detailed format
        output = format_scheme_detailed_telugu(top_scheme, reason)

        # Relevant scheme name
        self.assertIn("పీఎం కిసాన్", output)
        # Eligibility
        self.assertIn("అర్హతలు", output)
        # Benefits
        self.assertIn("ప్రయోజనాలు", output)
        self.assertIn("6,000", output)
        # Required documents
        self.assertIn("కావలసిన పత్రాలు", output)
        self.assertIn("ఆధార్", output)
        self.assertIn("పాస్ పుస్తకం", output)
        # Application procedure
        self.assertIn("దరఖాస్తు విధానం", output)
        # Official application link
        self.assertIn("pmkisan.gov.in", output)
        # Why user qualifies
        self.assertIn("మీకు ఎందుకు వర్తిస్తుంది", output)

    def test_senior_pension_query(self):
        query = "మా ఇంట్లో వృద్ధులకు 65 ఏళ్లు. ఆసరా వృద్ధాప్య పెన్షన్ ఎలా పొందాలి?"
        entities = extract_entities(query)
        self.assertIn("pension", entities["categories"])

        matched = match_schemes(query)
        self.assertTrue(any(s["id"] == "aasara_pension" for s, _, _ in matched))

    def test_health_query(self):
        query = "మాకు రేషన్ కార్డు ఉంది, హాస్పిటల్ లో ఉచిత వైద్యం మరియు ఆపరేషన్ కొరకు పథకం ఏమిటి?"
        entities = extract_entities(query)
        self.assertIn("health", entities["categories"])

        matched = match_schemes(query)
        self.assertTrue(any(s["id"] == "aarogyasri" for s, _, _ in matched))

    def test_street_vendor_loan_query(self):
        query = "నేను తోపుడు బండిపై వీధి వ్యాపారం చేస్తున్నాను, రుణం కావాలి"
        entities = extract_entities(query)
        self.assertIn("business", entities["categories"])

        matched = match_schemes(query)
        self.assertTrue(any(s["id"] == "pm_svanidhi" for s, _, _ in matched))

    def test_categories_integrity(self):
        cats = get_all_categories()
        self.assertTrue(len(cats) >= 6)
        for cat in cats:
            self.assertTrue(any(s["category"] == cat["key"] for s in SCHEMES))

    def test_html_sanitizer(self):
        from services.html_sanitizer import (
            clean_telegram_html,
            balance_telegram_tags,
            strip_html_tags,
            prepare_telegram_message,
        )
        raw = "<h3>శీర్షిక</h3><p>రైతులకు & ప్రజలకు <b>సహాయం<br>వివరాలు: <i>ముఖ్యమైనవి"
        cleaned = prepare_telegram_message(raw)
        # Should convert h3 to bold, escape ampersands, and close unclosed tags
        self.assertIn("<b>శీర్షిక</b>", cleaned)
        self.assertIn("&amp;", cleaned)
        self.assertTrue(cleaned.endswith("</i>") or "</i>" in cleaned)

        # Plain text stripped version must not have any < or >
        stripped = strip_html_tags(cleaned)
        self.assertNotIn("<", stripped)
        self.assertNotIn(">", stripped)
        self.assertIn("రైతులకు & ప్రజలకు సహాయం", stripped)

    def test_concise_multiple_schemes_summary(self):
        from services.matcher import format_multiple_schemes_summary, match_schemes
        from handlers.schemes_handler import build_scheme_actions_keyboard

        query = "నాకు రెండు ఎకరాల పొలం ఉంది. నేను చిన్న రైతును. నాకు ఏ ప్రభుత్వ పథకాలు వర్తిస్తాయి?"
        matched = match_schemes(query)
        self.assertTrue(len(matched) > 1)

        summary_text = format_multiple_schemes_summary(matched)
        # Should contain scheme names
        self.assertIn("పీఎం కిసాన్", summary_text)
        self.assertIn("ప్రయోజనం:", summary_text)
        self.assertIn("అర్హత:", summary_text)
        # Should not dump 10-line document lists in summary
        self.assertNotIn("బ్యాంక్ పాస్ పుస్తకం జిరాక్స్", summary_text)
        # Should prompt about clicking buttons for full details
        self.assertIn("పూర్తి వివరాలు", summary_text)

        # Verify keyboard generated for multiple schemes includes "పూర్తి వివరాలు" buttons
        kb = build_scheme_actions_keyboard(matched_schemes=matched)
        button_texts = [btn.text for row in kb.inline_keyboard for btn in row]
        button_callbacks = [btn.callback_data for row in kb.inline_keyboard for btn in row if btn.callback_data]

        # Check that dedicated full details button exists for top schemes
        self.assertTrue(any("పూర్తి వివరాలు" in t for t in button_texts))
        self.assertIn(f"sch:{matched[0][0]['id']}", button_callbacks)
        self.assertIn(f"sch:{matched[1][0]['id']}", button_callbacks)

    def test_dataset_loading_all_97_schemes(self):
        from data.dataset_loader import load_dataset_schemes
        from pathlib import Path

        schemes = load_dataset_schemes()
        self.assertEqual(len(schemes), 97, "Should load all 97 schemes from govt_schemes_dataset.md")

        central_count = len([s for s in schemes if s["jurisdiction"] == "Central"])
        ts_count = len([s for s in schemes if s["jurisdiction"] == "Telangana"])
        ap_count = len([s for s in schemes if s["jurisdiction"] == "Andhra Pradesh"])

        self.assertEqual(central_count, 38, "Part 1 should have 38 Central schemes")
        self.assertEqual(ts_count, 28, "Part 2 should have 28 Telangana schemes")
        self.assertEqual(ap_count, 31, "Part 3 should have 31 Andhra Pradesh schemes")

        # Every scheme must have required fields
        for s in schemes:
            self.assertTrue(s["id"], f"Scheme {s['name_en']} missing id")
            self.assertTrue(s["name_te"], f"Scheme {s['id']} missing name_te")
            self.assertTrue(s["name_en"], f"Scheme {s['id']} missing name_en")
            self.assertTrue(s["category"], f"Scheme {s['id']} missing category")
            self.assertTrue(s["benefits_te"], f"Scheme {s['id']} missing benefits_te")
            self.assertTrue(s["eligibility_te"], f"Scheme {s['id']} missing eligibility_te")
            self.assertTrue(len(s["documents_te"]) > 0, f"Scheme {s['id']} missing documents")
            self.assertTrue(s["official_link"].startswith("http"), f"Scheme {s['id']} invalid link")

    def test_telangana_and_andhra_specific_matching(self):
        # Telangana Mahalakshmi
        ts_res = match_schemes("తెలంగాణలో మహిళలకు మహాలక్ష్మి పథకం ద్వారా ఏమి వస్తుంది?")
        self.assertTrue(any(s["id"] == "ts_mahalakshmi" for s, _, _ in ts_res[:3]))

        # AP Talliki Vandanam (formerly Amma Vodi)
        ap_res = match_schemes("ఆంధ్రప్రదేశ్ లో తల్లికి వందనం అమ్మ ఒడి పథకం వివరాలు")
        self.assertTrue(any(s["id"] == "ap_talliki_vandanam" for s, _, _ in ap_res[:3]))

        # AP Deepam 2.0
        deepam_res = match_schemes("ఆంధ్రప్రదేశ్ లో ఉచిత గ్యాస్ సిలిండర్ల దీపం 2.0 పథకం")
        self.assertTrue(any(s["id"] == "ap_deepam_2" for s, _, _ in deepam_res[:3]))

        # AP Annadata Sukhibhava (formerly Rythu Bharosa)
        annadata_res = match_schemes("ఆంధ్రప్రదేశ్ లో రైతులకు అన్నదాత సుఖీభవ పెట్టుబడి సాయం")
        self.assertTrue(any(s["id"] == "ap_annadata_sukhibhava" for s, _, _ in annadata_res[:3]))

    def test_irrelevant_features_removed(self):
        from pathlib import Path
        base_dir = Path(__file__).resolve().parent.parent
        self.assertFalse((base_dir / "handlers" / "tools.py").exists(), "handlers/tools.py must be deleted")
        self.assertFalse((base_dir / "handlers" / "feedback.py").exists(), "handlers/feedback.py must be deleted")


if __name__ == "__main__":
    unittest.main()

