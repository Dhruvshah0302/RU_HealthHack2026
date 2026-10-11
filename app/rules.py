"""Red-flag rules: the safety layer that runs before and independently of any model.

These rules can only escalate a request to the nurse. They never downgrade one.
They are deliberately blunt and explicit. The model is there to catch what plain
phrases miss; these are there so an obvious emergency never depends on the model.

A clinician should review this list before it is trusted.
"""
from __future__ import annotations

import re

_FLAGS: list[tuple[str, str]] = [
    ("chest pain", r"chest (pain|pressure|tight\w*|hurt\w*)|(pain|pressure|tight\w*) in (my|the|his|her) chest|my chest (hurts|is tight|feels tight)"),
    ("trouble breathing", r"(can'?t|cannot|can not|hard to|trouble|difficulty|struggling to) breath\w*|short(ness)? of breath"
                          r"|out of breath|gasping"),
    ("bleeding", r"\bbleed\w*|\bblood\b(?! (sugar|pressure|test|tests|work|draw|orange))"),
    # A person falling, not an object: "I fell", "my husband has fallen", "fell out of bed".
    # "My phone fell on the floor" must not page a nurse.
    ("fall", r"\b(i|he|she|we|they)(?:'ve|'s| have| has| just)* (fell|fallen)\b"
             r"|\b(husband|wife|mother|father|mom|dad|son|daughter|roommate|patient|someone|somebody)"
             r" (?:just |has |have )?(fell|fallen)\b"
             r"|\b(fell|fallen) (out of (the |my )?bed|in the (bathroom|shower)|and (hit|hurt|can'?t))"
             r"|\bslid (down )?to the floor\b"),
    ("fainting", r"\bfaint\w*|pass(ed|ing)? out|black(ed|ing)? out"),
    ("dizziness", r"\bdizz\w+|light-?headed"),
    ("severe pain", r"(severe|terrible|unbearable|worst|excruciating|really bad|awful) (pain|headache)|pain is (a |an )?(10|[7-9])\b|\bthrobbing\b"),
    ("stroke signs", r"\bslurr\w+|face (is |feels )?droop\w*|\bnumb(ness)?\b|can'?t (feel|move) my"),
    ("seizure", r"\bseizure|\bconvuls\w+"),
    ("choking", r"\bchok\w+"),
    ("allergic reaction", r"\ballergic|anaphyla\w+|(lips?|tongue|throat|face) (is |are )?swell\w+|swollen (lips?|tongue|throat)"),
    ("self-harm", r"kill myself|suicid\w+|end my life|hurt myself|want to die"),
    ("racing heart", r"heart (is )?(racing|pounding)|palpitation"),
    ("confusion", r"\bconfus(ed|ion)\b"),
    ("IV problem", r"\biv\b.*(hurt|burn|swol|swell|leak|pain|pulled|came out)"),
    ("vomiting", r"thr[oe]w(ing)? up|\bvomit\w*"),
    ("emergency", r"\bemergency\b(?! (exit|contact|light|lights|number))"),
    # Spanish
    ("dolor de pecho", r"dolor (en|de) (el |mi )?pecho"),
    ("no puede respirar", r"no puedo respirar"),
    ("sangrado", r"\bsangr\w+"),
    ("caída", r"me ca[ií]\b"),
    ("desmayo", r"\bdesmay\w+"),
    ("mareo", r"\bmaread\w+"),
]

_COMPILED = [(label, re.compile(pattern, re.IGNORECASE)) for label, pattern in _FLAGS]


def red_flags(text: str) -> list[str]:
    """Return the labels of every red-flag rule the text matches."""
    return [label for label, pattern in _COMPILED if pattern.search(text or "")]
