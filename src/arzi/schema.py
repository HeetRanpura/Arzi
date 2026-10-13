"""Pydantic models for a case, plus the single parser for model output.

The same `parse_model_output` is used by eval (base and fine-tuned) and by the
local app, so every model is judged through identical parsing.
"""

from __future__ import annotations

import json
import re
from datetime import date
from enum import Enum

from pydantic import BaseModel, Field, ValidationError


class Category(str, Enum):
    NON_DISCLOSURE_PED = "non_disclosure_ped"
    WAITING_PERIOD = "waiting_period"
    PERMANENT_EXCLUSION = "permanent_exclusion"
    NO_HOSPITALISATION_NEEDED = "no_hospitalisation_needed"
    ROOM_RENT_PROPORTIONATE = "room_rent_proportionate"
    DOCUMENTS_OR_LATE_INTIMATION = "documents_or_late_intimation"
    POLICY_LAPSED = "policy_lapsed"
    SUM_INSURED_EXHAUSTED = "sum_insured_exhausted"
    OTHER = "other"


class Verdict(str, Enum):
    LIKELY_CONTESTABLE = "likely_contestable"
    WORTH_ASKING = "worth_asking"
    LIKELY_VALID = "likely_valid"


class CaseFacts(BaseModel):
    # all optional: a letter may not state them
    policy_inception_date: date | None = None  # first policy with continuous cover, incl. portability
    admission_date: date | None = None
    months_continuous_coverage: int | None = None  # derived; see rules.py
    condition_named_by_insurer: str | None = None
    ped_disclosed_in_proposal: bool | None = None
    condition_related_to_claim: bool | None = None
    waiting_period_months: int | None = None  # the waiting period the insurer relies on
    is_accident: bool | None = None
    accident_exempt_in_wording: bool | None = None  # does the wording exempt accidents from this waiting period
    exclusion_cited: str | None = None
    exclusion_in_policy_wording: bool | None = None
    hospital_stay_hours: int | None = None
    is_listed_daycare_procedure: bool | None = None
    room_rent_limit_per_day: int | None = None  # INR
    room_rent_charged_per_day: int | None = None  # INR
    premium_paid_within_grace: bool | None = None
    restore_benefit_available_unused: bool | None = None
    crc_approval_mentioned: bool | None = None  # Claims Review Committee


class ModelOutput(BaseModel):
    category: Category
    verdict: Verdict
    facts: CaseFacts
    reason: str = Field(max_length=600)  # plain English, <= ~80 words
    ask_insurer_for: list[str] = Field(default_factory=list, max_length=6)


class ParseError(ValueError):
    """Model text could not be turned into a ModelOutput. Counts as a wrong answer in eval."""


_THINK = re.compile(r"<think>.*?</think>", re.DOTALL)
_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def parse_model_output(text: str) -> ModelOutput:
    """Parse raw model text into a ModelOutput.

    Tolerates a leading <think> block, ``` fences and text after the JSON object.
    Missing required fields and invalid enum values raise ParseError.
    """
    text = _THINK.sub("", text)
    fenced = _FENCE.search(text)
    if fenced:
        text = fenced.group(1)
    start = text.find("{")
    if start < 0:
        raise ParseError("no JSON object found")
    try:
        obj, _ = json.JSONDecoder().raw_decode(text[start:])
    except json.JSONDecodeError as e:
        raise ParseError(f"invalid JSON: {e}") from e
    try:
        return ModelOutput.model_validate(obj)
    except ValidationError as e:
        raise ParseError(f"schema mismatch: {e}") from e
