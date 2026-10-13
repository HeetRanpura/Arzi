"""Deterministic rule engine: CaseFacts + Category -> verdict + reason codes.

This is the source of truth for synthetic labels and the cross-check in the app.
RULES.md is rendered from the RULES table below:

    python -m arzi.rules > RULES.md

How a category is evaluated (a rule's test is three-valued: true, false, or
cannot tell because a fact is missing):

1. Every LIKELY_CONTESTABLE rule is checked. If any is clearly true, the verdict
   is LIKELY_CONTESTABLE. A missing fact elsewhere never blocks this.
2. Otherwise, if any of them could not be decided, the verdict is WORTH_ASKING
   with `missing_fact:<field>` reason codes.
3. Only when every contestable rule is decidably false are the remaining rules
   tried top to bottom, first match wins. An undecidable one again gives
   WORTH_ASKING, so LIKELY_VALID is never reached by guessing.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Callable

from arzi.schema import CaseFacts, Category, Verdict

MORATORIUM_MONTHS = 60
INITIAL_WAITING_MAX_MONTHS = 1
MIN_INPATIENT_HOURS = 24
MAX_ASKS = 6  # ModelOutput.ask_insurer_for limit

ASK_CLAUSE = "The exact policy clause relied on"
ASK_CRC = "Confirmation that the Claims Review Committee approved this repudiation"
ASK_CONTINUITY = "Confirm policy inception date and continuity of cover, including portability"
MONTHS_MISMATCH_TOLERANCE = 1

Tri = bool | None  # None = cannot tell from the facts given


def _and(*xs: Tri) -> Tri:
    if any(x is False for x in xs):
        return False
    return None if any(x is None for x in xs) else True


def _or(*xs: Tri) -> Tri:
    if any(x is True for x in xs):
        return True
    return None if any(x is None for x in xs) else False


def _not(x: Tri) -> Tri:
    return None if x is None else not x


def _ge(a: int | None, b: int | None) -> Tri:
    return None if a is None or b is None else a >= b


def _le(a: int | None, b: int | None) -> Tri:
    return None if a is None or b is None else a <= b


def months_between(start: date, end: date) -> int:
    """Whole completed months from start to end (31 Jan -> 28 Feb is 0 months)."""
    months = (end.year - start.year) * 12 + (end.month - start.month)
    if end.day < start.day:
        months -= 1
    return months


def with_derived_months(facts: CaseFacts) -> CaseFacts:
    """Fill months_continuous_coverage from the two dates when both are known.

    The dates win over any stated month count; a stated count is used only when
    a date is missing.
    """
    if facts.policy_inception_date and facts.admission_date:
        months = months_between(facts.policy_inception_date, facts.admission_date)
        return facts.model_copy(update={"months_continuous_coverage": months})
    return facts


@dataclass(frozen=True)
class Rule:
    code: str  # reason code emitted when this rule decides the case
    when: str  # human-readable condition, shown in RULES.md
    verdict: Verdict
    test: Callable[[CaseFacts], Tri] = lambda f: True
    needs: tuple[str, ...] = ()  # facts the test reads
    note: str = ""
    asks: tuple[str, ...] = ()  # extra items for ask_insurer_for when this rule decides


C, W, V = Verdict.LIKELY_CONTESTABLE, Verdict.WORTH_ASKING, Verdict.LIKELY_VALID

RULES: dict[Category, tuple[Rule, ...]] = {
    Category.NON_DISCLOSURE_PED: (
        Rule(
            "moratorium_completed",
            f"`months_continuous_coverage` >= {MORATORIUM_MONTHS}",
            C,
            lambda f: _ge(f.months_continuous_coverage, MORATORIUM_MONTHS),
            ("months_continuous_coverage",),
            note=f"Moratorium: after {MORATORIUM_MONTHS} months of continuous cover a claim "
            "cannot be contested for non-disclosure, except for established fraud.",
        ),
        Rule(
            "ped_was_disclosed",
            "`ped_disclosed_in_proposal` is true",
            C,
            lambda f: f.ped_disclosed_in_proposal,
            ("ped_disclosed_in_proposal",),
            note="The condition was declared in the proposal form, so it was not concealed.",
        ),
        Rule(
            "condition_unrelated_to_claim",
            "`condition_related_to_claim` is false",
            W,
            lambda f: _not(f.condition_related_to_claim),
            ("condition_related_to_claim",),
            note="The undisclosed condition has no link to the illness claimed for.",
            asks=("The medical basis for linking the named condition to this claim",),
        ),
        Rule("non_disclosure_stands", "otherwise", V),
    ),
    Category.WAITING_PERIOD: (
        Rule(
            "accident_no_initial_waiting",
            f"`is_accident` is true and `waiting_period_months` <= {INITIAL_WAITING_MAX_MONTHS}",
            C,
            lambda f: _and(f.is_accident, _le(f.waiting_period_months, INITIAL_WAITING_MAX_MONTHS)),
            ("is_accident", "waiting_period_months"),
            note="The initial waiting period does not apply to accidents.",
        ),
        Rule(
            "accident_exempt_in_wording",
            f"`is_accident` is true, `waiting_period_months` > {INITIAL_WAITING_MAX_MONTHS} "
            "and `accident_exempt_in_wording` is true",
            C,
            lambda f: _and(
                f.is_accident,
                _not(_le(f.waiting_period_months, INITIAL_WAITING_MAX_MONTHS)),
                f.accident_exempt_in_wording,
            ),
            ("is_accident", "waiting_period_months", "accident_exempt_in_wording"),
            note="Whether accidents escape a longer waiting period depends on the policy wording, "
            "so it is a fact of the case, not a fixed rule.",
        ),
        Rule(
            "waiting_period_served",
            "`months_continuous_coverage` >= `waiting_period_months`",
            C,
            lambda f: _ge(f.months_continuous_coverage, f.waiting_period_months),
            ("months_continuous_coverage", "waiting_period_months"),
            note="Counts continuous cover carried over through portability.",
        ),
        Rule("waiting_period_not_served", "otherwise", V),
    ),
    Category.PERMANENT_EXCLUSION: (
        Rule(
            "exclusion_not_in_wording",
            "`exclusion_in_policy_wording` is false",
            C,
            lambda f: _not(f.exclusion_in_policy_wording),
            ("exclusion_in_policy_wording",),
            note="The exclusion the insurer cites does not appear in the policy wording.",
        ),
        Rule("exclusion_in_wording", "otherwise", V),
    ),
    Category.NO_HOSPITALISATION_NEEDED: (
        Rule(
            "inpatient_stay_or_daycare",
            f"`hospital_stay_hours` >= {MIN_INPATIENT_HOURS} or `is_listed_daycare_procedure` is true",
            C,
            lambda f: _or(_ge(f.hospital_stay_hours, MIN_INPATIENT_HOURS), f.is_listed_daycare_procedure),
            ("hospital_stay_hours", "is_listed_daycare_procedure"),
        ),
        Rule(
            "short_stay_not_daycare",
            "otherwise",
            W,
            asks=("The medical opinion relied on to say hospitalisation was not needed",),
        ),
    ),
    Category.ROOM_RENT_PROPORTIONATE: (
        Rule(
            "room_rent_within_limit",
            "`room_rent_charged_per_day` <= `room_rent_limit_per_day`",
            C,
            lambda f: _le(f.room_rent_charged_per_day, f.room_rent_limit_per_day),
            ("room_rent_charged_per_day", "room_rent_limit_per_day"),
        ),
        Rule(
            "room_rent_over_limit",
            "otherwise",
            W,
            note="A deduction is allowed; check the deduction maths.",
            asks=("The line-by-line proportionate deduction calculation",),
        ),
    ),
    Category.DOCUMENTS_OR_LATE_INTIMATION: (
        Rule(
            "documents_or_delay",
            "always",
            W,
            note="Resubmit the documents or explain the delay.",
            asks=("The exact list of documents still pending",),
        ),
    ),
    Category.POLICY_LAPSED: (
        Rule(
            "premium_within_grace",
            "`premium_paid_within_grace` is true",
            C,
            lambda f: f.premium_paid_within_grace,
            ("premium_paid_within_grace",),
        ),
        Rule("policy_lapsed", "otherwise", V),
    ),
    Category.SUM_INSURED_EXHAUSTED: (
        Rule(
            "restore_benefit_unused",
            "`restore_benefit_available_unused` is true",
            W,
            lambda f: f.restore_benefit_available_unused,
            ("restore_benefit_available_unused",),
            asks=("A statement of the sum insured used this policy year and why restore benefit was not applied",),
        ),
        Rule("sum_insured_exhausted", "otherwise", V),
    ),
    Category.OTHER: (Rule("uncategorised", "always", W),),
}

# What to ask the insurer for when a fact the rules need is missing.
# Facts only the family knows (e.g. is_accident) have no entry.
MISSING_FACT_ASKS: dict[str, str] = {
    "months_continuous_coverage": "The policy inception date being counted from, including any ported cover",
    "ped_disclosed_in_proposal": "A copy of the proposal form that was signed",
    "condition_related_to_claim": "The medical basis for linking the named condition to this claim",
    "waiting_period_months": "Which waiting period is being applied and its length",
    "accident_exempt_in_wording": "Whether the policy wording exempts accidents from this waiting period, with the clause",
    "exclusion_in_policy_wording": "The page and clause number of the exclusion in the policy wording",
    "hospital_stay_hours": "The medical opinion relied on to say hospitalisation was not needed",
    "is_listed_daycare_procedure": "The medical opinion relied on to say hospitalisation was not needed",
    "room_rent_limit_per_day": "The room rent limit applied and the deduction calculation",
    "room_rent_charged_per_day": "The room rent limit applied and the deduction calculation",
    "premium_paid_within_grace": "The premium due date, the grace period and the date payment was received",
    "restore_benefit_available_unused": "A statement of the sum insured used this policy year and whether restore benefit applies",
}


@dataclass(frozen=True)
class RuleResult:
    verdict: Verdict
    reason_codes: tuple[str, ...]
    ask_insurer_for: tuple[str, ...]
    missing_facts: tuple[str, ...] = ()


def _asks(facts: CaseFacts, extra: tuple[str, ...]) -> tuple[str, ...]:
    """Required items first so the cap never cuts them."""
    asks = [ASK_CLAUSE]
    if facts.crc_approval_mentioned is not True:
        asks.append(ASK_CRC)
    asks.extend(extra)
    return tuple(dict.fromkeys(asks))[:MAX_ASKS]


def _undecided(facts: CaseFacts, rules: list[Rule], extra: tuple[str, ...]) -> RuleResult:
    missing = tuple(dict.fromkeys(n for r in rules for n in r.needs if getattr(facts, n) is None))
    asks = tuple(MISSING_FACT_ASKS[n] for n in missing if n in MISSING_FACT_ASKS)
    return RuleResult(
        Verdict.WORTH_ASKING,
        tuple(f"missing_fact:{n}" for n in missing),
        _asks(facts, extra + asks),
        missing,
    )


def evaluate(category: Category, facts: CaseFacts) -> RuleResult:
    stated_months = facts.months_continuous_coverage
    facts = with_derived_months(facts)
    extra: tuple[str, ...] = ()
    # insurers often count from the current policy and ignore ported cover
    if stated_months is not None and abs(facts.months_continuous_coverage - stated_months) > MONTHS_MISMATCH_TOLERANCE:
        extra = (ASK_CONTINUITY,)

    rules = RULES[category]
    contestable = [(r, r.test(facts)) for r in rules if r.verdict is Verdict.LIKELY_CONTESTABLE]
    for rule, matched in contestable:
        if matched:
            return RuleResult(rule.verdict, (rule.code,), _asks(facts, extra + rule.asks))
    undecided = [r for r, matched in contestable if matched is None]
    if undecided:
        return _undecided(facts, undecided, extra)

    for rule in rules:
        if rule.verdict is Verdict.LIKELY_CONTESTABLE:
            continue
        matched = rule.test(facts)
        if matched is None:
            return _undecided(facts, [rule], extra)
        if matched:
            return RuleResult(rule.verdict, (rule.code,), _asks(facts, extra + rule.asks))
    raise AssertionError(f"no fallback rule for {category}")  # every category ends in an unconditional rule


def render_rules_md() -> str:
    lines = [
        "# Arzi rules (v1)",
        "",
        "<!-- Generated by `python -m arzi.rules > RULES.md`. Edit rules.py, not this file. -->",
        "",
        "**Simplified prototype rule set. Not legal advice. Regulations change.**",
        "",
        "These rules turn the facts of a rejected claim into one of three verdicts. They label all",
        "synthetic training data and cross-check the model's answer inside the app.",
        "",
        "| Verdict | Meaning |",
        "| --- | --- |",
        "| `likely_contestable` | On the stated facts the rejection looks wrong. Worth a formal complaint. |",
        "| `worth_asking` | Not clearly wrong, or a fact is missing. Ask the insurer before deciding. |",
        "| `likely_valid` | On the stated facts the rejection looks correct. |",
        "",
        "## How rules are applied",
        "",
        "1. **Evidence for the family wins.** Every `likely_contestable` rule of the category is checked.",
        "   If any one is clearly true the verdict is `likely_contestable`, even if other facts are missing.",
        "2. **Never guess.** If none is true but one could not be decided because a fact is missing,",
        "   the verdict is `worth_asking`. (A rule can still be decided with a fact missing: \"A and B\"",
        "   is false as soon as A is false.)",
        "3. Only when every contestable rule is clearly false are the remaining rules tried top to bottom,",
        "   first match wins. A missing fact there also gives `worth_asking`, so `likely_valid` is only",
        "   ever reached on known facts.",
        "4. `months_continuous_coverage` is the number of whole completed months from",
        "   `policy_inception_date` to `admission_date`. When both dates are known they override any",
        "   stated month count.",
        "",
        "## Rules by category",
    ]
    for category, rules in RULES.items():
        lines += ["", f"### `{category.value}`", "", "| # | Rule | Verdict | Reason code | Note |", "| --- | --- | --- | --- | --- |"]
        for i, r in enumerate(rules, 1):
            lines.append(f"| {i} | {r.when} | `{r.verdict.value}` | `{r.code}` | {r.note} |")
    lines += [
        "",
        "## What to ask the insurer for",
        "",
        f"- Always: \"{ASK_CLAUSE}\".",
        f"- Unless the letter says the Claims Review Committee approved the rejection: \"{ASK_CRC}\".",
        f"- When the dates give a month count more than {MONTHS_MISMATCH_TOLERANCE} away from a stated count: \"{ASK_CONTINUITY}\".",
        "- Some rules add their own item (for example the deduction calculation for room rent).",
        "- When a fact is missing, the matching document or explanation is requested:",
        "",
        "| Missing fact | Ask |",
        "| --- | --- |",
    ]
    lines += [f"| `{k}` | {v} |" for k, v in MISSING_FACT_ASKS.items()]
    lines += [f"", f"At most {MAX_ASKS} items are listed; the required items above come first so they are never cut.", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    print(render_rules_md(), end="")
