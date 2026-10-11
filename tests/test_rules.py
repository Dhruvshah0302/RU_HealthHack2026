"""Red-flag rules: they catch plain emergencies and stay quiet on everyday requests."""
import pytest

from app.rules import red_flags


@pytest.mark.parametrize("text", [
    "How do I call an outside number from this phone?",
    "What's my room number?",
    "My phone fell on the floor",
    "The remote fell behind the bed",
    "The trash can fell over",
    "The TV remote is confusing",
    "The emergency exit light is flickering",
    "Who is my emergency contact on file?",
    "Can I get a blood orange juice",
    "I'd kill for a coffee",
])
def test_everyday_requests_raise_no_flag(text):
    assert red_flags(text) == []


@pytest.mark.parametrize("text", [
    "I fell",
    "I just fell in the bathroom",
    "I've fallen and can't get up",
    "My husband fell out of bed",
    "My legs won't hold me up, I slid down to the floor",
    "I threw up twice",
    "it doesn't stop bleeding",
    "I can not breathe",
    "my arm is numb",
    "My mom is confused and doesn't know where she is",
    "This is an emergency",
    "no dejo de sangrar",
])
def test_plain_emergencies_raise_a_flag(text):
    assert red_flags(text) != []
