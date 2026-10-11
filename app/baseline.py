"""Keyword classifier.

Two uses: it lets the app run with no AWS account (offline mode), and it is the
floor the model is measured against in eval/run_eval.py. It only knows English
keywords, so it is not what you demo.
"""
from __future__ import annotations

import re

from .models import ROUTINE, URGENT, Classification, Intent
from .rules import red_flags

_KEYWORDS = {
    "clinical": [
        "pain", "hurt", "hurts", "ache", "nausea", "nauseous", "sick", "medication", "medicine",
        "pills", "meds", "nurse", "doctor", "to the bathroom", "iv", "bandage", "wound", "incision",
        "stitches", "breath", "breathe", "fever", "swollen", "rash", "itchy", "procedure",
        "test results", "blood sugar", "ice pack", "turn over", "catheter", "oxygen", "shower",
        "sleep", "going home",
    ],
    "cleaning_environment": [
        "pillow", "blanket", "sheet", "sheets", "towel", "soap", "trash", "spill", "spilled", "clean",
        "cleaned", "floor", "smell", "smells", "laundry", "toilet paper",
    ],
    "facilities_equipment": [
        "toilet", "flush", "cold", "hot", "heat", "light", "blind", "leak", "leaking", "sink",
        "noise", "air conditioner", "door", "bed won't", "bed doesn't",
    ],
    "dietary": [
        "water", "juice", "coffee", "tea", "food", "hungry", "lunch", "dinner", "breakfast", "meal",
        "tray", "snack", "menu", "soup", "straw", "spoon", "eat", "drink", "jello", "crackers",
        "ginger ale",
    ],
    "tech_amenities": [
        "tv", "television", "remote", "wifi", "wi-fi", "internet", "phone", "charger", "channel",
        "tablet", "password", "video call", "visiting hours", "visit", "parking", "subtitles",
        "sound", "chaplain",
    ],
    "patient_relations": [
        "complaint", "complain", "interpreter", "translator", "my rights", "patient advocate",
        "speak to a manager", "talk to a manager", "rude", "grievance",
    ],
    "care_coordination": [
        "insurance", "coverage", "medicare", "medicaid", "social worker", "nursing home",
        "rehab facility", "skilled nursing", "home health", "walker", "wheelchair at home",
        "equipment at home", "hospital bed at home",
    ],
}

_PATTERNS = {
    category: re.compile(r"\b(" + "|".join(re.escape(w) for w in words) + r")\b", re.IGNORECASE)
    for category, words in _KEYWORDS.items()
}


class BaselineClassifier:
    source = "baseline"

    def classify(self, text: str) -> Classification:
        intents = []
        for category, pattern in _PATTERNS.items():
            if pattern.search(text):
                priority = URGENT if category == "clinical" and red_flags(text) else ROUTINE
                intents.append(Intent(category=category, priority=priority, summary=text.strip()[:120]))
        if not intents:
            intents = [Intent(category="unknown", summary=text.strip()[:120])]
        return Classification(intents=intents, confidence=1.0, source=self.source)
