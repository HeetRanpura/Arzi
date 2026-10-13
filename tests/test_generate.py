import asyncio
import json
import random
from collections import Counter

from arzi.eval.run_eval import score
from arzi.generate.build_dataset import build_row
from arzi.generate.facts import CATEGORY_MIX, SCENARIOS, allocate, format_inr, sample_cases
from arzi.generate.letters import EVAL_STYLES, TRAIN_STYLES, Documents, teacher_messages, validate, write_documents
from arzi.generate.noise import add_noise
from arzi.prompts import SYSTEM_PROMPT
from arzi.rules import ASK_CLAUSE, evaluate
from arzi.schema import Category, Verdict, parse_model_output

CASES = sample_cases(740, 0, "t")


def test_sampling_is_deterministic():
    again = sample_cases(740, 0, "t")
    assert [c.facts for c in again] == [c.facts for c in CASES]
    assert [c.facts for c in sample_cases(40, 1, "t")] != [c.facts for c in sample_cases(40, 0, "t")]


def test_category_mix_and_all_scenarios_present():
    counts = Counter(c.category for c in CASES)
    for category, share in CATEGORY_MIX.items():
        assert abs(counts[category] / len(CASES) - share) < 0.01
    seen = {(c.category, c.scenario) for c in CASES}
    assert seen == {(cat, name) for cat, scenarios in SCENARIOS.items() for name, _, _ in scenarios}
    assert {c.category for c in sample_cases(40, 0, "pilot")} == set(Category)


def test_verdict_balance_and_moratorium_edges():
    verdicts = Counter(evaluate(c.category, c.facts).verdict for c in CASES)
    assert verdicts[Verdict.LIKELY_VALID] / len(CASES) >= 0.30
    assert min(verdicts.values()) / len(CASES) >= 0.25
    ped = [c for c in CASES if c.category is Category.NON_DISCLOSURE_PED]
    assert sum(c.is_moratorium_edge for c in ped) / len(ped) >= 0.15


def test_facts_are_consistent():
    for c in CASES:
        f = c.facts
        assert 2019 <= f.policy_inception_date.year and f.admission_date.year <= 2026
        assert f.policy_inception_date < f.admission_date
        assert f.crc_approval_mentioned is not None and f.is_accident is not None
        if f.is_accident and f.waiting_period_months and f.waiting_period_months > 1:
            assert c.scenario.startswith("accident")  # accident_exempt_in_wording is sampled for these
        if c.scenario in ("accident_exempt", "accident_not_exempt"):
            assert f.accident_exempt_in_wording is not None


def test_brief_never_states_the_verdict():
    for c in CASES[:200]:
        text = teacher_messages(c, TRAIN_STYLES[0])[0]["content"].lower()
        assert "contestable" not in text and "likely valid" not in text and "worth asking" not in text


def test_eval_styles_are_held_out():
    assert not set(TRAIN_STYLES) & set(EVAL_STYLES)


def test_allocate_and_inr():
    assert sum(allocate(40, list(CATEGORY_MIX.values()), random.Random(0))) == 40
    assert min(allocate(40, list(CATEGORY_MIX.values()), random.Random(0))) >= 2
    assert [format_inr(n) for n in (500, 5000, 150000, 1000000)] == ["500", "5,000", "1,50,000", "10,00,000"]


def _fake_docs(case):
    """Documents that state every required string, as a well-behaved teacher would."""
    filler = "Further to your claim we have examined the papers submitted by the hospital and the insured. " * 3
    return f"{filler}\n" + "\n".join(case.letter_must), f"{filler}\n" + "\n".join(case.policy_must)


def test_validate_catches_missing_and_forbidden_facts():
    case = next(c for c in CASES if c.scenario == "not_in_wording")
    letter, policy = _fake_docs(case)
    assert validate(case, letter, policy) == []
    assert validate(case, letter.replace(case.letter_must[0], ""), policy)
    assert validate(case, letter, policy + " " + case.policy_must_not[0])
    assert validate(case, letter + " This rejection is contestable.", policy)


def test_write_documents_retries_then_gives_up():
    case = CASES[0]
    letter, policy = _fake_docs(case)
    replies = iter(["garbage", f"===LETTER===\n{letter}\n===POLICY===\n{policy}\n===END==="])

    async def teacher(_messages):
        return next(replies)

    docs = asyncio.run(write_documents(case, "style", teacher))
    assert docs.attempts == 2 and docs.letter == letter.strip()

    async def bad_teacher(_messages):
        return "===LETTER===\nshort\n===POLICY===\nshort\n===END==="

    assert asyncio.run(write_documents(case, "style", bad_teacher)) is None


def test_row_format_and_gold_round_trip():
    rows = []
    for case in CASES[:120]:
        row = build_row(case, Documents(*_fake_docs(case), style="s", attempts=1), seed=0)
        roles = [m["role"] for m in row["messages"]]
        assert roles == ["system", "user", "assistant"]
        assert row["messages"][0]["content"] == SYSTEM_PROMPT
        target = json.loads(row["messages"][2]["content"])
        assert list(target) == ["category", "facts", "verdict", "reason", "ask_insurer_for"]
        gold = parse_model_output(row["messages"][2]["content"])
        assert gold.facts == case.facts
        assert gold.verdict.value == row["meta"]["verdict"] == evaluate(case.category, case.facts).verdict.value
        assert gold.ask_insurer_for[0] == ASK_CLAUSE and len(gold.reason) <= 600 and "{" not in gold.reason
        rows.append(row)
    assert 0.15 < sum(r["meta"]["noisy"] for r in rows) / len(rows) < 0.45

    # a model that echoes the target scores 100%; garbage scores 0 and is not false hope
    perfect = score(rows, [r["messages"][2]["content"] for r in rows])["metrics"]
    assert perfect["verdict_accuracy"] == perfect["fact_accuracy"] == 1.0 and perfect["false_hope_rate"] == 0.0
    broken = score(rows, ["no json here"] * len(rows))["metrics"]
    assert broken["valid_json_rate"] == 0.0 and broken["verdict_accuracy"] == 0.0 and broken["false_hope_rate"] == 0.0


def test_noise_changes_text_but_keeps_most_of_it():
    text = "Dear Sir,\nWe regret to inform you that claim 100200 dated 05/10/2024 for Rs. 1,50,000 is repudiated under clause 4.1 of the policy.\n" * 6
    noisy = add_noise(text, random.Random(1))
    assert noisy != text
    assert add_noise(text, random.Random(1)) == noisy
    assert 0.8 < len(noisy) / len(text) < 1.4
