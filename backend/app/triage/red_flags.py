"""Deterministic clinical red-flag gate.

Runs BEFORE / ALONGSIDE the LLM, in milliseconds, with no network.
If this fires, the request is clinical, no matter what the LLM says.
Member C owns this list; extend it with the safety test set.
"""
import re
from dataclasses import dataclass

# Phrases that indicate a potentially urgent clinical issue (English + a few Spanish)
RED_FLAGS: dict[str, list[str]] = {
    "chest pain": [r"chest\b.{0,20}(pain|hurt|tight|pressure|heavy|squeez)", r"dolor (de|en el) pecho"],
    "breathing": [r"can'?t breathe", r"cannot breathe", r"short(ness)? of breath", r"hard to breathe",
                  r"trouble breathing", r"no puedo respirar"],
    "bleeding": [r"bleed(ing)?", r"blood", r"sangr(e|ando)"],
    "dizziness/fainting": [r"dizzy", r"dizziness", r"light-?headed", r"faint(ing|ed)?", r"pass(ed|ing)? out",
                           r"mareado|mareada"],
    "fall": [r"\bfell\b", r"\bfall(en)?\b", r"me ca[ií]"],
    "severe pain": [r"(severe|bad|terrible|unbearable|worst) pain", r"pain (is )?(really )?bad",
                    r"throbbing", r"\bhurts? (so|really) (bad|much)", r"dolor fuerte"],
    "surgical site": [r"incision", r"stitches", r"wound", r"surgical site", r"drain"],
    "neuro": [r"numb(ness)?", r"can'?t (move|feel) my", r"slurred", r"confus(ed|ion)", r"seizure"],
    "cardiac": [r"heart (is )?(racing|pounding)", r"palpitations?"],
    "allergic reaction": [r"swell(ing)?", r"hives", r"throat (is )?(closing|tight)", r"rash"],
    "vomiting": [r"vomit(ing)?", r"throw(ing)? up", r"nause(a|ous)"],
    "fever": [r"fever", r"chills", r"burning up"],
    "mental health": [r"hurt myself", r"kill myself", r"suicid", r"want to die"],
    "medication": [r"medication", r"\bmeds?\b", r"pain ?killer", r"\bIV\b", r"drip", r"pump (is )?beeping"],
    "help/emergency": [r"\bemergency\b", r"\bhelp me\b", r"\bnurse\b", r"\bdoctor\b", r"ayuda"],
}

NEGATIONS = r"\b(no|not|don'?t|doesn'?t|isn'?t|without|never|sin)\b"


@dataclass
class RedFlagResult:
    hit: bool
    reasons: list[str]


def _negated(text: str, start: int) -> bool:
    """Crude negation check: a negation word within ~3 words before the match.
    Deliberately conservative: only suppresses on clear 'no X' phrasing."""
    window = text[max(0, start - 25):start]
    return re.search(NEGATIONS + r"(\s+\w+){0,2}\s*$", window) is not None


def check(text: str) -> RedFlagResult:
    t = text.lower()
    reasons: list[str] = []
    for label, patterns in RED_FLAGS.items():
        for p in patterns:
            m = re.search(p, t, flags=re.IGNORECASE)
            if m and not _negated(t, m.start()):
                reasons.append(label)
                break
    return RedFlagResult(hit=bool(reasons), reasons=reasons)
