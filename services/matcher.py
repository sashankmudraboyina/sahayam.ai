"""Natural Language Entity Extraction and Scheme Matching Engine for Telugu and English."""

import re
from typing import Any, Dict, List, Optional, Tuple
from data.schemes import SCHEMES, get_scheme_by_id

TELUGU_NUMBERS = {
    "ఒక": 1.0,
    "రెండు": 2.0,
    "మూడు": 3.0,
    "నాలుగు": 4.0,
    "ఐదు": 5.0,
    "ఆరు": 6.0,
    "ఏడు": 7.0,
    "ఎనిమిది": 8.0,
    "తొమ్మిది": 9.0,
    "పది": 10.0,
}


def extract_entities(text: str) -> Dict[str, Any]:
    """Extracts citizen profile attributes from natural language Telugu/English text."""
    lower_text = text.lower()
    entities: Dict[str, Any] = {
        "land_acres": None,
        "is_small_farmer": False,
        "is_tenant_farmer": False,
        "categories": set(),
        "keywords_found": [],
    }

    # 1. Land size extraction (e.g., "రెండు ఎకరాలు", "2 ఎకరాల", "2.5 acres", "ఒక ఎకరం")
    # Telugu word numbers
    for word, num in TELUGU_NUMBERS.items():
        if re.search(rf"{word}\s*(?:ఎకరాల|ఎకరాలు|ఎకరం|acres?|acre)", lower_text):
            entities["land_acres"] = num
            break

    # Numeric digits (e.g. "2 ఎకరాల", "3.5 acres", "1.5 ఎకరం")
    if entities["land_acres"] is None:
        digit_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:ఎకరాల|ఎకరాలు|ఎకరం|acres?|acre)", lower_text)
        if digit_match:
            try:
                entities["land_acres"] = float(digit_match.group(1))
            except ValueError:
                pass

    # 2. Farmer classification
    if any(w in lower_text for w in ["చిన్న రైతు", "సన్నకారు రైతు", "small farmer", "marginal farmer"]):
        entities["is_small_farmer"] = True
    elif entities["land_acres"] is not None and entities["land_acres"] <= 5.0:
        entities["is_small_farmer"] = True

    if any(w in lower_text for w in ["కౌలు", "కౌలు రైతు", "tenant"]):
        entities["is_tenant_farmer"] = True

    # 3. Category tagging
    category_signatures = {
        "agriculture": ["రైతు", "పొలం", "భూమి", "వ్యవసాయం", "ఎకరాలు", "ఎకరం", "పంట", "సాగు", "బోరు", "కరెంట్", "farmer", "agriculture", "crop", "land"],
        "women": ["మహిళ", "ఆడ", "డ్వాక్రా", "తల్లి", "స్త్రీ", "వివాహం", "పెళ్లి", "కళ్యాణ", "women", "girl", "mother", "dwakra", "marriage"],
        "education": ["చదువు", "విద్యార్థి", "స్కూల్", "కాలేజీ", "ఫీజు", "హాస్టల్", "స్కాలర్‌షిప్", "అమ్మ ఒడి", "student", "school", "college", "fees", "scholarship"],
        "health": ["ఆరోగ్యం", "హాస్పిటల్", "ఆపరేషన్", "వైద్యం", "చికిత్స", "జబ్బు", "రోగం", "కార్డు", "health", "hospital", "doctor", "medical"],
        "pension": ["పెన్షన్", "పింఛను", "ముసలి", "వృద్ధ", "వితంతువు", "వికలాంగ", "దివ్యాంగ", "చేయూత", "ఆసరా", "pension", "old age", "widow", "disabled"],
        "business": ["వ్యాపారం", "షాపు", "తోపుడు బండి", "దుకాణం", "చిరు వ్యాపారి", "ముద్ర", "లోన్", "స్వయం ఉపాధి", "business", "shop", "vendor", "loan"],
        "housing": ["ఇల్లు", "గృహం", "ఇంటి స్థలం", "ఆవాస్", "ఇందిరమ్మ", "నిర్మాణం", "house", "housing", "home", "plot"],
    }

    for cat, words in category_signatures.items():
        for w in words:
            if w in lower_text:
                entities["categories"].add(cat)
                entities["keywords_found"].append(w)

    return entities


