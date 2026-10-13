from datetime import date
from pathlib import Path

import pytest

from arzi.rules import (
    ASK_CLAUSE,
    ASK_CONTINUITY,
    ASK_CRC,
    MAX_ASKS,
    RULES,
    _asks,
    evaluate,
    months_between,
    render_rules_md,
    with_derived_months,
)
from arzi.schema import CaseFacts, Category, Verdict

C, W, V = Verdict.LIKELY_CONTESTABLE, Verdict.WORTH_ASKING, Verdict.LIKELY_VALID
Cat = Category

# (category, facts, expected verdict, expected reason code): at least 2 per rule row
CASES = [
    # NON_DISCLOSURE_PED
    (Cat.NON_DISCLOSURE_PED, dict(months_continuous_coverage=60), C, "moratorium_completed"),
    (Cat.NON_DISCLOSURE_PED, dict(months_continuous_coverage=96, ped_disclosed_in_proposal=False, condition_related_to_claim=True), C, "moratorium_completed"),
    (Cat.NON_DISCLOSURE_PED, dict(months_continuous_coverage=59, ped_disclosed_in_proposal=True), C, "ped_was_disclosed"),
    (Cat.NON_DISCLOSURE_PED, dict(months_continuous_coverage=3, ped_disclosed_in_proposal=True, condition_related_to_claim=True), C, "ped_was_disclosed"),
    # disclosure alone is grounds to fight, whatever the (unknown) coverage length
    (Cat.NON_DISCLOSURE_PED, dict(ped_disclosed_in_proposal=True), C, "ped_was_disclosed"),
    (Cat.NON_DISCLOSURE_PED, dict(months_continuous_coverage=59, ped_disclosed_in_proposal=False, condition_related_to_claim=False), W, "condition_unrelated_to_claim"),
    (Cat.NON_DISCLOSURE_PED, dict(months_continuous_coverage=12, ped_disclosed_in_proposal=False, condition_related_to_claim=False), W, "condition_unrelated_to_claim"),
    (Cat.NON_DISCLOSURE_PED, dict(months_continuous_coverage=59, ped_disclosed_in_proposal=False, condition_related_to_claim=True), V, "non_disclosure_stands"),
    (Cat.NON_DISCLOSURE_PED, dict(months_continuous_coverage=0, ped_disclosed_in_proposal=False, condition_related_to_claim=True), V, "non_disclosure_stands"),
    # WAITING_PERIOD
    (Cat.WAITING_PERIOD, dict(is_accident=True, waiting_period_months=1, months_continuous_coverage=0), C, "accident_no_initial_waiting"),
    (Cat.WAITING_PERIOD, dict(is_accident=True, waiting_period_months=1), C, "accident_no_initial_waiting"),
    (Cat.WAITING_PERIOD, dict(is_accident=False, waiting_period_months=24, months_continuous_coverage=24), C, "waiting_period_served"),
    (Cat.WAITING_PERIOD, dict(is_accident=True, waiting_period_months=36, months_continuous_coverage=40), C, "waiting_period_served"),
    (Cat.WAITING_PERIOD, dict(is_accident=False, waiting_period_months=24, months_continuous_coverage=23), V, "waiting_period_not_served"),
    (Cat.WAITING_PERIOD, dict(is_accident=False, waiting_period_months=1, months_continuous_coverage=0), V, "waiting_period_not_served"),
    (Cat.WAITING_PERIOD, dict(is_accident=True, accident_exempt_in_wording=False, waiting_period_months=24, months_continuous_coverage=10), V, "waiting_period_not_served"),
    (Cat.WAITING_PERIOD, dict(is_accident=True, accident_exempt_in_wording=True, waiting_period_months=24, months_continuous_coverage=10), C, "accident_exempt_in_wording"),
    (Cat.WAITING_PERIOD, dict(is_accident=True, accident_exempt_in_wording=True, waiting_period_months=48), C, "accident_exempt_in_wording"),
    # served anyway, so the unknown exemption does not matter
    (Cat.WAITING_PERIOD, dict(is_accident=True, waiting_period_months=24, months_continuous_coverage=24), C, "waiting_period_served"),
    # PERMANENT_EXCLUSION
    (Cat.PERMANENT_EXCLUSION, dict(exclusion_in_policy_wording=False), C, "exclusion_not_in_wording"),
    (Cat.PERMANENT_EXCLUSION, dict(exclusion_in_policy_wording=False, exclusion_cited="cosmetic surgery"), C, "exclusion_not_in_wording"),
    (Cat.PERMANENT_EXCLUSION, dict(exclusion_in_policy_wording=True), V, "exclusion_in_wording"),
    (Cat.PERMANENT_EXCLUSION, dict(exclusion_in_policy_wording=True, exclusion_cited="infertility treatment"), V, "exclusion_in_wording"),
    # NO_HOSPITALISATION_NEEDED
    (Cat.NO_HOSPITALISATION_NEEDED, dict(hospital_stay_hours=24, is_listed_daycare_procedure=False), C, "inpatient_stay_or_daycare"),
    (Cat.NO_HOSPITALISATION_NEEDED, dict(hospital_stay_hours=6, is_listed_daycare_procedure=True), C, "inpatient_stay_or_daycare"),
    (Cat.NO_HOSPITALISATION_NEEDED, dict(hospital_stay_hours=72), C, "inpatient_stay_or_daycare"),
    (Cat.NO_HOSPITALISATION_NEEDED, dict(hospital_stay_hours=23, is_listed_daycare_procedure=False), W, "short_stay_not_daycare"),
    (Cat.NO_HOSPITALISATION_NEEDED, dict(hospital_stay_hours=4, is_listed_daycare_procedure=False), W, "short_stay_not_daycare"),
    # ROOM_RENT_PROPORTIONATE
    (Cat.ROOM_RENT_PROPORTIONATE, dict(room_rent_charged_per_day=5000, room_rent_limit_per_day=5000), C, "room_rent_within_limit"),
    (Cat.ROOM_RENT_PROPORTIONATE, dict(room_rent_charged_per_day=3500, room_rent_limit_per_day=4000), C, "room_rent_within_limit"),
    (Cat.ROOM_RENT_PROPORTIONATE, dict(room_rent_charged_per_day=5001, room_rent_limit_per_day=5000), W, "room_rent_over_limit"),
    (Cat.ROOM_RENT_PROPORTIONATE, dict(room_rent_charged_per_day=9000, room_rent_limit_per_day=3000), W, "room_rent_over_limit"),
    # DOCUMENTS_OR_LATE_INTIMATION
    (Cat.DOCUMENTS_OR_LATE_INTIMATION, dict(), W, "documents_or_delay"),
    (Cat.DOCUMENTS_OR_LATE_INTIMATION, dict(hospital_stay_hours=48, crc_approval_mentioned=True), W, "documents_or_delay"),
    # POLICY_LAPSED
    (Cat.POLICY_LAPSED, dict(premium_paid_within_grace=True), C, "premium_within_grace"),
    (Cat.POLICY_LAPSED, dict(premium_paid_within_grace=True, months_continuous_coverage=30), C, "premium_within_grace"),
    (Cat.POLICY_LAPSED, dict(premium_paid_within_grace=False), V, "policy_lapsed"),
    (Cat.POLICY_LAPSED, dict(premium_paid_within_grace=False, months_continuous_coverage=30), V, "policy_lapsed"),
    # SUM_INSURED_EXHAUSTED
    (Cat.SUM_INSURED_EXHAUSTED, dict(restore_benefit_available_unused=True), W, "restore_benefit_unused"),
    (Cat.SUM_INSURED_EXHAUSTED, dict(restore_benefit_available_unused=True, crc_approval_mentioned=True), W, "restore_benefit_unused"),
    (Cat.SUM_INSURED_EXHAUSTED, dict(restore_benefit_available_unused=False), V, "sum_insured_exhausted"),
    (Cat.SUM_INSURED_EXHAUSTED, dict(restore_benefit_available_unused=False, crc_approval_mentioned=False), V, "sum_insured_exhausted"),
    # OTHER
    (Cat.OTHER, dict(), W, "uncategorised"),
    (Cat.OTHER, dict(is_accident=True, hospital_stay_hours=48), W, "uncategorised"),
]


