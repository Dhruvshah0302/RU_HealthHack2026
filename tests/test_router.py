"""The routing policy's safety properties. No network, no AWS."""
import pytest

from app.baseline import BaselineClassifier
from app.llm import BedrockClassifier, parse_tool_input
from app.models import FOOD, HOUSEKEEPING, NURSE, ROUTINE, URGENT, Classification, Intent
from app.router import route


class Fixed:
    """A classifier that returns whatever the test gives it."""
    source = "test"

    def __init__(self, intents=None, confidence=1.0, error=None):
        self.intents, self.confidence, self.error = intents or [], confidence, error

    def classify(self, text):
        if self.error:
            raise self.error
        return Classification(intents=self.intents, confidence=self.confidence)


def pairs(decision):
    return [(t.department, t.priority) for t in decision.tickets]


def test_non_clinical_request_never_reaches_the_nurse():
    decision = route("Can I get an extra pillow?", Fixed([Intent("cleaning_environment")]))
    assert pairs(decision) == [(HOUSEKEEPING, ROUTINE)]


def test_red_flag_escalates_even_when_the_classifier_says_routine():
    decision = route("Can I have water? I'm having chest pain.", Fixed([Intent("dietary")]))
    assert (NURSE, URGENT) in pairs(decision)
    assert (FOOD, ROUTINE) in pairs(decision)       # the water still gets delivered
    assert decision.rule_flags == ["chest pain"]


def test_red_flag_upgrades_a_routine_nurse_ticket():
    decision = route("I fell", Fixed([Intent("clinical", ROUTINE)]))
    assert pairs(decision) == [(NURSE, URGENT)]


@pytest.mark.parametrize("error", [TimeoutError("slow"), ValueError("bad json"), KeyError("output")])
def test_classifier_failure_sends_the_request_to_the_nurse(error):
    decision = route("something unusual", Fixed(error=error))
    assert pairs(decision) == [(NURSE, ROUTINE)]
    assert decision.fail_safe.startswith("classifier failed")


def test_classifier_failure_plus_red_flag_is_urgent_and_keeps_the_patients_words():
    decision = route("I can't breathe", Fixed(error=TimeoutError()))
    assert pairs(decision) == [(NURSE, URGENT)]
    assert decision.tickets[0].summary == "I can't breathe"


def test_low_confidence_never_lowers_an_urgent_answer():
    # The model was unsure what the patient needs, but it did call it urgent. Keep that.
    decision = route("I need help right now, something is wrong",
                     Fixed([Intent("clinical", priority=URGENT)], confidence=0.6))
    assert [(t.department, t.priority) for t in decision.tickets] == [(NURSE, URGENT)]
    assert "low confidence" in decision.fail_safe


def test_low_confidence_goes_to_the_nurse_instead_of_guessing():
    decision = route("that thing again", Fixed([Intent("dietary")], confidence=0.4))
    assert pairs(decision) == [(NURSE, ROUTINE)]
    assert "low confidence" in decision.fail_safe


def test_empty_classifier_answer_goes_to_the_nurse():
    assert pairs(route("hello", Fixed([]))) == [(NURSE, ROUTINE)]


def test_several_needs_become_several_tickets_with_the_nurse_first():
    intents = [Intent("dietary"), Intent("clinical", URGENT), Intent("cleaning_environment")]
    decision = route("juice, a blanket, and my wound is open", Fixed(intents))
    assert pairs(decision)[0] == (NURSE, URGENT)
    assert {d for d, _ in pairs(decision)} == {NURSE, FOOD, HOUSEKEEPING}


def test_two_needs_for_one_department_share_a_ticket():
    intents = [Intent("cleaning_environment", summary="blanket"), Intent("cleaning_environment", summary="spill")]
    decision = route("blanket and a spill", Fixed(intents))
    assert pairs(decision) == [(HOUSEKEEPING, ROUTINE)]
    assert decision.tickets[0].summary == "blanket; spill"


def test_nurse_button_skips_classification():
    decision = route("", Fixed(error=AssertionError("must not be called")), direct_nurse=True)
    assert pairs(decision) == [(NURSE, URGENT)]


def test_baseline_sends_what_it_does_not_understand_to_the_nurse():
    assert pairs(route("¿Me pueden traer otra almohada?", BaselineClassifier())) == [(NURSE, ROUTINE)]


# --- the model's structured answer ---

def test_model_answer_is_parsed():
    result = parse_tool_input({"language": "es", "confidence": 0.93, "intents": [
        {"category": "clinical", "priority": "urgent", "summary_en": "Chest pain"},
        {"category": "dietary", "priority": "routine", "summary_en": "Wants water"}]})
    assert [(i.department, i.priority) for i in result.intents] == [(NURSE, URGENT), (FOOD, ROUTINE)]
    assert result.language == "es"


def test_model_cannot_mark_a_non_clinical_request_urgent():
    result = parse_tool_input({"language": "en", "confidence": 0.9, "intents": [
        {"category": "dietary", "priority": "urgent", "summary_en": "Coffee now"}]})
    assert result.intents[0].priority == ROUTINE


@pytest.mark.parametrize("bad", [
    {"language": "en", "confidence": 0.9, "intents": []},
    {"language": "en", "confidence": 0.9, "intents": [{"category": "pharmacy", "priority": "routine", "summary_en": "x"}]},
    {"language": "en", "confidence": 0.9, "intents": [{"category": "clinical", "priority": "asap", "summary_en": "x"}]},
    {"language": "en", "confidence": 7, "intents": [{"category": "clinical", "priority": "urgent", "summary_en": "x"}]},
])
def test_unexpected_model_answers_are_rejected(bad):
    with pytest.raises(ValueError):
        parse_tool_input(bad)


class FakeBedrock:
    """Stands in for the Bedrock client so the request and response shapes are exercised."""
    def __init__(self, content):
        self.content, self.calls = content, []

    def converse(self, **kwargs):
        self.calls.append(kwargs)
        return {"output": {"message": {"content": self.content}}}


def test_bedrock_classifier_reads_the_tool_call_and_forces_the_tool():
    client = FakeBedrock([{"toolUse": {"name": "route_request", "input": {
        "language": "en", "confidence": 0.9,
        "intents": [{"category": "tech_amenities", "priority": "routine", "summary_en": "TV remote broken"}]}}}])
    result = BedrockClassifier(model_id="test-model", client=client).classify("remote is broken")
    assert result.intents[0].category == "tech_amenities"
    call = client.calls[0]
    assert call["modelId"] == "test-model"
    assert call["toolConfig"]["toolChoice"] == {"tool": {"name": "route_request"}}


def test_a_text_only_model_reply_routes_to_the_nurse():
    client = FakeBedrock([{"text": "I think this is about food."}])
    decision = route("food?", BedrockClassifier(model_id="test-model", client=client))
    assert pairs(decision) == [(NURSE, ROUTINE)]
