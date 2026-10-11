"""Model classifier on Amazon Bedrock.

The model is forced to answer through one tool, so the reply is structured JSON
and never free text. Everything it returns is validated in parse_tool_input().
Anything unexpected raises, and the router then sends the request to the nurse.
"""
from __future__ import annotations

import os

from .models import ROUTINE, URGENT, Classification, Intent

CATEGORIES = ["cleaning_environment", "dietary", "tech_amenities", "clinical", "unknown"]

SYSTEM_PROMPT = """You sort hospital inpatients' call-bell requests so that non-clinical ones \
reach the right support team and clinical ones reach the nurse.

Categories:
- cleaning_environment: room cleaning, spills, linens, pillows, blankets, room temperature, \
lights, plumbing, noise from equipment in the room, broken furniture.
- dietary: food, drinks, meal trays, menus, utensils, and questions about ordering food, \
including meals for visitors.
- tech_amenities: TV, remote, Wi-Fi, phone, chargers, tablet, visiting hours, parking, \
chaplain or interpreter requests, general information.
- clinical: anything about the patient's body, symptoms, pain, breathing, bleeding, wounds, \
dressings, medication, IV lines or medical devices, tests, procedures, mobility or toileting \
help, sleep, mood, safety, a slip, trip or near-fall even if the patient was not hurt, \
questions about test results, the care plan or when the patient is going home, or any \
question for a nurse or doctor.
- unknown: you cannot tell what the patient needs.

Rules:
1. Patient safety comes first. If a request could be clinical, it is clinical.
2. A clinical intent is "urgent" when it describes a new, worsening or severe symptom, an \
injury, a fall, a reaction to a medicine, a problem with a line or device, thoughts of \
self-harm, or anything that could mean the patient is getting worse. Patients often use \
everyday words, not medical ones; judge the meaning. If unsure, choose urgent.
3. Other clinical intents are "routine". Non-clinical intents are always "routine".
4. A request can contain several needs. Return one intent per need. If a problem in the \
room has already affected the patient's body or safety (a wet floor they slipped on), return \
both the room need and a clinical intent.
5. Figures of speech are not symptoms ("I'd kill for a coffee" is dietary). If you cannot \
tell whether a phrase is a figure of speech, treat it as clinical.
6. The request may be in any language, or mix languages. Write every summary in English, \
in at most 12 words, using only what the patient said. Never add details.
7. Report your confidence from 0 to 1. Lower it when the request is vague or ambiguous."""

TOOL = {
    "toolSpec": {
        "name": "route_request",
        "description": "Record every need found in the patient's request.",
        "inputSchema": {"json": {
            "type": "object",
            "properties": {
                "language": {"type": "string", "description": "ISO 639-1 code of the patient's language"},
                "intents": {
                    "type": "array", "minItems": 1,
                    "items": {
                        "type": "object",
                        "properties": {
                            "category": {"type": "string", "enum": CATEGORIES},
                            "priority": {"type": "string", "enum": [URGENT, ROUTINE]},
                            "summary_en": {"type": "string"},
                        },
                        "required": ["category", "priority", "summary_en"],
                    },
                },
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            },
            "required": ["language", "intents", "confidence"],
        }},
    }
}


def parse_tool_input(data: dict) -> Classification:
    """Validate the model's structured answer. Raises ValueError on anything unexpected."""
    intents_raw = data.get("intents")
    if not isinstance(intents_raw, list) or not intents_raw:
        raise ValueError("model returned no intents")
    intents = []
    for item in intents_raw:
        category = item.get("category")
        if category not in CATEGORIES:
            raise ValueError(f"unknown category from model: {category!r}")
        priority = item.get("priority")
        if priority not in (URGENT, ROUTINE):
            raise ValueError(f"unknown priority from model: {priority!r}")
        if category != "clinical":
            priority = ROUTINE          # only clinical requests can be urgent
        intents.append(Intent(category=category, priority=priority,
                              summary=str(item.get("summary_en", "")).strip()[:160]))
    confidence = float(data.get("confidence", 0))
    if not 0 <= confidence <= 1:
        raise ValueError(f"confidence out of range: {confidence}")
    return Classification(intents=intents, confidence=confidence,
                          language=data.get("language"), source="llm")


class BedrockClassifier:
    source = "llm"

    def __init__(self, model_id: str | None = None, client=None):
        self.model_id = model_id or os.environ["BEDROCK_MODEL_ID"]
        if client is None:
            import boto3
            from botocore.config import Config
            client = boto3.client(
                "bedrock-runtime",
                region_name=os.getenv("AWS_REGION", "us-east-1"),
                # a slow model must not leave a patient waiting; the router falls back to the nurse
                config=Config(read_timeout=8, connect_timeout=3, retries={"max_attempts": 2}),
            )
        self.client = client
        # Temperature 0 keeps answers the same from run to run. Set LLM_TEMPERATURE to an
        # empty value for a model that does not accept the setting.
        self.inference_config = {"maxTokens": 600}
        temperature = os.getenv("LLM_TEMPERATURE", "0").strip()
        if temperature:
            self.inference_config["temperature"] = float(temperature)
        # running totals, so the evaluation can report tokens and cost per request
        self.calls = 0
        self.input_tokens = 0
        self.output_tokens = 0

    def classify(self, text: str) -> Classification:
        response = self.client.converse(
            modelId=self.model_id,
            system=[{"text": SYSTEM_PROMPT}],
            messages=[{"role": "user", "content": [{"text": f"Patient request:\n{text}"}]}],
            toolConfig={"tools": [TOOL], "toolChoice": {"tool": {"name": "route_request"}}},
            inferenceConfig=self.inference_config,
        )
        usage = response.get("usage") or {}
        self.calls += 1
        self.input_tokens += int(usage.get("inputTokens", 0))
        self.output_tokens += int(usage.get("outputTokens", 0))
        for block in response["output"]["message"]["content"]:
            if "toolUse" in block:
                return parse_tool_input(block["toolUse"]["input"])
        raise ValueError("model did not call the routing tool")
