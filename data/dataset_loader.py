"""Loader and parser for the Government Welfare Schemes Dataset (govt_schemes_dataset.md).

Parses all 97 schemes across Central, Telangana, and Andhra Pradesh governments
into structured, typed Python dictionaries for fast local matching, categorization,
and grounding.
"""

import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("telegram_bot.dataset_loader")

# Path to the dataset markdown file
DATASET_PATH = Path(__file__).resolve().parent.parent / "govt_schemes_dataset.md"

SECTION_CATEGORY_MAP = {
    "1.1 Agriculture & Farmer Welfare": "agriculture",
    "1.2 Health & Medical Insurance": "health",
    "1.3 Housing": "housing",
    "1.4 Women & Child Development": "women",
    "1.5 Financial Inclusion, Insurance & Pension": "pension",
    "1.6 Employment, Skilling & MSME / Self-Employment": "business",
    "1.7 Education & Scholarships": "education",
    "1.8 Rural Development, Infrastructure & Other Welfare": "welfare",
    "2.1 Women Welfare": "women",
    "2.2 Agriculture & Allied": "agriculture",
    "2.3 Health": "health",
    "2.4 Education": "education",
    "2.5 Housing": "housing",
    "2.6 SC / ST / BC / Minority Welfare": "welfare",
    "2.7 Employment & Skill Development": "business",
    "2.8 Senior Citizens, Disability & Social Security": "pension",
    "3.1 Women Welfare": "women",
    "3.2 Agriculture & Allied": "agriculture",
    "3.3 Health": "health",
    "3.4 Education": "education",
    "3.5 Housing": "housing",
    "3.6 SC / ST / BC / Minority Welfare": "welfare",
    "3.7 Employment, Weavers, Artisans & Fishermen": "business",
    "3.8 Senior Citizens, Disability & Social Security": "pension",
}

CATEGORY_TE_MAP = {
    "agriculture": "🌾 వ్యవసాయం & రైతులు",
    "women": "👩 మహిళలు & డ్వాక్రా",
    "education": "🎓 విద్యార్థులు & చదువు",
    "health": "🏥 ఆరోగ్యం & చికిత్స",
    "pension": "👴 వృద్ధులు & పెన్షన్లు",
    "business": "💼 వ్యాపారం & రుణాలు / ఉపాధి",
    "housing": "🏠 గృహ నిర్మాణం & ఇండ్లు",
    "welfare": "🤝 సంక్షేమం & సామాజిక భద్రత",
}

# Explicit Canonical IDs for well-known schemes to ensure backwards compatibility with tests & handlers
CANONICAL_IDS = {
    ("Central", 1): "pm_kisan",
    ("Central", 2): "pmfby_crop_insurance",
    ("Central", 3): "kisan_credit_card",
    ("Central", 4): "pm_kisan_maandhan",
    ("Central", 5): "ayushman_bharat",
    ("Central", 7): "pmay_gramin",
    ("Central", 8): "pmay_housing",
    ("Central", 9): "pm_ujjwala_2",
    ("Central", 13): "pm_jan_dhan",
    ("Central", 14): "pm_suraksha_bima",
    ("Central", 15): "pm_jeevan_jyoti_bima",
    ("Central", 16): "atal_pension_yojana",
    ("Central", 20): "pm_vishwakarma",
    ("Central", 22): "pm_svanidhi",
    ("Central", 24): "mgnrega_central",
    ("Telangana", 1): "ts_mahalakshmi",
    ("Telangana", 2): "kalyana_lakshmi",
    ("Telangana", 3): "ts_kcr_kit",
    ("Telangana", 5): "rythu_bharosa",
    ("Telangana", 7): "ts_rythu_bima",
    ("Telangana", 11): "aarogyasri",
    ("Telangana", 13): "ts_epass_scholarship",
    ("Telangana", 19): "ts_indiramma_indlu",
    ("Telangana", 20): "ts_dalit_bandhu",
    ("Telangana", 26): "aasara_pension",
    ("Andhra Pradesh", 1): "ap_talliki_vandanam",
    ("Andhra Pradesh", 6): "ap_annadata_sukhibhava",
    ("Andhra Pradesh", 11): "ap_aarogyasri",
    ("Andhra Pradesh", 13): "jagananna_vidya_deevena",
    ("Andhra Pradesh", 14): "ap_jagananna_vasathi_deevena",
    ("Andhra Pradesh", 21): "ap_navaratnalu_housing",
    ("Andhra Pradesh", 29): "ap_deepam_2",
    ("Andhra Pradesh", 30): "ap_ntr_bharosa_pension",
}