@pytest.mark.parametrize("category,facts,verdict,code", CASES)
def test_rule_table(category, facts, verdict, code):
    result = evaluate(category, CaseFacts(**facts))
    assert result.verdict == verdict
    assert result.reason_codes == (code,)
    assert result.missing_facts == ()


def test_every_rule_row_has_two_cases():
    seen = {}
    for category, _, _, code in CASES:
        seen[(category, code)] = seen.get((category, code), 0) + 1
    for category, rules in RULES.items():
        for rule in rules:
            assert seen.get((category, rule.code), 0) >= 2, f"{category.value}/{rule.code}"


# A missing fact that a rule cannot be decided without -> WORTH_ASKING, never a guess.
MISSING = [
    (Cat.NON_DISCLOSURE_PED, dict(), ("months_continuous_coverage", "ped_disclosed_in_proposal")),
    # would be "valid" if we guessed the coverage was short
    (Cat.NON_DISCLOSURE_PED, dict(ped_disclosed_in_proposal=False, condition_related_to_claim=True), ("months_continuous_coverage",)),
    (Cat.NON_DISCLOSURE_PED, dict(months_continuous_coverage=20), ("ped_disclosed_in_proposal",)),
    (Cat.NON_DISCLOSURE_PED, dict(months_continuous_coverage=20, ped_disclosed_in_proposal=False), ("condition_related_to_claim",)),
    (Cat.WAITING_PERIOD, dict(), ("is_accident", "waiting_period_months", "accident_exempt_in_wording", "months_continuous_coverage")),
    (Cat.WAITING_PERIOD, dict(is_accident=True), ("waiting_period_months", "accident_exempt_in_wording", "months_continuous_coverage")),
    # accident, longer waiting period not served, wording unknown
    (Cat.WAITING_PERIOD, dict(is_accident=True, waiting_period_months=24, months_continuous_coverage=10), ("accident_exempt_in_wording",)),
    # would be "valid" if we guessed it was not an accident
    (Cat.WAITING_PERIOD, dict(waiting_period_months=24, months_continuous_coverage=10), ("is_accident", "accident_exempt_in_wording")),
    (Cat.WAITING_PERIOD, dict(is_accident=None, waiting_period_months=1, months_continuous_coverage=0), ("is_accident",)),
    (Cat.WAITING_PERIOD, dict(is_accident=False, waiting_period_months=24), ("months_continuous_coverage",)),
    (Cat.PERMANENT_EXCLUSION, dict(), ("exclusion_in_policy_wording",)),
    (Cat.NO_HOSPITALISATION_NEEDED, dict(), ("hospital_stay_hours", "is_listed_daycare_procedure")),
    (Cat.NO_HOSPITALISATION_NEEDED, dict(hospital_stay_hours=5), ("is_listed_daycare_procedure",)),
    (Cat.NO_HOSPITALISATION_NEEDED, dict(is_listed_daycare_procedure=False), ("hospital_stay_hours",)),
    (Cat.ROOM_RENT_PROPORTIONATE, dict(room_rent_charged_per_day=6000), ("room_rent_limit_per_day",)),
    (Cat.POLICY_LAPSED, dict(), ("premium_paid_within_grace",)),
    (Cat.SUM_INSURED_EXHAUSTED, dict(), ("restore_benefit_available_unused",)),
]


