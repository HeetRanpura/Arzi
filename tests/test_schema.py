from datetime import date

import pytest
from pydantic import ValidationError

from arzi.schema import CaseFacts, Category, ModelOutput, Verdict


def test_case_facts_all_optional():
    facts = CaseFacts()
    assert all(v is None for v in facts.model_dump().values())


def test_model_output_json_round_trip():
    out = ModelOutput(
        category=Category.NON_DISCLOSURE_PED,
        verdict=Verdict.LIKELY_VALID,
        facts=CaseFacts(policy_inception_date=date(2022, 4, 1), admission_date=date(2024, 6, 15), months_continuous_coverage=26),
        reason="The condition was not declared and cover is under 60 months.",
        ask_insurer_for=["The exact policy clause relied on"],
    )
    data = out.model_dump_json()
    assert '"non_disclosure_ped"' in data and '"2022-04-01"' in data
    assert ModelOutput.model_validate_json(data) == out


def test_enum_values_are_stable():
    # these strings are the training targets; renaming them invalidates datasets
    assert [c.value for c in Category] == [
        "non_disclosure_ped",
        "waiting_period",
        "permanent_exclusion",
        "no_hospitalisation_needed",
        "room_rent_proportionate",
        "documents_or_late_intimation",
        "policy_lapsed",
        "sum_insured_exhausted",
        "other",
    ]
    assert [v.value for v in Verdict] == ["likely_contestable", "worth_asking", "likely_valid"]


def test_reason_length_limit():
    with pytest.raises(ValidationError):
        ModelOutput(category="other", verdict="worth_asking", facts={}, reason="x" * 601)


def test_ask_list_limit():
    with pytest.raises(ValidationError):
        ModelOutput(category="other", verdict="worth_asking", facts={}, reason="ok", ask_insurer_for=["a"] * 7)
