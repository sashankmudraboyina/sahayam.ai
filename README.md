# 🌾 సహాయం (Sahayam.ai) - Telugu AI Government Welfare Scheme Discovery Platform

**Sahayam.ai (సహాయం)** is an AI-powered conversational government welfare scheme discovery platform built for Telugu-speaking citizens. Many citizens find it difficult to navigate complex government websites and bureaucratic jargon. With Sahayam.ai, citizens can simply describe their situation in natural, everyday Telugu (or English), and the system instantly identifies relevant schemes, explains benefits, eligibility criteria, required documents, step-by-step application procedures, and why they qualify.

---

## 🤖 Live Telegram Bot

* **Bot Name:** `sahayam.ai`
* **Bot Username:** [@sahayamusernameledu_bot](https://t.me/sahayamusernameledu_bot)
* **Access Link:** [https://t.me/sahayamusernameledu_bot](https://t.me/sahayamusernameledu_bot)

---

## 🌟 Key Features

1. **Natural Telugu Processing & Entity Extraction**:
   - Understands colloquial Telugu (e.g., `"నాకు రెండు ఎకరాల పొలం ఉంది. నేను చిన్న రైతును. నాకు ఏ ప్రభుత్వ పథకాలు వర్తిస్తాయి?"`).
   - Automatically extracts citizen parameters: land size (e.g. `రెండు ఎకరాలు` -> `2.0 acres`), farmer classification (చిన్న రైతు / సన్నకారు రైతు), occupation, age, and requirements.

2. **Comprehensive Scheme Evaluation (All 7 Key Dimensions)**:
   For every query, the bot delivers:
   - 🏛 **సంబంధిత పథకాలు (Relevant Schemes)**: Matched against Central & State (AP/Telangana) databases.
   - 🎯 **మీకు ఎందుకు వర్తిస్తుంది? (Why you qualify / conditions)**: Tailored rationale explaining how the citizen meets scheme parameters.
   - 💰 **ప్రయోజనాలు (Benefits)**: Financial amounts, subsidies, insurance coverage details.
   - 📋 **అర్హతలు (Eligibility)**: Landholding limits, income thresholds, family criteria, age.
   - 📄 **కావలసిన పత్రాలు / డాక్యుమెంట్లు (Required Documents)**: Aadhaar, Pattadar passbook, Ration card, 1-B, etc.
   - 📝 **దరఖాస్తు విధానం (Application Procedure)**: Step-by-step guide (Grama/Ward Sachivalayam, MeeSeva, RBK, or online).
   - 🌐 **అధికారిక వెబ్‌సైట్ లింక్ (Official Application Link)**: Direct clickable government portal URLs.

3. **Dual-Engine Architecture (Hybrid AI + Deterministic Matcher)**:
   - **Gemini AI Engine**: If `GEMINI_API_KEY` is provided, leverages Google Gemini 2.5 Flash grounded on the scheme knowledge base for natural conversational Telugu synthesis.
   - **Smart Telugu Semantic Rule Engine**: Works 100% out of the box without any external API keys or cloud dependencies.

4. **Interactive Eligibility Wizard & Category Browser**:
   - 🎯 **అర్హత చెకర్ (Wizard)**: Guided tap-to-answer questionnaire for farmers, women, students, seniors, vendors, etc.
   - 📂 **విభాగాలు (Categories)**: Browse Agriculture, Women/SHG, Education, Healthcare (Aarogyasri), Pensions, Loans, and Housing.

---

## 📁 Project Structure

```text
├── config.py                 # Configuration loader, token validation & logging
├── main.py                   # Telegram Bot entry point, polling, command handlers
├── data/
│   ├── __init__.py
│   └── schemes.py            # Central & State welfare schemes knowledge base
├── services/
│   ├── __init__.py
│   ├── matcher.py            # Natural Telugu entity extraction & constraint reasoning
│   └── ai_engine.py          # Gemini AI bridge with deterministic fallback
├── handlers/
│   ├── __init__.py
│   ├── start.py              # /start, /help and main welcome in Telugu
│   ├── schemes_handler.py    # Natural language query processing & inline action buttons
│   ├── wizard.py             # Interactive step-by-step eligibility checker
│   └── menu.py               # Callback router and sample questions
├── tests/
│   ├── test_schemes.py       # Unit tests verifying NLP extraction & scheme accuracy
│   └── test_bot.py           # Core bot sanity tests
├── requirements.txt          # Python dependencies
├── .env.example              # Environment template
└── README.md
```

---

## 🚀 Quick Start Guide

### 1. Configure Environment
Your `.env` file should contain:
```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
GEMINI_API_KEY=optional_gemini_api_key
LOG_LEVEL=INFO
```

### 2. Run the Bot
```bash
source .venv/bin/activate
python main.py
```

### 3. Run Automated Tests
```bash
.venv/bin/python -m unittest discover tests/
```

---

## 💡 Example Queries to Try in Telegram

* **రైతులు (Farmers):**
  > *"నాకు రెండు ఎకరాల పొలం ఉంది. నేను చిన్న రైతును. నాకు ఏ ప్రభుత్వ పథకాలు వర్తిస్తాయి?"*
* **ఆరోగ్యం (Health):**
  > *"ఆరోగ్యశ్రీ పథకం ద్వారా ఉచిత వైద్యం మరియు ఆపరేషన్లకు ఏయే పత్రాలు కావాలి?"*
* **విద్యార్థులు (Students):**
  > *"మా అబ్బాయి ఇంజనీరింగ్ చదువుతున్నాడు. ఫీజు రీయింబర్స్‌మెంట్ ఎలా వస్తుంది?"*
* **వ్యాపారం (Small Business):**
  > *"తోపుడు బండిపై పండ్ల వ్యాపారం చేస్తున్నాను, పీఎం స్వనిధి లోన్ ఎలా పొందాలి?"*
* **పెన్షన్లు (Pensions):**
  > *"మా ఇంట్లో పెద్దవారికి 65 ఏళ్లు. వృద్ధాప్య పింఛను ఎలా దరఖాస్తు చేసుకోవాలి?"*