# Common transliterations / Telugu titles for central & state schemes
SCHEME_NAME_TE_LOOKUP = {
    "pm_kisan": "పీఎం కిసాన్ సమ్మాన్ నిధి (PM-KISAN)",
    "pmfby_crop_insurance": "పీఎం ఫసల్ బీమా యోజన / ఉచిత పంటల బీమా (PMFBY)",
    "kisan_credit_card": "కిసాన్ క్రెడిట్ కార్డ్ (KCC)",
    "pm_kisan_maandhan": "పీఎం కిసాన్ మాన్‌ధన్ యోజన (రైతు పెన్షన్)",
    "ayushman_bharat": "ఆయుష్మాన్ భారత్ - పీఎం జేఏవై (AB PM-JAY)",
    "pmay_gramin": "పీఎం గ్రామీణ ఆవాస్ యోజన (PMAY-G)",
    "pmay_housing": "పీఎం పట్టణ ఆవాస్ యోజన 2.0 (PMAY-U 2.0)",
    "pm_ujjwala_2": "పీఎం ఉజ్జ్వల యోజన 2.0 (PMUY)",
    "pm_svanidhi": "పీఎం స్వనిధి (PM SVANidhi / వీధి వ్యాపారుల రుణం)",
    "pm_jan_dhan": "పీఎం జన్ ధన్ యోజన (PMJDY)",
    "pm_suraksha_bima": "పీఎం సురక్షా బీమా యోజన (PMSBY)",
    "pm_jeevan_jyoti_bima": "పీఎం జీవన్ జ్యోతి బీమా యోజన (PMJJBY)",
    "atal_pension_yojana": "అటల్ పెన్షన్ యోజన (APY)",
    "pm_vishwakarma": "పీఎం విశ్వకర్మ యోజన (చేతివృత్తుల సాయం)",
    "mgnrega_central": "మహాత్మా గాంధీ జాతీయ గ్రామీణ ఉపాధి హామీ పథకం (MGNREGA)",
}


def _clean_slug(raw_name: str, jurisdiction: str) -> str:
    """Generates a clean snake_case slug from scheme name."""
    clean = raw_name.lower()
    clean = re.sub(r"\(.*?\)", "", clean)
    clean = re.sub(r"—.*$", "", clean)
    clean = re.sub(r"[^\w\s]", " ", clean)
    words = [
        w
        for w in clean.split()
        if w
        not in [
            "scheme",
            "yojana",
            "pathakam",
            "and",
            "of",
            "the",
            "for",
            "pradhan",
            "mantri",
        ]
    ]
    slug = "_".join(words[:4])

    prefix = ""
    if jurisdiction == "Telangana":
        prefix = "ts_"
    elif jurisdiction == "Andhra Pradesh":
        prefix = "ap_"

    if prefix and not slug.startswith(prefix):
        slug = prefix + slug
    return slug


def _extract_field_val(lines: List[str], field_name: str) -> str:
    """Extracts field text following - **Field Name:** pattern."""
    block = "\n".join(lines)
    pat = rf"-\s+\*\*{re.escape(field_name)}[:\*]*\s*([^\n]+(?:\n(?!-\s+\*\*)[^\n]+)*)"
    m = re.search(pat, block, re.IGNORECASE)
    if m:
        val = " ".join(m.group(1).split())
        val = re.sub(r"^[\s:—–-]+", "", val).strip()
        return val
    return ""


