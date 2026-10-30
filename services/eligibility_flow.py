"""Interactive Conversational Eligibility Discovery Engine for Sahayam.ai.

Enforces the step-by-step chat flow:
1. Analyzes user query in Telugu or English (via Text or Voice).
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
DOMAIN_HEALTH = "health"
DOMAIN_GENERAL = "general"

DOMAIN_KEYWORDS = {
    DOMAIN_SCHOLARSHIP: [
        "స్కాలర్‌షిప్", "స్కాలర్షిప్", "స్కాలర్‌షిప్‌లు", "స్కాలర్షిప్స్", "చదువు", "కాలేజీ", "ఫీజు",
        "రీయింబర్స్‌మెంట్", "విద్యా దీవెన", "వసతి దీవెన", "అమ్మ ఒడి", "తల్లికి వందనం", "ఈపాస్", "epass",
        "scholarship", "scholarships", "fee", "fees", "student", "college", "school", "btech", "degree",
        "డిగ్రీ", "ఇంజనీరింగ్", "ఇంటర్", "పాఠశాల", "విద్యార్థి", "విద్యార్థులు", "హాస్టల్"
    ],
    DOMAIN_AGRICULTURE: [
        "రైతు", "రైతులు", "రైతును", "పొలం", "భూమి", "సాగు", "వ్యవసాయం", "పంట",
        "రైతు భరోసా", "రైతు బంధు", "అన్నదాత సుఖీభవ", "పీఎం కిసాన్", "pm kisan",
        "farmer", "farmers", "agriculture", "crop", "land", "acres", "కౌలు", "ఎకరాల", "ఎకరం",
        "విత్తనాలు", "ఎరువులు", "బోరు", "ట్రాక్టర్"
    ],
    DOMAIN_PENSION: [
        "పెన్షన్", "పింఛను", "వృద్ధాప్య", "ముసలి", "వితంతువు", "దివ్యాంగ", "వికలాంగ",
        "ఆసరా", "ఎన్టీఆర్ భరోసా", "పెన్షన్ కానుక", "pension", "old age", "widow", "disability",
        "చేనేత పెన్షన్", "డయాలసిస్", "వృద్ధులు", "60 ఏళ్లు", "65 ఏళ్లు"
    ],
    DOMAIN_HOUSING: [
        "ఇల్లు", "ఇండ్లు", "గృహం", "ఇంటి స్థలం", "ఆవాస్", "ఇందిరమ్మ ఇండ్లు", "నవరత్నాలు ఇండ్లు",
        "house", "housing", "pmay", "home", "plot", "పేదల ఇళ్లు", "సొంత ఇల్లు", "పట్టా"
    ],
    DOMAIN_WOMEN: [
        "మహిళ", "మహిళలు", "స్త్రీ", "డ్వాక్రా", "ఆడపడుచు", "మహాలక్ష్మి", "కళ్యాణ లక్ష్మి",
        "షాదీ ముబారక్", "దీపం", "women", "girl", "mother", "dwakra", "shg", "marriage",
        "ఆడపిల్ల", "పెళ్లి సాయం", "ఉచిత బస్సు", "గ్యాస్ సిలిండర్",
        "పెళ్లి", "పెళ్లయింది", "పెళ్లైంది", "పెళ్లి అయింది", "పెళ్లి అయ్యింది", "వివాహం", "కళ్యాణం", "కళ్యాణమస్తు", "షాదీ", "wedding", "bride"
    ],
    DOMAIN_BUSINESS: [
        "వ్యాపారం", "షాపు", "తోపుడు బండి", "దుకాణం", "చిరు వ్యాపారి", "ముద్ర", "లోన్",
        "స్వయం ఉపాధి", "రుణం", "business", "shop", "vendor", "loan", "mudra", "svanidhi",
        "చేతివృత్తులు", "విశ్వకర్మ", "స్ట్రీట్ వెండర్"
    ],
    DOMAIN_HEALTH: [
        "ఆరోగ్యశ్రీ", "ఆయుష్మాన్", "వైద్యం", "ఆసుపత్రి", "హాస్పిటల్", "చికిత్స", "ఆపరేషన్",
        "మందులు", "జబ్బు", "క్యాన్సర్", "గుండె", "ఉచిత వైద్యం", "health", "hospital", "medical", "treatment", "aarogyasri", "ayushman"
    ],
    DOMAIN_GENERAL: [
        "పథకాలు వర్తిస్తాయి", "పథకాలు వస్తాయి", "ఏ పథకాలు", "పథకాలు కావాలి", "పథకాలు ఏమున్నాయి",
        "ప్రభుత్వ పథకాలు", "సంక్షేమ పథకాలు", "ప్రభుత్వ సాయం", "అర్హుడినా", "అర్హురాలినా",
        "నన్ను ప్రశ్నలు అడగండి", "నా అర్హత", "schemes apply", "eligible schemes", "which schemes",
        "schemes for me", "government schemes", "welfare schemes", "అర్హత చెకర్",
        "ఏమేం స్కీమ్స్", "ఏం స్కీమ్స్", "ఏ స్కీమ్స్", "స్కీమ్స్ వస్తాయి", "స్కీమ్స్ వర్తిస్తాయి", "గవర్నమెంట్ నుండి"
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
    DOMAIN_HEALTH: ["state", "income_or_ration"],
    DOMAIN_GENERAL: ["category"],
}


def detect_domain(text: str) -> Optional[str]:
    """Identifies the welfare domain of the citizen query."""
    lower_text = text.lower()
    # Check specific domains first
    for domain in [DOMAIN_SCHOLARSHIP, DOMAIN_AGRICULTURE, DOMAIN_PENSION, DOMAIN_HOUSING, DOMAIN_WOMEN, DOMAIN_BUSINESS, DOMAIN_HEALTH]:
        keywords = DOMAIN_KEYWORDS[domain]
        if any(w in lower_text for w in keywords):
            return domain
    # Check general domain
    if any(w in lower_text for w in DOMAIN_KEYWORDS[DOMAIN_GENERAL]):
        return DOMAIN_GENERAL
    return None


def extract_slots_from_text(
    text: str,
    current_slots: Optional[Dict[str, Any]] = None,
    expected_slot: Optional[str] = None,
) -> Dict[str, Any]:
    """Extracts known eligibility criteria slots from citizen natural language message."""
    slots = dict(current_slots or {})
    lower_text = text.lower()

    # 1. State extraction
    ap_cues = [
        "ఆంధ్రప్రదేశ్", "ఆంధ్ర", "ఆంధ్రా", "ఏపీ", "విజయవాడ", "విశాఖ", "విశాఖపట్నం",
        "వైజాగ్", "vizag", "గుంటూరు", "తిరుపతి", "కర్నూలు", "నెల్లూరు", "కడప",
        "అనంతపురం", "కాకినాడ", "రాజమండ్రి", "ఒంగోలు", "శ్రీకాకుళం", "విజయనగరం",
        "చిత్తూరు", "ఏలూరు", "నంద్యాల", "బాపట్ల"
    ]
    ts_cues = [
        "తెలంగాణ", "తెలంగాణా", "టీఎస్", "హైదరాబాద్", "వరంగల్", "కరీంనగర్", "ఖమ్మం",
        "నిజామాబాద్", "నల్గొండ", "మహబూబ్ నగర్", "రంగారెడ్డి", "మేడ్చల్", "సిద్దిపేట",
        "సూర్యాపేట", "ఆదిలాబాద్", "మంచిర్యాల", "జగిత్యాల", "కామారెడ్డి", "జనగాం", "హనుమకొండ"
    ]
    central_cues = ["కేంద్ర", "సెంట్రల్", "భారత", "ఇండియా", "దేశవ్యాప్తంగా"]

    if re.search(r"\b(telangana|ts)\b", lower_text) or any(w in lower_text for w in ts_cues):
        slots["state"] = "Telangana"
    elif re.search(r"\b(andhra|ap)\b", lower_text) or any(w in lower_text for w in ap_cues):
        slots["state"] = "Andhra Pradesh"
    elif re.search(r"\b(central|all india|india)\b", lower_text) or any(w in lower_text for w in central_cues):
        slots["state"] = "Central"
    elif expected_slot == "state":
        if "1" in lower_text or "తెలం" in lower_text:
            slots["state"] = "Telangana"
        elif "2" in lower_text or "ఆంధ్ర" in lower_text:
            slots["state"] = "Andhra Pradesh"
        elif "3" in lower_text or "కేంద్ర" in lower_text:
            slots["state"] = "Central"

    # 2. Course level (for education / scholarships)
    if re.search(r"\b(btech|b\.tech|engineering|mbbs|medicine|pharmacy|bpharm|law)\b", lower_text) or any(
        w in lower_text for w in ["బీటెక్", "బీ.టెక్", "ఇంజనీరింగ్", "ఇంజినీరింగ్", "మెడిసిన్", "ఫార్మసీ", "ప్రొఫెషనల్", "ఎంబీబీఎస్"]
    ):
        slots["course_level"] = "engineering"
    elif re.search(r"\b(degree|diploma|bsc|bcom|ba|bba|bca|polytechnic|iti)\b", lower_text) or any(
        w in lower_text for w in ["డిగ్రీ", "డిప్లొమా", "పాలిటెక్నిక్", "ఐటీఐ", "బీఎస్సీ", "బీకాం", "బీఏ", "బిఏ", "బీబీఏ", "బీసీఏ", "కాలేజీ"]
    ):
        slots["course_level"] = "degree"
    elif re.search(r"\b(inter|intermediate|10\+2|\+2|11th|12th)\b", lower_text) or any(
        w in lower_text for w in ["ఇంటర్", "ఇంటర్మీడియట్", "11వ", "12వ", "ప్లస్ 2"]
    ):
        slots["course_level"] = "intermediate"
    elif re.search(r"\b(school|10th|9th|8th|7th|6th|5th|4th|3rd|2nd|1st)\b", lower_text) or any(
        w in lower_text for w in ["స్కూల్", "పాఠశాల", "10వ", "టెన్త్", "1వ", "2వ", "3వ", "4వ", "5వ", "6వ", "7వ", "8వ", "9వ", "క్లాస్", "తరగతి"]
    ):
        slots["course_level"] = "school"
    elif re.search(r"\b(pg|mtech|mba|mca|msc|ma|masters)\b", lower_text) or any(
        w in lower_text for w in ["పీజీ", "మాస్టర్స్", "ఎంటెక్", "ఎంబీఏ", "ఎంసీఏ", "ఎమ్మెస్సీ", "ఎంఏ"]
    ):
        slots["course_level"] = "pg"

    # 3. Caste category
    if re.search(r"\b(sc|st|dalit|adivasi)\b", lower_text) or any(
        w in lower_text for w in ["ఎస్సీ", "ఎస్టీ", "దళిత", "గిరిజన", "మాల", "మాదిగ", "లంబాడా", "ఆదివాసి", "కోయ"]
    ):
        slots["caste_category"] = "SC/ST"
    elif re.search(r"\b(bc|obc|bc-a|bc-b|bc-c|bc-d|bc-e|bca|bcb|bcc|bcd|bce)\b", lower_text) or any(
        w in lower_text for w in ["బీసీ", "ఓబీసీ", "వెనుకబడిన", "యాదవ", "గొల్ల", "కురుమ", "ముదిరాజ్", "మున్నూరు కాపు", "గౌడ", "పద్మశాలి", "చేనేత", "విశ్వబ్రాహ్మణ", "కుమ్మరి", "రజక", "నాయీ బ్రాహ్మణ", "వడ్డెర"]
    ):
        slots["caste_category"] = "BC"
    elif re.search(r"\b(minority|muslim|christian|sikh)\b", lower_text) or any(
        w in lower_text for w in ["మైనారిటీ", "ముస్లిం", "క్రిస్టియన్", "సిక్కు", "జైన్"]
    ):
        slots["caste_category"] = "Minority"
    elif re.search(r"\b(oc|ebc|general|open)\b", lower_text) or any(
        w in lower_text for w in ["ఓసీ", "ఈబీసీ", "జనరల్", "ఓపెన్", "కాపు", "రెడ్డి", "చౌదరి", "కమ్మ", "బ్రాహ్మణ", "ఆర్య వైశ్య", "వైశ్య", "వెలమ", "క్షత్రియ"]
    ):
        slots["caste_category"] = "OC"

    # 4. Income or White Ration Card
    # Check negative cues FIRST to avoid false matches on "రేషన్ కార్డు లేదు"
    negative_income_cues = [
        "లేదు", "కాదు", "no", "లేవు", "కార్డు లేదు", "ఎక్కువ ఆదాయం",
        "ప్రభుత్వ ఉద్యోగం", "గవర్నమెంట్ జాబ్", "టాక్స్", "ఇన్‌కమ్ టాక్స్", "ధనిక", "rich"
    ]
    positive_income_cues = [
        "అవును", "ఉంది", "yes", "ఉన్నాయి", "తెల్ల కార్డు", "తెల్ల రేషన్ కార్డు",
        "రేషన్ కార్డు", "white card", "white ration", "పేద", "కూలీ", "కూలి పని",
        "తక్కువ ఆదాయం", "below", "పరిమితి లోపే", "బీపీఎల్", "bpl", "poor"
    ]

    num_lakh_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:లక్ష|లక్షలు|lakh|lakhs)", lower_text)
    if num_lakh_match:
        try:
            val = float(num_lakh_match.group(1))
            slots["income_or_ration"] = "eligible" if val <= 2.5 else "ineligible"
        except ValueError:
            pass
    elif any(w in lower_text for w in negative_income_cues):
        slots["income_or_ration"] = "ineligible"
    elif any(w in lower_text for w in positive_income_cues):
        slots["income_or_ration"] = "eligible"
    elif expected_slot == "income_or_ration":
        if any(w in lower_text for w in ["అవును", "ఉంది", "yes", "యా"]):
            slots["income_or_ration"] = "eligible"
        elif any(w in lower_text for w in ["లేదు", "కాదు", "no"]):
            slots["income_or_ration"] = "ineligible"

    # 5. Land status (for agriculture)
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
    elif any(w in lower_text for w in ["కౌలు", "కౌలు రైతు", "tenant", "సొంత భూమి లేదు"]):
        slots["land_status"] = "tenant"
    elif expected_slot == "land_status":
        if "కౌలు" in lower_text or "tenant" in lower_text:
            slots["land_status"] = "tenant"
        elif any(w in lower_text for w in ["చిన్న", "సన్నకారు", "2", "3", "5"]):
            slots["land_status"] = "small_farmer"

    # 6. Pension type
    if any(w in lower_text for w in ["వృద్ధాప్య", "ముసలి", "60", "62", "65", "70", "old age", "సీనియర్", "తాతయ్య", "బామ్మ", "అమ్మమ్మ"]):
        slots["pension_type"] = "old_age"
    elif any(w in lower_text for w in ["వితంతువు", "వితంతు", "భర్త లేని", "భర్త చనిపోయిన", "widow"]):
        slots["pension_type"] = "widow"
    elif any(w in lower_text for w in ["వికలాంగ", "దివ్యాంగ", "దివ్యాంగుల", "సదరం", "sadarem", "disabled", "హాండీక్యాప్"]):
        slots["pension_type"] = "disabled"
    elif any(w in lower_text for w in ["చేనేత"]):
        slots["pension_type"] = "weaver"
    elif any(w in lower_text for w in ["కల్లు గీత", "గీత కార్మికులు"]):
        slots["pension_type"] = "toddy_tapper"
    elif any(w in lower_text for w in ["డయాలసిస్", "కిడ్నీ"]):
        slots["pension_type"] = "dialysis"

    # 7. Housing site
    if any(w in lower_text for w in ["స్థలం లేదు", "నో ప్లాట్", "స్థలం కావాలి"]):
        slots["has_site"] = "no"
    elif any(w in lower_text for w in ["స్థలం ఉంది", "సొంత స్థలం", "పట్టా ఉంది", "plot", "site"]):
        slots["has_site"] = "yes"
    elif expected_slot == "has_site":
        if any(w in lower_text for w in ["ఉంది", "అవును", "yes"]):
            slots["has_site"] = "yes"
        elif any(w in lower_text for w in ["లేదు", "కాదు", "no"]):
            slots["has_site"] = "no"

    # 8. Business type
    if any(w in lower_text for w in ["తోపుడు బండి", "వీధి వ్యాపారి", "స్ట్రీట్ వెండర్", "ఫుట్‌పాత్", "పుట్ పాత్", "street vendor"]):
        slots["business_type"] = "street_vendor"
    elif any(w in lower_text for w in ["షాపు", "దుకాణం", "కిరాణా", "చిన్న వ్యాపారం", "స్టోర్"]):
        slots["business_type"] = "shop"
    elif any(w in lower_text for w in ["చేతివృత్తులు", "కుమ్మరి", "కమ్మరి", "వడ్రంగి", "శిల్పి", "టైలర్", "దర్జీ", "artisan"]):
        slots["business_type"] = "artisan"

    # 9. Women welfare type
    if any(w in lower_text for w in ["డ్వాక్రా", "dwakra", "shg", "మహిళా సంఘం", "సంఘం"]):
        slots["welfare_type"] = "dwakra"
    elif any(w in lower_text for w in ["పెళ్లి", "వివాహం", "కళ్యాణ లక్ష్మి", "షాదీ ముబారక్", "marriage"]):
        slots["welfare_type"] = "marriage"
    elif any(w in lower_text for w in ["మహాలక్ష్మి", "బస్సు", "సిలిండర్", "ఉచిత బస్సు", "గ్యాస్"]):
        slots["welfare_type"] = "financial_bus"

    # 10. General category selection
    if expected_slot == "category":
        for cat_key, cat_domain in [
            ("రైతు", DOMAIN_AGRICULTURE),
            ("వ్యవసాయ", DOMAIN_AGRICULTURE),
            ("చదువు", DOMAIN_SCHOLARSHIP),
            ("విద్యార్థి", DOMAIN_SCHOLARSHIP),
            ("స్కాలర్", DOMAIN_SCHOLARSHIP),
            ("పెన్షన్", DOMAIN_PENSION),
            ("మహిళ", DOMAIN_WOMEN),
            ("ఇల్లు", DOMAIN_HOUSING),
            ("వ్యాపార", DOMAIN_BUSINESS),
            ("వైద్య", DOMAIN_HEALTH),
            ("ఆరోగ్య", DOMAIN_HEALTH),
        ]:
            if cat_key in lower_text:
                slots["category"] = cat_domain
                break

    return slots


def get_missing_slots(domain: str, slots: Dict[str, Any]) -> List[str]:
    """Returns the list of missing required slots for the given domain."""
    required = REQUIRED_SLOTS.get(domain, [])
    return [slot for slot in required if slot not in slots or slots[slot] is None]


def format_collected_profile_badges(slots: Dict[str, Any], lang: str = "te") -> str:
    """Returns a short human-readable recap of details collected so far."""
    badges = []
    is_en = (lang == "en")

    if "state" in slots:
        badges.append(f"📍 {'State' if is_en else 'రాష్ట్రం'}: {slots['state']}")
    if "course_level" in slots:
        c_names_en = {
            "school": "School (Classes 1-10)",
            "intermediate": "Intermediate (11-12)",
            "degree": "Degree / Diploma / ITI",
            "engineering": "Engineering / Professional",
            "pg": "Post-Graduation (PG)",
        }
        c_names_te = {
            "school": "పాఠశాల (School)",
            "intermediate": "ఇంటర్మీడియట్ (+2)",
            "degree": "డిగ్రీ / డిప్లొమా (Degree)",
            "engineering": "ఇంజనీరింగ్ / ప్రొఫెషనల్",
            "pg": "పీజీ (Post-Graduation)",
        }
        c_name = c_names_en.get(slots['course_level'], slots['course_level']) if is_en else c_names_te.get(slots['course_level'], slots['course_level'])
        badges.append(f"🎓 {'Education' if is_en else 'చదువు'}: {c_name}")
    if "caste_category" in slots:
        badges.append(f"📋 {'Category' if is_en else 'వర్గం'}: {slots['caste_category']}")
    if "income_or_ration" in slots:
        inc_label = ("Income within limit / White Card" if is_en else "పరిమితి లోపే / తెల్ల కార్డు ఉంది") if slots["income_or_ration"] == "eligible" else ("Higher income" if is_en else "ఎక్కువ ఆదాయం")
        badges.append(f"💰 {'Income' if is_en else 'ఆదాయం'}: {inc_label}")
    if "land_status" in slots:
        land_label = ("Tenant Farmer" if is_en else "కౌలు రైతు") if slots["land_status"] == "tenant" else (f"{slots.get('land_acres', '')} Acres (Small Farmer)" if is_en else f"{slots.get('land_acres', '')} ఎకరాలు (చిన్న రైతు)")
        badges.append(f"🌾 {'Land' if is_en else 'భూమి'}: {land_label}")
    if "pension_type" in slots:
        p_names_en = {"old_age": "Old Age", "widow": "Widow", "disabled": "Disability"}
        p_names_te = {"old_age": "వృద్ధాప్య", "widow": "వితంతువు", "disabled": "దివ్యాంగులు"}
        p_name = p_names_en.get(slots['pension_type'], slots['pension_type']) if is_en else p_names_te.get(slots['pension_type'], slots['pension_type'])
        badges.append(f"👴 {'Pension' if is_en else 'పెన్షన్'}: {p_name}")
    if "has_site" in slots:
        s_label = ("Own plot available" if is_en else "సొంత స్థలం ఉంది") if slots["has_site"] == "yes" else ("No plot" if is_en else "స్థలం లేదు")
        badges.append(f"🏠 {'Site' if is_en else 'స్థలం'}: {s_label}")
    if "business_type" in slots:
        b_names_en = {"street_vendor": "Street Vendor", "shop": "Small Shop", "artisan": "Artisan / Crafts"}
        b_names_te = {"street_vendor": "తోపుడు బండి", "shop": "చిన్న షాపు", "artisan": "చేతివృత్తులు"}
        b_name = b_names_en.get(slots['business_type'], slots['business_type']) if is_en else b_names_te.get(slots['business_type'], slots['business_type'])
        badges.append(f"💼 {'Business' if is_en else 'వ్యాపారం'}: {b_name}")

    if not badges:
        return ""
    heading = "👤 <b>Details registered so far:</b>\n" if is_en else "👤 <b>ఇప్పటివరకు నమోదు చేసుకున్న వివరాలు:</b>\n"
    return heading + "\n".join(f"• {b}" for b in badges) + "\n\n"


def get_slot_question_and_buttons(
    domain: str,
    slot: str,
    current_slots: Optional[Dict[str, Any]] = None,
    lang: str = "te",
) -> Tuple[str, List[List[Tuple[str, str]]]]:
    """Generates a friendly bilingual (Telugu/English) question with quick-reply buttons and conversational context."""
    is_en = (lang == "en")
    recap = format_collected_profile_badges(current_slots or {}, lang=lang)

    if domain == DOMAIN_GENERAL and slot == "category":
        if is_en:
            text = (
                "🙏 <b>Welcome to Sahayam.ai!</b>\n\n"
                "To accurately discover government welfare schemes suitable for you, please choose your category:\n"
                "<i>(Select a button below or type your background)</i>"
            )
            buttons = [
                [("🌾 Farmers / Agriculture", "elig:cat:agriculture"), ("🎓 Students / Education", "elig:cat:scholarship")],
                [("👴 Pensions (Senior/Disabled)", "elig:cat:pension"), ("👩 Women Welfare", "elig:cat:women")],
                [("🏠 Housing / Plots", "elig:cat:housing"), ("💼 Business & Loans", "elig:cat:business")],
                [("🏥 Free Healthcare (Aarogyasri)", "elig:cat:health")],
            ]
        else:
            text = (
                "🙏 <b>నమస్కారం!</b>\n\n"
                "మీకు సరిగ్గా వర్తించే ప్రభుత్వ పథకాలను ఖచ్చితంగా గుర్తించడానికి, మీ నేపథ్యాన్ని ఎంచుకోండి:\n"
                "<i>(క్రింది బటన్లలో ఒకదాన్ని ఎంచుకోండి లేదా టైప్ చేయండి)</i>"
            )
            buttons = [
                [("🌾 రైతులు / వ్యవసాయం", "elig:cat:agriculture"), ("🎓 విద్యార్థులు / చదువు", "elig:cat:scholarship")],
                [("👴 పెన్షన్లు (వృద్ధాప్య/దివ్యాంగ)", "elig:cat:pension"), ("👩 మహిళా సంక్షేమం", "elig:cat:women")],
                [("🏠 ఇళ్ల నిర్మాణం / స్థలం", "elig:cat:housing"), ("💼 వ్యాపారం / స్వయం ఉపాధి", "elig:cat:business")],
                [("🏥 ఉచిత వైద్యం (ఆరోగ్యశ్రీ)", "elig:cat:health")],
            ]
        return text, buttons

    if slot == "state":
        if is_en:
            text = (
                recap
                + "📍 <b>State Details:</b>\n\n"
                "To accurately determine state-specific welfare schemes, which state do you belong to?\n"
                "<i>(Telangana or Andhra Pradesh?)</i>"
            )
            buttons = [
                [("🌾 Telangana", "elig:state:Telangana"), ("🏛 Andhra Pradesh", "elig:state:Andhra Pradesh")],
                [("🇮🇳 Central Government", "elig:state:Central")],
            ]
        else:
            text = (
                recap
                + "📍 <b>రాష్ట్ర వివరాలు:</b>\n\n"
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
            if is_en:
                text = (
                    recap
                    + "🎓 <b>Education Details:</b>\n\n"
                    "Which course or class are you currently studying?"
                )
                buttons = [
                    [("🏫 School (Classes 1-10)", "elig:course:school"), ("📚 Intermediate (11-12)", "elig:course:intermediate")],
                    [("🎓 Degree / Diploma / ITI", "elig:course:degree"), ("⚙️ Engineering / Professional", "elig:course:engineering")],
                    [("📖 Post-Graduation (PG)", "elig:course:pg")],
                ]
            else:
                text = (
                    recap
                    + "🎓 <b>చదువు వివరాలు:</b>\n\n"
                    "మీరు ప్రస్తుతం ఏ తరగతి లేదా కోర్సు చదువుతున్నారు?"
                )
                buttons = [
                    [("🏫 పాఠశాల (Classes 1-10)", "elig:course:school"), ("📚 ఇంటర్మీడియట్ (11-12)", "elig:course:intermediate")],
                    [("🎓 డిగ్రీ / డిప్లొమా / ఐటీఐ", "elig:course:degree"), ("⚙️ ఇంజనీరింగ్ / ప్రొఫెషనల్", "elig:course:engineering")],
                    [("📖 పీజీ (Post-Graduation)", "elig:course:pg")],
                ]
            return text, buttons

        if slot == "caste_category":
            if is_en:
                text = (
                    recap
                    + "📋 <b>Social / Caste Category:</b>\n\n"
                    "For scholarship reservation and criteria, what is your social category?"
                )
                buttons = [
                    [("SC / ST", "elig:caste:SC/ST"), ("BC / OBC", "elig:caste:BC")],
                    [("Minority", "elig:caste:Minority"), ("EBC / OC / General", "elig:caste:OC")],
                ]
            else:
                text = (
                    recap
                    + "📋 <b>సామాజిక వర్గం:</b>\n\n"
                    "స్కాలర్‌షిప్ నిబంధనల కొరకు మీ సామాజిక వర్గం (Caste Category) ఏమిటి?"
                )
                buttons = [
                    [("SC / ST", "elig:caste:SC/ST"), ("BC / OBC", "elig:caste:BC")],
                    [("మైనారిటీ (Minority)", "elig:caste:Minority"), ("EBC / OC / జనరల్", "elig:caste:OC")],
                ]
            return text, buttons

        if slot == "income_or_ration":
            if is_en:
                text = (
                    recap
                    + "💰 <b>Income Details:</b>\n\n"
                    "Is your family's annual income within the required limit (below ₹1.5 - ₹2.5 Lakhs), "
                    "or do you possess a White Ration Card?"
                )
                buttons = [
                    [("✅ Yes (Income within limit / Have White Card)", "elig:income:eligible")],
                    [("❌ No (Higher Income)", "elig:income:ineligible")],
                ]
            else:
                text = (
                    recap
                    + "💰 <b>ఆదాయ వివరాలు:</b>\n\n"
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
            if is_en:
                text = (
                    recap
                    + "🌾 <b>Agricultural Land Details:</b>\n\n"
                    "How much farmland do you own/cultivate, or are you a tenant farmer?"
                )
                buttons = [
                    [("🌱 Below 2 Acres (Marginal)", "elig:land:2"), ("🚜 2 to 5 Acres (Small Farmer)", "elig:land:5")],
                    [("🌾 Above 5 Acres", "elig:land:more"), ("🤝 Tenant Farmer (No own land)", "elig:land:tenant")],
                ]
            else:
                text = (
                    recap
                    + "🌾 <b>వ్యవసాయ భూమి వివరాలు:</b>\n\n"
                    "మీ వద్ద ఎంత సాగుభూమి ఉంది, లేదా మీరు కౌలు రైతునా?"
                )
                buttons = [
                    [("🌱 2 ఎకరాల లోపు (సన్నకారు రైతు)", "elig:land:2"), ("🚜 2 నుండి 5 ఎకరాలు (చిన్న రైతు)", "elig:land:5")],
                    [("🌾 5 ఎకరాల కంటే ఎక్కువ", "elig:land:more"), ("🤝 కౌలు రైతు (సొంత భూమి లేదు)", "elig:land:tenant")],
                ]
            return text, buttons

    elif domain == DOMAIN_PENSION:
        if slot == "pension_type":
            if is_en:
                text = (
                    recap
                    + "👴 <b>Pension Category:</b>\n\n"
                    "Which category of social security pension are you applying for?"
                )
                buttons = [
                    [("👴 Old Age Pension (60+ yrs)", "elig:pen:old_age"), ("👩 Widow Pension", "elig:pen:widow")],
                    [("♿ Disability Pension (SADAREM)", "elig:pen:disabled")],
                ]
            else:
                text = (
                    recap
                    + "👴 <b>పెన్షన్ విభాగం:</b>\n\n"
                    "మీరు ఏ రకమైన పెన్షన్ కొరకు దరఖాస్తు చేయాలనుకుంటున్నారు?"
                )
                buttons = [
                    [("👴 వృద్ధాప్య పెన్షన్ (60+ ఏళ్లు)", "elig:pen:old_age"), ("👩 వితంతు పెన్షన్", "elig:pen:widow")],
                    [("♿ దివ్యాంగుల పెన్షన్ (SADAREM)", "elig:pen:disabled")],
                ]
            return text, buttons

    elif domain == DOMAIN_HOUSING:
        if slot == "has_site":
            if is_en:
                text = (
                    recap
                    + "🏠 <b>House Site Details:</b>\n\n"
                    "Do you or your family members own a registered plot or patta to construct a house?"
                )
                buttons = [
                    [("✅ Own Plot / Patta Available", "elig:site:yes")],
                    [("❌ No Plot (Need house site as well)", "elig:site:no")],
                ]
            else:
                text = (
                    recap
                    + "🏠 <b>గృహ నిర్మాణ స్థలం వివరాలు:</b>\n\n"
                    "ఇల్లు నిర్మించుకోవడానికి మీ పేరు మీద లేదా కుటుంబ సభ్యుల పేరిట సొంత స్థలం/పట్టా ఉందా?"
                )
                buttons = [
                    [("✅ సొంత స్థలం / పట్టా ఉంది", "elig:site:yes")],
                    [("❌ సొంత స్థలం లేదు (ఇంటి స్థలం కూడా కావాలి)", "elig:site:no")],
                ]
            return text, buttons

    elif domain == DOMAIN_WOMEN:
        if slot == "welfare_type":
            if is_en:
                text = (
                    recap
                    + "👩 <b>Women Welfare Assistance:</b>\n\n"
                    "What type of government support are you looking for?"
                )
                buttons = [
                    [("🚌 Mahalakshmi / Free Bus & Gas Subsidy", "elig:wom:financial_bus")],
                    [("💍 Girl Child Marriage Assistance", "elig:wom:marriage")],
                    [("💼 DWACRA / SHG Bank Loan", "elig:wom:dwakra")],
                ]
            else:
                text = (
                    recap
                    + "👩 <b>మహిళా సంక్షేమ విభాగం:</b>\n\n"
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
            if is_en:
                text = (
                    recap
                    + "💼 <b>Business / Enterprise Details:</b>\n\n"
                    "What type of business or trade are you operating or planning?"
                )
                buttons = [
                    [("🛒 Street Vendor / Pushcart", "elig:biz:street_vendor")],
                    [("🏪 Small Grocery / Retail Shop", "elig:biz:shop")],
                    [("🛠 Artisan / Handicrafts", "elig:biz:artisan")],
                ]
            else:
                text = (
                    recap
                    + "💼 <b>వ్యాపార వివరాలు:</b>\n\n"
                    "మీరు ఏ రకమైన వ్యాపారం చేస్తున్నారు లేదా ప్రారంభించాలనుకుంటున్నారు?"
                )
                buttons = [
                    [("🛒 తోపుడు బండి / వీధి వ్యాపారం (Street Vendor)", "elig:biz:street_vendor")],
                    [("🏪 కిరాణా / చిన్న దుకాణం (Small Shop)", "elig:biz:shop")],
                    [("🛠 చేతివృత్తులు / కళాకారులు (Artisan)", "elig:biz:artisan")],
                ]
            return text, buttons

    elif domain == DOMAIN_HEALTH:
        if slot == "income_or_ration":
            if is_en:
                text = (
                    recap
                    + "🏥 <b>Healthcare & Ration Card:</b>\n\n"
                    "To avail free cashless medical treatments under Aarogyasri / Ayushman Bharat, do you have a White Ration Card?"
                )
                buttons = [
                    [("✅ Yes (Have White Ration Card)", "elig:income:eligible")],
                    [("❌ No (Do not have White Card)", "elig:income:ineligible")],
                ]
            else:
                text = (
                    recap
                    + "🏥 <b>వైద్య సాయం & రేషన్ కార్డు:</b>\n\n"
                    "ఆరోగ్యశ్రీ / ఆయుష్మాన్ భారత్ ద్వారా ఉచిత వైద్యం పొందడానికి మీ వద్ద తెల్ల రేషన్ కార్డు ఉందా?"
                )
                buttons = [
                    [("✅ అవును (తెల్ల రేషన్ కార్డు ఉంది)", "elig:income:eligible")],
                    [("❌ లేదు (రేషన్ కార్డు లేదు)", "elig:income:ineligible")],
                ]
            return text, buttons

    # Default generic fallback question
    fallback_text = (
        recap + "✍️ <i>Please provide your details with more clarity.</i>"
        if is_en
        else recap + "✍️ <i>మీ వివరాలు మరింత స్పష్టంగా తెలియజేయండి.</i>"
    )
    return fallback_text, []


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

        elif domain == DOMAIN_HEALTH:
            sid = s.get("id", "")
            if sid == "ayushman_bharat":
                matched.append(s)
            if state == "Andhra Pradesh" and sid in ["ap_aarogyasri", "aarogyasri"]:
                matched.append(s)
            elif state == "Telangana" and sid in ["aarogyasri", "ts_telangana_cm_relief_fund"]:
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


def format_final_eligibility_report(domain: str, slots: Dict[str, Any], schemes: List[Dict[str, Any]], lang: str = "te") -> str:
    """Formats the final structured eligibility result for the citizen in polite Telugu or English."""
    is_en = (lang == "en")
    profile_badges = []

    if "state" in slots:
        profile_badges.append(f"<b>{'State' if is_en else 'రాష్ట్రం'}:</b> {slots['state']}")
    if "course_level" in slots:
        c_names_en = {
            "school": "School (Classes 1-10)",
            "intermediate": "Intermediate (11-12)",
            "degree": "Degree / Diploma",
            "engineering": "Engineering / Professional",
            "pg": "Post-Graduation (PG)",
        }
        c_names_te = {
            "school": "పాఠశాల (School)",
            "intermediate": "ఇంటర్మీడియట్ (+2)",
            "degree": "డిగ్రీ / డిప్లొమా",
            "engineering": "ఇంజనీరింగ్ / ప్రొఫెషనల్",
            "pg": "పీజీ (Post-Graduation)",
        }
        c_name = c_names_en.get(slots['course_level'], slots['course_level']) if is_en else c_names_te.get(slots['course_level'], slots['course_level'])
        profile_badges.append(f"<b>{'Education' if is_en else 'చదువు'}:</b> {c_name}")
    if "caste_category" in slots:
        profile_badges.append(f"<b>{'Category' if is_en else 'వర్గం'}:</b> {slots['caste_category']}")
    if "income_or_ration" in slots:
        inc_label = "Within Limit / White Card" if is_en else "అర్హత పరిమితిలో ఉంది"
        profile_badges.append(f"<b>{'Income' if is_en else 'ఆదాయం'}:</b> {inc_label}")
    if "land_status" in slots:
        land_str = ("Tenant Farmer" if is_en else "కౌలు రైతు") if slots["land_status"] == "tenant" else (f"{slots.get('land_acres', '')} Acres (Small Farmer)" if is_en else f"{slots.get('land_acres', '')} ఎకరాలు (చిన్న రైతు)")
        profile_badges.append(f"<b>{'Land' if is_en else 'భూమి'}:</b> {land_str}")
    if "pension_type" in slots:
        p_names_en = {"old_age": "Old Age", "widow": "Widow", "disabled": "Disability"}
        p_names_te = {"old_age": "వృద్ధాప్య", "widow": "వితంతువు", "disabled": "దివ్యాంగులు"}
        p_name = p_names_en.get(slots['pension_type'], slots['pension_type']) if is_en else p_names_te.get(slots['pension_type'], slots['pension_type'])
        profile_badges.append(f"<b>{'Pension' if is_en else 'పెన్షన్'}:</b> {p_name}")
    if "business_type" in slots:
        b_names_en = {"street_vendor": "Street Vendor", "shop": "Small Shop", "artisan": "Artisan / Crafts"}
        b_names_te = {"street_vendor": "తోపుడు బండి", "shop": "చిన్న షాపు", "artisan": "చేతివృత్తులు"}
        b_name = b_names_en.get(slots['business_type'], slots['business_type']) if is_en else b_names_te.get(slots['business_type'], slots['business_type'])
        profile_badges.append(f"<b>{'Business' if is_en else 'వ్యాపారం'}:</b> {b_name}")

    profile_header = " | ".join(profile_badges)

    if not schemes:
        if is_en:
            return (
                "🙏 <b>Sahayam.ai - Eligibility Analysis</b>\n\n"
                f"👤 <i>{profile_header}</i>\n\n"
                "Based on the details provided, no directly matching specific scheme was identified in the database. "
                "Income limits or specific state guidelines may apply.\n\n"
                "💡 <i>Feel free to ask about any other welfare scheme or benefit!</i>"
            )
        else:
            return (
                "🙏 <b>సహాయం (Sahayam.ai) - అర్హత విశ్లేషణ</b>\n\n"
                f"👤 <i>{profile_header}</i>\n\n"
                "మీరు అందించిన వివరాల ప్రకారం నేరుగా సరిపోయే నిర్దిష్ట పథకం గుర్తించబడలేదు. "
                "సాధారణంగా ఆదాయ పరిమితి లేదా ఇతర ప్రత్యేక నిబంధనలు వర్తించవచ్చు.\n\n"
                "💡 <i>ఏదైనా ఇతర పథకం లేదా సహాయం కోసం దయచేసి ఇక్కడ అడగండి!</i>"
            )

    cards = []
    for idx, sch in enumerate(schemes[:3], 1):
        if is_en:
            benefit_preview = sch.get("benefits_en") or sch.get("benefits_te", "").split("\n")[0].lstrip("•*- ")
            docs_preview = ", ".join(sch.get("documents_te", [])[:4])
            portal = sch.get("official_link", "")

            card = (
                f"<b>{idx}. 🏛 {sch.get('name_en', sch['name_te'])}</b>\n"
                f"   <i>({sch['name_te']})</i>\n"
                f"   💰 <b>Benefits:</b> {benefit_preview}\n"
                f"   🎯 <b>Why you qualify:</b> Based on your state ({slots.get('state', '')}) and eligibility criteria, you qualify for this scheme.\n"
                f"   📄 <b>Key Documents:</b> {docs_preview}\n"
                f"   🌐 <b>Official Website:</b> <a href=\"{portal}\">{portal}</a>"
            )
        else:
            benefit_preview = sch.get("benefits_te", "").split("\n")[0].lstrip("•*- ")
            docs_preview = ", ".join(sch.get("documents_te", [])[:4])
            portal = sch.get("official_link", "")

            card = (
                f"<b>{idx}. 🏛 {sch['name_te']}</b>\n"
                f"   <i>({sch['name_en']})</i>\n"
                f"   💰 <b>ప్రయోజనాలు:</b> {benefit_preview}\n"
                f"   🎯 <b>మీకు ఎందుకు వర్తిస్తుంది:</b> మీ రాష్ట్రం ({slots.get('state', '')}), మరియు అర్హత ప్రమాణాల ప్రకారం మీరు ఈ పథకానికి పూర్తి అర్హులు.\n"
                f"   📄 <b>కావలసిన పత్రాలు:</b> {docs_preview}\n"
                f"   🌐 <b>అధికారిక వెబ్‌సైట్:</b> <a href=\"{portal}\">{portal}</a>"
            )
        cards.append(card)

    if is_en:
        heading = "Scholarships" if domain == DOMAIN_SCHOLARSHIP else "Government Welfare Schemes"
        response_text = (
            f"🎉 <b>Sahayam.ai - Eligible {heading} for You:</b>\n\n"
            f"👤 <b>Your Profile:</b> {profile_header}\n\n"
            "Based on your complete verified details, the following schemes apply to you:\n\n"
            + "\n\n".join(cards) + "\n\n"
            "💡 <i>Tap any button below for application steps, required documents, or to listen in audio!</i>"
        )
    else:
        heading = "స్కాలర్‌షిప్‌లు" if domain == DOMAIN_SCHOLARSHIP else "ప్రభుత్వ సంక్షేమ పథకాలు"
        response_text = (
            f"🎉 <b>సహాయం (Sahayam.ai) - మీకు అర్హత ఉన్న {heading}:</b>\n\n"
            f"👤 <b>మీ ప్రొఫైల్:</b> {profile_header}\n\n"
            "మీరు అందించిన పూర్తి వివరాల ఆధారంగా మీకు క్రింది పథకాలు వర్తిస్తాయి:\n\n"
            + "\n\n".join(cards) + "\n\n"
            "💡 <i>ఏదైనా పథకం యొక్క దరఖాస్తు విధానం లేదా పత్రాల వివరాల కోసం క్రింది బటన్ నొక్కండి!</i>"
        )

    return response_text
