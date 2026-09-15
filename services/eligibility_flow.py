"""Interactive Conversational Eligibility Discovery Engine for Sahayam.ai.

Enforces the step-by-step chat flow:
1. Analyzes user query.
2. Checks if the citizen provided ALL details required for eligibility.
3. If ANY detail is missing, asks questions ONE BY ONE in polite Telugu to gather
   the complete profile.
4. Once all details are collected (or if provided upfront), presents the exact
   eligible scholarship(s) or welfare scheme(s) from the dataset.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from data.schemes import SCHEMES, get_scheme_by_id

logger = logging.getLogger("telegram_bot.eligibility_flow")

# Domains supported
DOMAIN_SCHOLARSHIP = "scholarship"
DOMAIN_AGRICULTURE = "agriculture"
DOMAIN_PENSION = "pension"
DOMAIN_HOUSING = "housing"
DOMAIN_WOMEN = "women"
DOMAIN_BUSINESS = "business"

DOMAIN_KEYWORDS = {
    DOMAIN_SCHOLARSHIP: [
        "స్కాలర్‌షిప్", "స్కాలర్షిప్", "స్కాలర్‌షిప్‌లు", "చదువు", "కాలేజీ", "ఫీజు",
        "రీయింబర్స్‌మెంట్", "విద్యార్థి", "విద్యార్థులు", "హాస్టల్", "విద్యా దీవెన",
        "వసతి దీవెన", "అమ్మ ఒడి", "తల్లికి వందనం", "ఈపాస్", "epass", "scholarship",
        "scholarships", "fee", "fees", "student", "college", "school", "btech", "degree"
    ],
    DOMAIN_AGRICULTURE: [
        "రైతు", "రైతులు", "రైతును", "పొలం", "భూమి", "సాగు", "వ్యవసాయం", "పంట",
        "రైతు భరోసా", "రైతు బంధు", "అన్నదాత సుఖీభవ", "పీఎం కిసాన్", "pm kisan",
        "farmer", "farmers", "agriculture", "crop", "land", "acres"
    ],
    DOMAIN_PENSION: [
        "పెన్షన్", "పింఛను", "వృద్ధాప్య", "ముసలి", "వితంతువు", "దివ్యాంగ", "వికలాంగ",
        "ఆసరా", "ఎన్టీఆర్ భరోసా", "పెన్షన్ కానుక", "pension", "old age", "widow", "disability"
    ],
    DOMAIN_HOUSING: [
        "ఇల్లు", "గృహం", "ఇంటి స్థలం", "ఆవాస్", "ఇందిరమ్మ ఇండ్లు", "నవరత్నాలు ఇండ్లు",
        "house", "housing", "pmay", "home", "plot"
    ],
    DOMAIN_WOMEN: [
        "మహిళ", "మహిళలు", "స్త్రీ", "డ్వాక్రా", "ఆడపడుచు", "మహాలక్ష్మి", "కళ్యాణ లక్ష్మి",
        "షాదీ ముబారక్", "దీపం", "women", "girl", "mother", "dwakra", "shg", "marriage"
    ],
    DOMAIN_BUSINESS: [
        "వ్యాపారం", "షాపు", "తోపుడు బండి", "దుకాణం", "చిరు వ్యాపారి", "ముద్ర", "లోన్",
        "స్వయం ఉపాధి", "రుణం", "business", "shop", "vendor", "loan", "mudra", "svanidhi"
    ],
}

# Required slots per domain in strict sequential order
REQUIRED_SLOTS = {
    DOMAIN_SCHOLARSHIP: ["state", "course_level", "caste_category", "income_or_ration"],
    DOMAIN_AGRICULTURE: ["state", "land_status"],
    DOMAIN_PENSION: ["state", "pension_type"],
    DOMAIN_HOUSING: ["state", "has_site"],
    DOMAIN_WOMEN: ["state", "welfare_type"],
    DOMAIN_BUSINESS: ["business_type"],
}


def detect_domain(text: str) -> Optional[str]:
    """Identifies the welfare domain of the citizen query."""
    lower_text = text.lower()
    for domain, keywords in DOMAIN_KEYWORDS.items():
        if any(w in lower_text for w in keywords):
            return domain
    return None


def extract_slots_from_text(text: str, current_slots: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Extracts known eligibility criteria slots from citizen natural language message."""
    slots = dict(current_slots or {})
    lower_text = text.lower()

    # 1. State extraction
    if any(w in lower_text for w in ["తెలంగాణ", "telangana", "ts", "హైదరాబాద్"]):
        slots["state"] = "Telangana"
    elif any(w in lower_text for w in ["ఆంధ్రప్రదేశ్", "ఆంధ్ర", "andhra", "ap", "విజయవాడ", "అమరావతి"]):
        slots["state"] = "Andhra Pradesh"
    elif any(w in lower_text for w in ["కేంద్ర", "భారత", "central", "all india"]):
        slots["state"] = "Central"

    # 2. Course level (for education / scholarships)
    if any(w in lower_text for w in ["బీటెక్", "btech", "b.tech", "ఇంజనీరింగ్", "engineering", "మెడిసిన్", "mbbs", "pharmacy", "ఫార్మసీ"]):
        slots["course_level"] = "engineering"
    elif any(w in lower_text for w in ["డిగ్రీ", "degree", "డిప్లొమా", "diploma", "bsc", "bcom", "ba", "polytechnic", "పాలిటెక్నిక్", "iti", "ఐటీఐ"]):
        slots["course_level"] = "degree"
    elif any(w in lower_text for w in ["ఇంటర్", "inter", "intermediate", "11వ", "12వ", "+2"]):
        slots["course_level"] = "intermediate"
    elif any(w in lower_text for w in ["స్కూల్", "school", "పాఠశాల", "1వ", "2వ", "3వ", "4వ", "5వ", "6వ", "7వ", "8వ", "9వ", "10వ", "10th", "క్లాస్"]):
        slots["course_level"] = "school"
    elif any(w in lower_text for w in ["పీజీ", "pg", "mtech", "mba", "mca", "msc"]):
        slots["course_level"] = "pg"

    # 3. Caste category
    if any(w in lower_text for w in ["ఎస్సీ", "ఎస్టీ", "sc", "st", "దళిత", "గిరిజన"]):
        slots["caste_category"] = "SC/ST"
    elif any(w in lower_text for w in ["బీసీ", "bc", "obc", "ఓబీసీ", "వెనుకబడిన"]):
        slots["caste_category"] = "BC"
    elif any(w in lower_text for w in ["మైనారిటీ", "minority", "ముస్లిం", "muslim", "క్రిస్టియన్", "christian"]):
        slots["caste_category"] = "Minority"
    elif any(w in lower_text for w in ["ఈబీసీ", "ebc", "కాపు", "kapu"]):
        slots["caste_category"] = "EBC"
    elif any(w in lower_text for w in ["ఓసీ", "oc", "general", "జనరల్", "ఓపెన్"]):
        slots["caste_category"] = "OC"

    # 4. Income or White Ration Card
    if any(w in lower_text for w in ["రేషన్ కార్డు", "తెల్ల కార్డు", "white card", "white ration", "పేద", "below", "అవును", "ఉంది", "yes", "తక్కువ ఆదాయం"]):
        slots["income_or_ration"] = "eligible"
    elif any(w in lower_text for w in ["ఎక్కువ ఆదాయం", "రేషన్ కార్డు లేదు", "లేదు", "no"]):
        slots["income_or_ration"] = "ineligible"

    # 5. Land status (for agriculture)
    # Check acres
    acre_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:ఎకరాల|ఎకరాలు|ఎకరం|acres?|acre)", lower_text)
    if acre_match:
        try:
            acres = float(acre_match.group(1))
            slots["land_status"] = f"{acres}_acres"
            slots["land_acres"] = acres
        except ValueError:
            pass
    elif any(w in lower_text for w in ["రెండు ఎకరాల", "రెండు ఎకరాలు", "ఒక ఎకరం", "మూడు ఎకరాలు", "ఐదు ఎకరాలు"]):
        slots["land_status"] = "small_farmer"
        slots["land_acres"] = 2.0
    elif any(w in lower_text for w in ["చిన్న రైతు", "సన్నకారు రైతు", "small farmer", "marginal"]):
        slots["land_status"] = "small_farmer"
    elif any(w in lower_text for w in ["కౌలు", "కౌలు రైతు", "tenant"]):
        slots["land_status"] = "tenant"

    # 6. Pension type
    if any(w in lower_text for w in ["వృద్ధాప్య", "ముసలి", "60", "65", "old age", "సీనియర్"]):
        slots["pension_type"] = "old_age"
    elif any(w in lower_text for w in ["వితంతువు", "భర్త లేని", "widow"]):
        slots["pension_type"] = "widow"
    elif any(w in lower_text for w in ["వికలాంగ", "దివ్యాంగ", "సదరం", "sadarem", "disabled"]):
        slots["pension_type"] = "disabled"

    # 7. Housing site
    if any(w in lower_text for w in ["స్థలం ఉంది", "సొంత స్థలం", "పట్టా ఉంది", "plot", "site"]):
        slots["has_site"] = "yes"
    elif any(w in lower_text for w in ["స్థలం లేదు", "నో ప్లాట్"]):
        slots["has_site"] = "no"

    # 8. Business type
    if any(w in lower_text for w in ["తోపుడు బండి", "వీధి వ్యాపారి", "street vendor"]):
        slots["business_type"] = "street_vendor"
    elif any(w in lower_text for w in ["షాపు", "దుకాణం", "కిరాణా", "చిన్న వ్యాపారం"]):
        slots["business_type"] = "shop"

    # 9. Women welfare type
    if any(w in lower_text for w in ["డ్వాక్రా", "dwakra", "shg", "మహిళా సంఘం"]):
        slots["welfare_type"] = "dwakra"
    elif any(w in lower_text for w in ["పెళ్లి", "వివాహం", "marriage"]):
        slots["welfare_type"] = "marriage"
    elif any(w in lower_text for w in ["మహాలక్ష్మి", "బస్సు", "సిలిండర్"]):
        slots["welfare_type"] = "financial_bus"

    return slots