def _parse_telugu_and_english_names(
    raw_name: str, also_known_as: str, scheme_id: str
) -> Tuple[str, str]:
    """Extracts or derives natural Telugu and English names for a scheme."""
    if scheme_id in SCHEME_NAME_TE_LOOKUP:
        return SCHEME_NAME_TE_LOOKUP[scheme_id], raw_name

    # Check if Telugu script exists inside parentheses or name
    telugu_matches = re.findall(r"[\u0C00-\u0C7F]+(?:\s+[\u0C00-\u0C7F]+)*", raw_name)
    if not telugu_matches and also_known_as:
        telugu_matches = re.findall(
            r"[\u0C00-\u0C7F]+(?:\s+[\u0C00-\u0C7F]+)*", also_known_as
        )

    clean_en = re.sub(r"\([^\)]*[\u0C00-\u0C7F]+[^\)]*\)", "", raw_name).strip()
    clean_en = re.sub(r"\s+", " ", clean_en)

    if telugu_matches:
        te_name = " ".join(telugu_matches)
        return f"{te_name} ({clean_en})", clean_en

    # If no Telugu script found, use English title with standard prefix
    return raw_name, raw_name


def _build_scheme_tags(
    scheme_id: str,
    name_te: str,
    name_en: str,
    also_known_as: str,
    category: str,
    jurisdiction: str,
    target_group: str,
) -> List[str]:
    """Generates comprehensive search tags in Telugu and English."""
    tags = set()

    # Category base tags
    cat_tags = {
        "agriculture": [
            "రైతు",
            "పొలం",
            "భూమి",
            "వ్యవసాయం",
            "చిన్న రైతు",
            "సన్నకారు రైతు",
            "ఎకరాలు",
            "farmer",
            "agriculture",
            "crop",
            "kisan",
            "రైతులు",
        ],
        "women": [
            "మహిళ",
            "స్త్రీ",
            "ఆడపడుచు",
            "డ్వాక్రా",
            "తల్లి",
            "వివాహం",
            "పెళ్లి",
            "women",
            "shg",
            "mother",
            "girl",
        ],
        "education": [
            "చదువు",
            "విద్యార్థి",
            "స్కూల్",
            "కాలేజీ",
            "ఫీజు",
            "స్కాలర్‌షిప్",
            "student",
            "school",
            "college",
            "scholarship",
            "education",
        ],
        "health": [
            "ఆరోగ్యం",
            "వైద్యం",
            "హాస్పిటల్",
            "ఆపరేషన్",
            "చికిత్స",
            "మందులు",
            "health",
            "hospital",
            "medical",
            "treatment",
        ],
        "pension": [
            "పెన్షన్",
            "పింఛను",
            "వృద్ధాప్య",
            "ముసలి",
            "వితంతువు",
            "వికలాంగులు",
            "దివ్యాంగులు",
            "pension",
            "senior",
            "old age",
            "disability",
        ],
        "business": [
            "వ్యాపారం",
            "స్వయం ఉపాధి",
            "రుణం",
            "లోన్",
            "చేతివృత్తులు",
            "తోపుడు బండి",
            "business",
            "loan",
            "vendor",
            "employment",
            "msme",
        ],
        "housing": [
            "ఇల్లు",
            "గృహం",
            "ఇంటి స్థలం",
            "ఆవాస్",
            "ఇందిరమ్మ ఇండ్లు",
            "house",
            "housing",
            "home",
            "shelter",
        ],
        "welfare": [
            "సంక్షేమం",
            "బీసీ",
            "ఎస్సీ",
            "ఎస్టీ",
            "మైనారిటీ",
            "కార్మికులు",
            "welfare",
            "sc",
            "st",
            "bc",
            "minority",
            "worker",
        ],
    }

    tags.update(cat_tags.get(category, []))

    # Add jurisdiction tags
    if jurisdiction == "Telangana":
        tags.update(["తెలంగాణ", "telangana", "ts"])
    elif jurisdiction == "Andhra Pradesh":
        tags.update(["ఆంధ్రప్రదేశ్", "ఆంధ్ర", "andhra", "ap"])
    elif jurisdiction == "Central":
        tags.update(["కేంద్ర", "భారత ప్రభుత్వం", "central", "india", "pm"])

    # Extract words from names
    for text in [name_te, name_en, also_known_as, target_group]:
        if not text:
            continue
        words = re.findall(r"[\w\u0C00-\u0C7F]+", text.lower())
        for w in words:
            if len(w) >= 3 and w not in [
                "and",
                "the",
                "for",
                "scheme",
                "yojana",
                "pathakam",
            ]:
                tags.add(w)

    return sorted(list(tags))