def match_schemes(user_query: str) -> List[Tuple[Dict[str, Any], float, str]]:
    """Matches user query against schemes database and returns ranked list with match confidence and explanation."""
    entities = extract_entities(user_query)
    lower_query = user_query.lower()
    scored_schemes: List[Tuple[Dict[str, Any], float, str]] = []

    for scheme in SCHEMES:
        score = 0.0
        reason_parts = []

        # 1. Category relevance
        if scheme["category"] in entities["categories"]:
            score += 4.0

        # 2. Tag matching
        matched_tags = 0
        for tag in scheme["tags"]:
            if tag.lower() in lower_query:
                matched_tags += 1
                score += 2.0

        # 3. Specific constraint analysis (Land, Farmer type, etc.)
        if scheme["category"] == "agriculture":
            if entities["land_acres"] is not None:
                max_allowed = scheme.get("max_land_acres")
                if max_allowed is not None:
                    if entities["land_acres"] <= max_allowed:
                        score += 3.5
                        reason_parts.append(
                            f"మీకు {entities['land_acres']} ఎకరాల సాగుభూమి ఉన్నందున (గరిష్ట పరిమితి {max_allowed} ఎకరాల లోపు), మీరు ఈ పథకానికి పూర్తి అర్హులు."
                        )
                    else:
                        score -= 2.0
                        reason_parts.append(
                            f"ఈ పథకం గరిష్టంగా {max_allowed} ఎకరాలు ఉన్న చిన్న రైతులకు మాత్రమే వర్తిస్తుంది. మీ వద్ద {entities['land_acres']} ఎకరాలు ఉన్నట్లు గుర్తించబడింది."
                        )
                else:
                    score += 2.0
                    reason_parts.append("సాగుభూమి ఉన్న రైతులందరికీ ఈ పథకం వర్తిస్తుంది.")

            if entities["is_small_farmer"]:
                score += 1.5
                if not reason_parts:
                    reason_parts.append("చిన్న మరియు సన్నకారు రైతు వర్గానికి ప్రభుత్వం అందించే ప్రత్యేక సంక్షేమ పథకం ఇది.")

            if entities["is_tenant_farmer"] and "కౌలు రైతు" in scheme.get("target_group_te", ""):
                score += 3.0
                reason_parts.append("గుర్తింపు పొందిన కౌలు రైతులకు కూడా ఈ పథకం ద్వారా లబ్ధి చేకూరుతుంది.")

        # If no custom reason was generated, use default
        qualification_note = " ".join(reason_parts) if reason_parts else scheme.get("qualify_reason_te", "మీ ప్రొఫైల్ ఆధారంగా ఈ పథకం మీకు వర్తించే అవకాశం ఉంది.")

        # Minimum threshold to be considered a match
        if score >= 2.0:
            scored_schemes.append((scheme, score, qualification_note))

    # Sort descending by score
    scored_schemes.sort(key=lambda x: x[1], reverse=True)
    return scored_schemes


def format_scheme_detailed_telugu(scheme: Dict[str, Any], qualification_note: str) -> str:
    """Formats a scheme into a structured, crystal-clear Telugu response complying with all requirements."""
    docs_formatted = "\n".join([f"  • {doc}" for doc in scheme["documents_te"]])

    return (
        f"🏛 <b>{scheme['name_te']}</b>\n"
        f"<i>({scheme['name_en']})</i>\n"
        f"🏷 <b>వర్గం:</b> {scheme['category_te']} | <b>పరిధి:</b> {scheme['jurisdiction']}\n\n"
        f"🎯 <b>మీకు ఎందుకు వర్తిస్తుంది? (అర్హత విశ్లేషణ):</b>\n"
        f"👉 <i>{qualification_note}</i>\n\n"
        f"💰 <b>ప్రయోజనాలు (Benefits):</b>\n"
        f"{scheme['benefits_te']}\n\n"
        f"📋 <b>అర్హతలు (Eligibility):</b>\n"
        f"{scheme['eligibility_te']}\n\n"
        f"📄 <b>కావలసిన పత్రాలు / డాక్యుమెంట్లు (Required Documents):</b>\n"
        f"{docs_formatted}\n\n"
        f"📝 <b>దరఖాస్తు విధానం (Application Procedure):</b>\n"
        f"{scheme['application_steps_te']}\n\n"
        f"🌐 <b>అధికారిక దరఖాస్తు వెబ్‌సైట్:</b>\n"
        f"🔗 <a href=\"{scheme['official_link']}\">{scheme['official_link']}</a>"
    )


def format_scheme_summary_telugu(scheme: Dict[str, Any], qualification_note: str, index: int = 1) -> str:
    """Formats a concise summary card for a scheme when multiple schemes are presented together."""
    # Keep qualification note to 1 clear sentence
    short_reason = qualification_note.split(".")[0].strip() + "." if "." in qualification_note else qualification_note.strip()
    # Extract concise first benefit line
    raw_benefit = scheme.get("benefits_te", "").strip()
    first_benefit = raw_benefit.split("\n")[0].lstrip("•*- ").strip()

    return (
        f"<b>{index}. 🏛 {scheme['name_te']}</b>\n"
        f"   <i>({scheme['name_en']})</i>\n"
        f"   💰 <b>ప్రయోజనం:</b> {first_benefit}\n"
        f"   🎯 <b>అర్హత:</b> {short_reason}\n"
    )


def format_multiple_schemes_summary(matched_schemes: List[tuple]) -> str:
    """Formats multiple matched schemes into a clean, concise digest."""
    cards = []
    for idx, (sch, score, reason) in enumerate(matched_schemes[:4], 1):
        cards.append(format_scheme_summary_telugu(sch, reason, index=idx))

    return (
        f"🌾 <b>సహాయం (Sahayam.ai) - మీకు అనువైన పథకాలు:</b>\n\n"
        f"మీ వివరాల ఆధారంగా <b>{len(matched_schemes)}</b> ప్రభుత్వ సంక్షేమ పథకాలు గుర్తించబడ్డాయి:\n\n"
        + "\n".join(cards) + "\n"
        "💡 <i>ఏదైనా పథకం యొక్క పూర్తి వివరాలు, కావలసిన పత్రాలు మరియు దరఖాస్తు విధానం తెలుసుకోవడానికి క్రింది బటన్లపై నొక్కండి.</i>"
    )