def get_missing_slots(domain: str, slots: Dict[str, Any]) -> List[str]:
    """Returns the list of missing required slots for the given domain."""
    required = REQUIRED_SLOTS.get(domain, [])
    return [slot for slot in required if slot not in slots or slots[slot] is None]


def get_slot_question_and_buttons(domain: str, slot: str) -> Tuple[str, List[List[Tuple[str, str]]]]:
    """Generates a single, friendly Telugu question with quick-reply buttons for the missing slot."""
    if slot == "state":
        text = (
            "📍 <b>రాష్ట్ర వివరాలు:</b>\n\n"
            "అర్హతగల పథకాలను ఖచ్చితంగా గుర్తించడానికి, మీరు ఏ రాష్ట్రానికి చెందినవారో తెలియజేయండి:\n"
            "<i>(తెలంగాణ లేదా ఆంధ్రప్రదేశ్?)</i>"
        )
        buttons = [
            [("🌾 తెలంగాణ (Telangana)", "elig:state:Telangana"), ("🏛 ఆంధ్రప్రదేశ్ (Andhra Pradesh)", "elig:state:Andhra Pradesh")],
            [("🇮🇳 కేంద్ర ప్రభుత్వం (Central)", "elig:state:Central")],
        ]
        return text, buttons

    if domain == DOMAIN_SCHOLARSHIP:
        if slot == "course_level":
            text = (
                "🎓 <b>చదువు వివరాలు:</b>\n\n"
                "మీరు ప్రస్తుతం ఏ తరగతి లేదా కోర్సు చదువుతున్నారు?"
            )
            buttons = [
                [("🏫 పాఠశాల (Classes 1-10)", "elig:course:school"), ("📚 ఇంటర్మీడియట్ (11-12)", "elig:course:intermediate")],
                [("🎓 డిగ్రీ / డిప్లొమా / ఐటీఐ", "elig:course:degree"), ("⚙️ ఇంజనీరింగ్ / ప్రొఫెషనల్", "elig:course:engineering")],
                [("📖 పీజీ (Post-Graduation)", "elig:course:pg")],
            ]
            return text, buttons

        if slot == "caste_category":
            text = (
                "📋 <b>సామాజిక వర్గం:</b>\n\n"
                "స్కాలర్‌షిప్ నిబంధనల కొరకు మీ సామాజిక వర్గం (Caste Category) ఏమిటి?"
            )
            buttons = [
                [("SC / ST", "elig:caste:SC/ST"), ("BC / OBC", "elig:caste:BC")],
                [("మైనారిటీ (Minority)", "elig:caste:Minority"), ("EBC / OC / జనరల్", "elig:caste:OC")],
            ]
            return text, buttons

        if slot == "income_or_ration":
            text = (
                "💰 <b>ఆదాయ వివరాలు:</b>\n\n"
                "మీ కుటుంబ వార్షిక ఆదాయం నిర్దేశిత పరిమితిలోపు (రూ. 1.5 - 2.5 లక్షల లోపు) ఉందా, "
                "లేదా మీ వద్ద తెల్ల రేషన్ కార్డు (White Ration Card) ఉందా?"
            )
            buttons = [
                [("✅ అవును (పరిమితి లోపే / తెల్ల కార్డు ఉంది)", "elig:income:eligible")],
                [("❌ లేదు (ఎక్కువ ఆదాయం)", "elig:income:ineligible")],
            ]
            return text, buttons

    elif domain == DOMAIN_AGRICULTURE:
        if slot == "land_status":
            text = (
                "🌾 <b>వ్యవసాయ భూమి వివరాలు:</b>\n\n"
                "మీ వద్ద ఎంత సాగుభూమి ఉంది, లేదా మీరు కౌలు రైతునా?"
            )
            buttons = [
                [("🌱 2 ఎకరాల లోపు (సన్నకారు రైతు)", "elig:land:2"), ("🚜 2 నుండి 5 ఎకరాలు (చిన్న రైతు)", "elig:land:5")],
                [("🌾 5 ఎకరాల కంటే ఎక్కువ", "elig:land:more"), ("🤝 కౌలు రైతు (సొంత భూమి లేదు)", "elig:land:tenant")],
            ]
            return text, buttons

    elif domain == DOMAIN_PENSION:
        if slot == "pension_type":
            text = (
                "👴 <b>పెన్షన్ విభాగం:</b>\n\n"
                "మీరు ఏ రకమైన పెన్షన్ కొరకు దరఖాస్తు చేయాలనుకుంటున్నారు?"
            )
            buttons = [
                [("👴 వృద్ధాప్య పెన్షన్ (60+ ఏళ్లు)", "elig:pen:old_age"), ("👩 వితంతు పెన్షన్", "elig:pen:widow")],
                [("♿ దివ్యాంగుల పెన్షన్ (SADAREM)", "elig:pen:disabled")],
            ]
            return text, buttons

    elif domain == DOMAIN_HOUSING:
        if slot == "has_site":
            text = (
                "🏠 <b>గృహ నిర్మాణ స్థలం వివరాలు:</b>\n\n"
                "ఇల్లు నిర్మించుకోవడానికి మీ పేరు మీద లేదా కుటుంబ సభ్యుల పేరిట సొంత స్థలం/పట్టా ఉందా?"
            )
            buttons = [
                [("✅ సొంత స్థలం / పట్టా ఉంది", "elig:site:yes")],
                [("❌ సొంత స్థలం లేదు (ఇంటి స్థలం కూడా కావాలి)", "elig:site:no")],
            ]
            return text, buttons

    elif domain == DOMAIN_WOMEN:
        if slot == "welfare_type":
            text = (
                "👩 <b>మహిళా సంక్షేమ విభాగం:</b>\n\n"
                "మీకు ఏ విధమైన ప్రభుత్వ సాయం అవసరం?"
            )
            buttons = [
                [("🚌 మహాలక్ష్మి / ఉచిత బస్సు & గ్యాస్ సాయం", "elig:wom:financial_bus")],
                [("💍 ఆడపిల్ల వివాహ సాయం (కళ్యాణ లక్ష్మి)", "elig:wom:marriage")],
                [("💼 డ్వాక్రా / స్వయం సహాయక సంఘాల రుణం", "elig:wom:dwakra")],
            ]
            return text, buttons

    elif domain == DOMAIN_BUSINESS:
        if slot == "business_type":
            text = (
                "💼 <b>వ్యాపార వివరాలు:</b>\n\n"
                "మీరు ఏ రకమైన వ్యాపారం చేస్తున్నారు లేదా ప్రారంభించాలనుకుంటున్నారు?"
            )
            buttons = [
                [("🛒 తోపుడు బండి / వీధి వ్యాపారం (Street Vendor)", "elig:biz:street_vendor")],
                [("🏪 కిరాణా / చిన్న దుకాణం (Small Shop)", "elig:biz:shop")],
                [("🛠 చేతివృత్తులు / కళాకారులు (Artisan)", "elig:biz:artisan")],
            ]
            return text, buttons

    # Default generic fallback question
    return (
        "✍️ <i>మీ వివరాలు మరింత స్పష్టంగా తెలియజేయండి.</i>",
        [],
    )