def _clean_documents(raw_docs: str) -> List[str]:
    """Splits comma/semicolon separated documents into a clean list."""
    if not raw_docs:
        return ["ఆధార్ కార్డు (Aadhaar Card)", "బ్యాంక్ పాస్ బుక్ (Bank Passbook)"]

    items = re.split(r"[,;•\n]+", raw_docs)
    docs = []
    for item in items:
        cleaned = item.strip().lstrip("•*- ")
        if cleaned and len(cleaned) > 2:
            docs.append(cleaned)
    return (
        docs
        if docs
        else ["ఆధార్ కార్డు (Aadhaar Card)", "బ్యాంక్ పాస్ బుక్ (Bank Passbook)"]
    )


def _format_official_link(portal_str: str) -> str:
    """Formats the portal string into a full HTTPS URL."""
    if not portal_str:
        return "https://www.india.gov.in"

    urls = re.findall(
        r"[a-zA-Z0-9.-]+\.(?:gov\.in|nic\.in|in|org|com)[^\s,;\)]*", portal_str
    )
    if urls:
        target = urls[0].strip()
        if not target.startswith("http"):
            return f"https://{target}"
        return target

    # Default fallback
    if "/" in portal_str:
        first_part = portal_str.split("/")[0].strip()
        if "." in first_part:
            return f"https://{first_part}"

    return "https://myscheme.gov.in"


