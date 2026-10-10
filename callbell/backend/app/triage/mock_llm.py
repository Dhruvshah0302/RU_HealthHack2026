"""Offline keyword classifier for development when Bedrock isn't set up (LLM_PROVIDER=mock).
Not for judging accuracy, and never present it as the AI in the demo."""
import re

from ..schemas import Category, LLMClassification, Priority

RULES = [
    (Category.clinical, r"pain|hurt|nurse|doctor|bathroom|toilet|medic|iv\b|breath|dizzy|unwell|sick|bleed"),
    (Category.dietary, r"water|juice|ice|food|snack|meal|drink|coffee|tea|hungry|thirsty|agua"),
    (Category.comfort_linens, r"pillow|blanket|sheet|towel|gown|almohada|manta"),
    (Category.cleaning, r"clean|dirty|spill|sticky|trash|mess"),
    (Category.room_environment, r"cold|hot|temperature|light|blind|noise|broken|thermostat"),
    (Category.tech_amenities, r"tv|television|remote|wifi|wi-fi|phone|charger|tablet|channel"),
]


def classify(text: str) -> LLMClassification:
    t = text.lower()
    for cat, pat in RULES:
        if re.search(pat, t):
            clinical = cat == Category.clinical
            return LLMClassification(
                category=cat, is_clinical=clinical,
                priority=Priority.soon if clinical else Priority.routine,
                summary=text.strip()[:60], items=[], confidence=0.9,
                reason="mock keyword classifier")
    return LLMClassification(category=Category.other, is_clinical=False, priority=Priority.soon,
                             summary=text.strip()[:60], confidence=0.3, reason="mock: no match")