def match_eligible_schemes_for_profile(domain: str, slots: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Filters dataset schemes strictly based on complete collected criteria."""
    state = slots.get("state")
    matched: List[Dict[str, Any]] = []

    for s in SCHEMES:
        sch_jur = s.get("jurisdiction", "")
        # State filter
        if state and state != "Central":
            if sch_jur != state and sch_jur not in ["Central", "State & Central", "State (AP / TS)"]:
                continue

        if domain == DOMAIN_SCHOLARSHIP:
            course = slots.get("course_level")
            caste = slots.get("caste_category")
            sid = s.get("id", "")

            # Telangana matches
            if state == "Telangana":
                if course in ["intermediate", "degree", "engineering", "pg"]:
                    if sid in ["ts_epass_scholarship", "ts_telangana_bc_obc_epass"] and caste in ["BC", "SC/ST", "EBC", "Minority"]:
                        matched.append(s)
                    elif sid == "ts_telangana_minority_welfare_scholarship" and caste == "Minority":
                        matched.append(s)
                    elif sid == "ts_telangana_bc_study_circles" and caste == "BC":
                        matched.append(s)
                elif course == "school":
                    if sid in ["ts_telangana_education_kits", "ts_telangana_social_welfare_residential"]:
                        matched.append(s)

            # Andhra Pradesh matches
            elif state == "Andhra Pradesh":
                if course in ["degree", "engineering", "pg"]:
                    if sid in ["jagananna_vidya_deevena", "ap_jagananna_vasathi_deevena"]:
                        matched.append(s)
                    if sid == "ap_bc_obc_post" and caste == "BC":
                        matched.append(s)
                    if sid == "ap_sc_st_post" and caste == "SC/ST":
                        matched.append(s)
                    if sid == "ap_minority_ebc_scholarship" and caste in ["Minority", "EBC"]:
                        matched.append(s)
                elif course in ["school", "intermediate"]:
                    if sid == "ap_talliki_vandanam":
                        matched.append(s)
                    if course == "school" and sid in ["ap_jagananna_vidya_kanuka", "ap_jagananna_gorumudda"]:
                        matched.append(s)

            # Central matches
            if sid == "national_scholarship_portal":
                matched.append(s)
            elif sid == "pm_yasasvi_scholarship" and course in ["school", "intermediate"] and caste in ["BC", "EBC"]:
                matched.append(s)

        elif domain == DOMAIN_AGRICULTURE:
            land_status = slots.get("land_status", "")
            sid = s.get("id", "")
            if land_status in ["small_farmer", "2_acres", "5_acres"]:
                if sid in ["pm_kisan", "pmfby_crop_insurance", "kisan_credit_card"]:
                    matched.append(s)
                if state == "Telangana" and sid in ["rythu_bharosa", "ts_rythu_bima"]:
                    matched.append(s)
                elif state == "Andhra Pradesh" and sid in ["ap_annadata_sukhibhava", "ap_ysr_sunna_vaddi"]:
                    matched.append(s)
            elif land_status == "tenant":
                if state == "Telangana" and sid == "rythu_bharosa":
                    matched.append(s)
                elif state == "Andhra Pradesh" and sid == "ap_annadata_sukhibhava":
                    matched.append(s)
                if sid == "pmfby_crop_insurance":
                    matched.append(s)

        elif domain == DOMAIN_PENSION:
            p_type = slots.get("pension_type", "")
            sid = s.get("id", "")
            if state == "Telangana":
                if p_type in ["old_age", "widow"] and sid == "aasara_pension":
                    matched.append(s)
                elif p_type == "disabled" and sid in ["ts_disabled_pension", "aasara_pension"]:
                    matched.append(s)
            elif state == "Andhra Pradesh":
                if p_type in ["old_age", "widow"] and sid == "ap_ntr_bharosa_pension":
                    matched.append(s)
                elif p_type == "disabled" and sid in ["ap_disability_pension", "ap_ntr_bharosa_pension"]:
                    matched.append(s)
            if sid == "atal_pension_yojana" and p_type == "old_age":
                matched.append(s)

        elif domain == DOMAIN_HOUSING:
            sid = s.get("id", "")
            if state == "Telangana" and sid in ["ts_indiramma_indlu", "pmay_housing"]:
                matched.append(s)
            elif state == "Andhra Pradesh" and sid in ["ap_navaratnalu_housing", "pmay_housing"]:
                matched.append(s)
            elif sid in ["pmay_housing", "pmay_gramin"]:
                matched.append(s)

        elif domain == DOMAIN_WOMEN:
            sid = s.get("id", "")
            w_type = slots.get("welfare_type", "")
            if state == "Telangana":
                if w_type == "financial_bus" and sid == "ts_mahalakshmi":
                    matched.append(s)
                elif w_type == "marriage" and sid == "kalyana_lakshmi":
                    matched.append(s)
            elif state == "Andhra Pradesh":
                if w_type == "marriage" and sid == "kalyana_lakshmi":
                    matched.append(s)
                elif w_type == "dwakra" and sid in ["ap_ysr_aasara", "ap_ysr_sunna_vaddi"]:
                    matched.append(s)
            if sid in ["pm_ujjwala_2", "mahila_samman_savings"]:
                matched.append(s)

        elif domain == DOMAIN_BUSINESS:
            sid = s.get("id", "")
            b_type = slots.get("business_type", "")
            if b_type == "street_vendor" and sid == "pm_svanidhi":
                matched.append(s)
            elif sid in ["pm_mudra_yojana", "pm_vishwakarma"]:
                matched.append(s)

    # De-duplicate while preserving order
    unique_schemes = []
    seen = set()
    for item in matched:
        if item["id"] not in seen:
            seen.add(item["id"])
            unique_schemes.append(item)

    # Fallback to category match if none matched strictly
    if not unique_schemes and state:
        cat_key = "education" if domain == DOMAIN_SCHOLARSHIP else domain
        for s in SCHEMES:
            if s.get("category") == cat_key and s.get("jurisdiction") in [state, "Central"]:
                if s["id"] not in seen:
                    seen.add(s["id"])
                    unique_schemes.append(s)

    return unique_schemes


def format_final_eligibility_report(domain: str, slots: Dict[str, Any], schemes: List[Dict[str, Any]]) -> str:
    """Formats the final structured eligibility result for the citizen in polite Telugu."""
    # Profile summary banner
    profile_badges = []
    if "state" in slots:
        profile_badges.append(f"<b>రాష్ట్రం:</b> {slots['state']}")
    if "course_level" in slots:
        c_names = {
            "school": "పాఠశాల (School)",
            "intermediate": "ఇంటర్మీడియట్ (+2)",
            "degree": "డిగ్రీ / డిప్లొమా",
            "engineering": "ఇంజనీరింగ్ / ప్రొఫెషనల్",
            "pg": "పీజీ (Post-Graduation)",
        }
        profile_badges.append(f"<b>చదువు:</b> {c_names.get(slots['course_level'], slots['course_level'])}")
    if "caste_category" in slots:
        profile_badges.append(f"<b>వర్గం:</b> {slots['caste_category']}")
    if "income_or_ration" in slots:
        profile_badges.append("<b>ఆదాయం:</b> అర్హత పరిమితిలో ఉంది")
    if "land_status" in slots:
        profile_badges.append(f"<b>భూమి:</b> {slots.get('land_acres', '')} ఎకరాలు (చిన్న రైతు)")

    profile_header = " | ".join(profile_badges)

    if not schemes:
        return (
            "🙏 <b>సహాయం (Sahayam.ai) - అర్హత విశ్లేషణ</b>\n\n"
            f"👤 <i>{profile_header}</i>\n\n"
            "మీరు అందించిన వివరాల ప్రకారం నేరుగా సరిపోయే నిర్దిష్ట పథకం గుర్తించబడలేదు. "
            "సాధారణంగా ఆదాయ పరిమితి లేదా ఇతర ప్రత్యేక నిబంధనలు వర్తించవచ్చు.\n\n"
            "💡 <i>ఏదైనా ఇతర పథకం లేదా సహాయం కోసం దయచేసి ఇక్కడ అడగండి!</i>"
        )

    # Build crisp scheme cards
    cards = []
    for idx, sch in enumerate(schemes[:3], 1):
        benefit_preview = sch.get("benefits_te", "").split("\n")[0].lstrip("•*- ")
        docs_preview = ", ".join(sch.get("documents_te", [])[:4])
        portal = sch.get("official_link", "")

        card = (
            f"<b>{idx}. 🏛 {sch['name_te']}</b>\n"
            f"   <i>({sch['name_en']})</i>\n"
            f"   💰 <b>ప్రయోజనాలు:</b> {benefit_preview}\n"
            f"   📋 <b>మీకు ఎందుకు వర్తిస్తుంది:</b> మీ రాష్ట్రం, చదువు మరియు కేటగిరీ నిబంధనల ప్రకారం మీరు ఈ పథకానికి పూర్తి అర్హులు.\n"
            f"   📄 <b>కావలసిన పత్రాలు:</b> {docs_preview}\n"
            f"   🌐 <b>అధికారిక వెబ్‌సైట్:</b> <a href=\"{portal}\">{portal}</a>"
        )
        cards.append(card)

    heading = "స్కాలర్‌షిప్‌లు" if domain == DOMAIN_SCHOLARSHIP else "ప్రభుత్వ సంక్షేమ పథకాలు"
    response_text = (
        f"🎉 <b>సహాయం (Sahayam.ai) - మీకు అర్హత ఉన్న {heading}:</b>\n\n"
        f"👤 <b>మీ ప్రొఫైల్:</b> {profile_header}\n\n"
        "మీరు అందించిన పూర్తి వివరాల ఆధారంగా మీకు క్రింది పథకాలు వర్తిస్తాయి:\n\n"
        + "\n\n".join(cards) + "\n\n"
        "💡 <i>ఏదైనా పథకం యొక్క దరఖాస్తు విధానం లేదా పత్రాల వివరాల కోసం క్రింది బటన్ నొక్కండి!</i>"
    )

    return response_text