def load_dataset_schemes() -> List[Dict[str, Any]]:
    """Reads govt_schemes_dataset.md and returns all 97 structured schemes."""
    if not DATASET_PATH.exists():
        logger.error(f"Dataset file not found at {DATASET_PATH}")
        return []

    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        text = f.read()

    lines = text.splitlines()

    current_part = ""
    current_jurisdiction = ""
    current_section = ""
    schemes_raw = []
    current_scheme = None

    for line in lines:
        if line.startswith("## Part 1"):
            current_part = "Central Government Schemes"
            current_jurisdiction = "Central"
        elif line.startswith("## Part 2"):
            current_part = "Telangana State Government Schemes"
            current_jurisdiction = "Telangana"
        elif line.startswith("## Part 3"):
            current_part = "Andhra Pradesh State Government Schemes"
            current_jurisdiction = "Andhra Pradesh"
        elif line.startswith("## Notes"):
            current_part = "Notes"
            current_jurisdiction = ""
        elif line.startswith("### ") and current_part != "Notes":
            current_section = line[4:].strip()
        elif line.startswith("#### ") and current_jurisdiction:
            if current_scheme:
                schemes_raw.append(current_scheme)
            m = re.match(r"^####\s+(\d+)\.\s+(.+)$", line)
            if m:
                num = int(m.group(1))
                raw_name = m.group(2).strip()
                current_scheme = {
                    "num": num,
                    "raw_name": raw_name,
                    "part": current_part,
                    "jurisdiction": current_jurisdiction,
                    "section": current_section,
                    "raw_lines": [],
                }
        elif current_scheme:
            current_scheme["raw_lines"].append(line)

    if current_scheme:
        schemes_raw.append(current_scheme)

    logger.info(f"Read {len(schemes_raw)} raw schemes from {DATASET_PATH.name}")

    parsed_schemes: List[Dict[str, Any]] = []
    used_ids = set()

    for item in schemes_raw:
        jur = item["jurisdiction"]
        num = item["num"]
        raw_name = item["raw_name"]
        raw_lines = item["raw_lines"]
        section = item["section"]

        # 1. Scheme ID
        scheme_id = CANONICAL_IDS.get((jur, num))
        if not scheme_id:
            scheme_id = _clean_slug(raw_name, jur)

        # Collision prevention
        orig_id = scheme_id
        counter = 2
        while scheme_id in used_ids:
            scheme_id = f"{orig_id}_{counter}"
            counter += 1
        used_ids.add(scheme_id)

        # 2. Category
        category = SECTION_CATEGORY_MAP.get(section, "welfare")
        category_te = CATEGORY_TE_MAP.get(
            category, "🤝 సంక్షేమం & సామాజిక భద్రత"
        )

        # 3. Extract text fields
        also_known_as = _extract_field_val(raw_lines, "Also known as")
        raw_category = _extract_field_val(raw_lines, "Category")
        launched_by = _extract_field_val(raw_lines, "Launched by / Year")
        if not launched_by:
            launched_by = _extract_field_val(raw_lines, "Launched by")
        benefit = _extract_field_val(raw_lines, "Benefit")
        eligibility = _extract_field_val(raw_lines, "Eligibility")
        documents_raw = _extract_field_val(raw_lines, "Documents required")
        portal_raw = _extract_field_val(raw_lines, "Official portal")

        # 4. Names in Telugu and English
        name_te, name_en = _parse_telugu_and_english_names(
            raw_name, also_known_as, scheme_id
        )

        # 5. Documents list
        documents_te = _clean_documents(documents_raw)

        # 6. Official link
        official_link = _format_official_link(portal_raw)

        # 7. Tags
        tags = _build_scheme_tags(
            scheme_id,
            name_te,
            name_en,
            also_known_as,
            category,
            jur,
            raw_category,
        )

        # 8. Land limit detection for small farmer schemes
        max_land_acres = None
        if "small" in raw_category.lower() or "marginal" in raw_category.lower():
            if category == "agriculture":
                max_land_acres = 5.0

        # Application steps
        application_steps = (
            f"1. అధికారిక వెబ్‌సైట్ {official_link} లో లేదా సమీప గ్రామ/వార్డు సచివాలయం, "
            f"MeeSeva లేదా రైతు సేవా కేంద్రం (RBK/CSC) లో దరఖాస్తు చేసుకోవచ్చు.\n"
            f"2. ఆధార్ మరియు సంబంధిత పత్రాలతో e-KYC పూర్తి చేయండి.\n"
            f"3. దరఖాస్తు స్థితిని పోర్టల్ ద్వారా ట్రాక్ చేయండి."
        )

        # Qualify reason
        qualify_reason = (
            f"మీరు ఈ వర్గానికి ({raw_category}) చెందిన పౌరులుగా ఉన్నందున, "
            f"ప్రభుత్వం అందించే ఈ సంక్షేమ పథకానికి అర్హత పొందే అవకాశం ఉంది."
        )

        scheme_dict = {
            "id": scheme_id,
            "name_te": name_te,
            "name_en": name_en,
            "category": category,
            "category_te": category_te,
            "target_group_te": raw_category,
            "jurisdiction": jur,
            "section": section,
            "launched_by": launched_by,
            "also_known_as": also_known_as,
            "max_land_acres": max_land_acres,
            "tags": tags,
            "benefits_te": benefit,
            "benefits_en": benefit,
            "eligibility_te": eligibility,
            "documents_te": documents_te,
            "application_steps_te": application_steps,
            "official_link": official_link,
            "qualify_reason_te": qualify_reason,
            "raw_dataset_entry": "\n".join(
                [f"#### {num}. {raw_name}"] + raw_lines
            ),
        }
        parsed_schemes.append(scheme_dict)

    return parsed_schemes
