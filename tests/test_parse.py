import json
from datetime import date

import pytest

from arzi.schema import Category, ParseError, Verdict, parse_model_output

GOOD = {
    "category": "waiting_period",
    "verdict": "likely_contestable",
    "facts": {"policy_inception_date": "2021-02-01", "admission_date": "2024-03-05", "waiting_period_months": 24, "is_accident": False},
    "reason": "Cover has run longer than the waiting period relied on.",
    "ask_insurer_for": ["The exact policy clause relied on"],
}
GOOD_JSON = json.dumps(GOOD, indent=2)


def check(out):
    assert out.category == Category.WAITING_PERIOD
    assert out.verdict == Verdict.LIKELY_CONTESTABLE
    assert out.facts.policy_inception_date == date(2021, 2, 1)
    assert out.facts.waiting_period_months == 24
    assert out.facts.is_accident is False
    assert out.facts.hospital_stay_hours is None


def test_valid_json():
    check(parse_model_output(GOOD_JSON))


@pytest.mark.parametrize("fence", ["```json\n{}\n```", "```\n{}\n```", "Here is the result:\n```json\n{}\n```\nHope this helps."])
def test_fenced_json(fence):
    check(parse_model_output(fence.replace("{}", GOOD_JSON)))


def test_trailing_text():
    check(parse_model_output(GOOD_JSON + "\n\nNote: this is not legal advice. {see clause 4}"))


def test_leading_text_and_think_block():
    check(parse_model_output('<think>maybe {"category": "other"}?</think>\nAnswer: ' + GOOD_JSON))


@pytest.mark.parametrize("missing", ["category", "verdict", "facts", "reason"])
def test_missing_required_field(missing):
    with pytest.raises(ParseError):
        parse_model_output(json.dumps({k: v for k, v in GOOD.items() if k != missing}))


def test_missing_optional_fields_default():
    out = parse_model_output(json.dumps({**{k: v for k, v in GOOD.items() if k != "ask_insurer_for"}, "facts": {}}))
    assert out.ask_insurer_for == []
    assert out.facts.admission_date is None


@pytest.mark.parametrize("field,value", [("category", "fraud"), ("verdict", "contestable"), ("verdict", "LIKELY_VALID"), ("category", None)])
def test_invalid_enum_value(field, value):
    with pytest.raises(ParseError):
        parse_model_output(json.dumps({**GOOD, field: value}))


@pytest.mark.parametrize(
    "text",
    ["", "I cannot determine this.", "{not json}", GOOD_JSON[:-20], "[1, 2, 3]", json.dumps({**GOOD, "facts": {"admission_date": "5th March"}})],
)
def test_garbage_raises_parse_error(text):
    with pytest.raises(ParseError):
        parse_model_output(text)