@pytest.mark.parametrize("category,facts,missing", MISSING)
def test_missing_fact_is_worth_asking(category, facts, missing):
    result = evaluate(category, CaseFacts(**facts))
    assert result.verdict == W
    assert result.missing_facts == missing
    assert result.reason_codes == tuple(f"missing_fact:{m}" for m in missing)


def test_missing_fact_that_does_not_matter_is_ignored():
    # not an accident, so the unknown-free second rule decides
    r = evaluate(Cat.WAITING_PERIOD, CaseFacts(is_accident=None, waiting_period_months=24, months_continuous_coverage=30))
    assert (r.verdict, r.reason_codes) == (C, ("waiting_period_served",))


def test_months_between():
    assert months_between(date(2020, 1, 15), date(2025, 1, 15)) == 60
    assert months_between(date(2020, 1, 15), date(2025, 1, 14)) == 59
    assert months_between(date(2024, 1, 31), date(2024, 2, 28)) == 0
    assert months_between(date(2023, 11, 1), date(2024, 2, 1)) == 3


def test_months_derived_from_dates_override_stated_count():
    facts = CaseFacts(policy_inception_date=date(2020, 3, 10), admission_date=date(2025, 3, 9), months_continuous_coverage=70)
    assert with_derived_months(facts).months_continuous_coverage == 59
    assert with_derived_months(CaseFacts(months_continuous_coverage=70)).months_continuous_coverage == 70


