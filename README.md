# 🏥 VentAssist — AI-Powered ICU Ventilation Decision Support

> Built for the Google Gemini Live Agent Challenge 2026

## What It Does
VentAssist is a real-time AI clinical decision support agent
for mechanical ventilation management in the ICU. Doctors can
speak or type clinical questions and receive instant,
evidence-based guidance.

## Three Clinical Modules
- **Hypoxemia Management** — Low SpO2 action plans using ARDSnet protocol
- **Pressure Alarm Troubleshooting** — Distinguishes airway vs lung problems
- **Weaning Readiness** — SAT/SBT checklist assessment

## Tech Stack
- **AI:** Gemini Live API (gemini-2.5-flash-native-audio-latest)
- **SDK:** Google GenAI SDK (v1alpha)
- **Backend:** Python + Flask
- **Frontend:** Vanilla HTML/CSS/JS (mobile-first)
- **Deployment:** Google Cloud Run

## Safety
All outputs are decision support only and include mandatory
disclaimers. Emergency detection triggers immediate escalation
messages. Clinical logic uses validated formulas (ARDSnet,
Berlin Definition, Devine formula).

## Setup Instructions

### Prerequisites
- Python 3.11+
- Google AI Studio API key

### Run Locally
```bash
git clone https://github.com/YOUR_USERNAME/ventassist-icu
cd ventassist-icu
pip install -r requirements.txt
export GOOGLE_API_KEY=your_key_here
python app.py
```

### Deploy to Google Cloud Run
```bash
gcloud run deploy ventassist \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_API_KEY=your_key_here
```

## Architecture
See ARCHITECTURE.jpg for system diagram.

## Disclaimer
This tool is for decision support only and does not replace
clinical judgment. Always verify recommendations with your
medical team.