def test_moratorium_boundary_from_dates():
    base = dict(policy_inception_date=date(2020, 3, 10), ped_disclosed_in_proposal=False, condition_related_to_claim=True)
    assert evaluate(Cat.NON_DISCLOSURE_PED, CaseFacts(admission_date=date(2025, 3, 9), **base)).verdict == V
    assert evaluate(Cat.NON_DISCLOSURE_PED, CaseFacts(admission_date=date(2025, 3, 10), **base)).verdict == C


def test_asks_always_include_clause_and_crc_unless_mentioned():
    for crc in (None, False):
        r = evaluate(Cat.OTHER, CaseFacts(crc_approval_mentioned=crc))
        assert r.ask_insurer_for == (ASK_CLAUSE, ASK_CRC)
    assert evaluate(Cat.OTHER, CaseFacts(crc_approval_mentioned=True)).ask_insurer_for == (ASK_CLAUSE,)


def test_ask_cap_keeps_required_items_first():
    asks = _asks(CaseFacts(), tuple(f"extra {i}" for i in range(10)))
    assert len(asks) == MAX_ASKS == 6
    assert asks[:2] == (ASK_CLAUSE, ASK_CRC)
    assert _asks(CaseFacts(), (ASK_CLAUSE, "x", "x")) == (ASK_CLAUSE, ASK_CRC, "x")


def test_months_mismatch_asks_about_continuity():
    dates = dict(policy_inception_date=date(2019, 6, 1), admission_date=date(2025, 6, 1))  # 72 months
    for stated, expected in [(14, True), (70, True), (71, False), (72, False), (73, False), (None, False)]:
        r = evaluate(Cat.NON_DISCLOSURE_PED, CaseFacts(months_continuous_coverage=stated, **dates))
        assert r.verdict == C
        assert (ASK_CONTINUITY in r.ask_insurer_for) is expected, stated
        assert r.ask_insurer_for[:2] == (ASK_CLAUSE, ASK_CRC)
    # no dates: nothing to compare the stated count with
    assert ASK_CONTINUITY not in evaluate(Cat.NON_DISCLOSURE_PED, CaseFacts(months_continuous_coverage=70)).ask_insurer_for


def test_asks_are_unique_and_capped():
    for category in Category:
        r = evaluate(category, CaseFacts())
        assert r.ask_insurer_for[0] == ASK_CLAUSE
        assert len(set(r.ask_insurer_for)) == len(r.ask_insurer_for) <= MAX_ASKS


def test_every_category_has_rules_ending_in_a_fallback():
    assert set(RULES) == set(Category)
    for rules in RULES.values():
        assert rules[-1].needs == ()
        codes = [r.code for r in rules]
        assert len(codes) == len(set(codes))


def test_rules_md_is_in_sync():
    path = Path(__file__).parent.parent / "RULES.md"
    assert path.read_text() == render_rules_md(), "run: python -m arzi.rules > RULES.md"
