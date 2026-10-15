"""Out-of-generator eval set: same sampled facts and rule labels, documents written by a
different model family with a free-form prompt.

    python -m arzi.generate.ood --dry-run
    python -m arzi.generate.ood            # -> data/ood/ood.jsonl

No style templates, letter skeletons or noise from the main generator are used. The
other model sees the facts only (the same fact list the main teacher gets, which also
carries the "do not state X" constraints that keep the rule labels true) and a one-line
request. The same fact-presence check decides whether a case is kept.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
from collections import Counter
from pathlib import Path

from rich.console import Console

from arzi.generate.build_dataset import TEACHER_MAX_TOKENS
from arzi.generate.facts import Case, sample_case
from arzi.schema import Category as K
from arzi.generate.letters import Documents, validate
from arzi.generate.reasons import reason_for
from arzi.prompts import build_messages, render_target
from arzi.rules import evaluate

OUT = Path("data/ood/ood.jsonl")
RAW_DIR = Path("data/generated/raw/ood")  # gitignored
SEED = 0
# Hand-picked plan: every category, five cases per verdict, and five non-disclosure cases
# in the 55-65 month band (one spare over the required four, in case one is dropped).
PLAN = [
    (K.NON_DISCLOSURE_PED, "moratorium", True),
    (K.NON_DISCLOSURE_PED, "disclosed", True),
    (K.NON_DISCLOSURE_PED, "valid", True),
    (K.NON_DISCLOSURE_PED, "valid", True),
    (K.NON_DISCLOSURE_PED, "unrelated", True),
    (K.WAITING_PERIOD, "served", False),
    (K.WAITING_PERIOD, "not_served", False),
    (K.WAITING_PERIOD, "accident_wording_unknown", False),
    (K.PERMANENT_EXCLUSION, "in_wording", False),
    (K.NO_HOSPITALISATION_NEEDED, "long_stay", False),
    (K.ROOM_RENT_PROPORTIONATE, "within_limit", False),
    (K.DOCUMENTS_OR_LATE_INTIMATION, "late_intimation", False),
    (K.POLICY_LAPSED, "lapsed", False),
    (K.SUM_INSURED_EXHAUSTED, "restore_unused", False),
    (K.OTHER, "investigation", False),
]
WRITERS = ["moonshotai/Kimi-K2.6", "Qwen/Qwen3.5-397B-A17B"]  # not the gpt-oss family that wrote the training data
# Kimi-K2.6 price was not checked; this assumes a deliberately high US$/M so the estimate is an upper bound
ASSUMED_PRICE_IN, ASSUMED_PRICE_OUT = 2.0, 8.0
MAX_ATTEMPTS = 4
console = Console()

PROMPT = """Write a realistic Indian health insurance claim rejection letter and policy schedule excerpt, based on these facts. All names are fictional.

Facts for the rejection letter:
{letter}

Facts for the policy schedule excerpt:
{policy}

Copy dates, amounts and numbers exactly as given. Put the letter first under the line ===LETTER=== and the excerpt under the line ===POLICY===, then end with ===END==="""


def ood_messages(case: Case) -> list[dict[str, str]]:
    bullet = lambda points: "\n".join(f"- {p}" for p in points)  # noqa: E731
    return [{"role": "user", "content": PROMPT.format(letter=bullet(case.letter_points), policy=bullet(case.policy_points))}]


def sample_ood_cases() -> list[Case]:
    return [
        sample_case(random.Random(f"{SEED}:ood:{i}"), f"ood-{i:04d}", category, scenario, edge)
        for i, (category, scenario, edge) in enumerate(PLAN)
    ]


async def write(case: Case, writer) -> Documents | None:
    import re

    split = re.compile(r"===LETTER===(.*?)===POLICY===(.*?)(?:===END===|$)", re.DOTALL)
    for attempt in range(1, MAX_ATTEMPTS + 1):
        match = split.search(await writer(ood_messages(case)))
        if match:
            letter, policy = match.group(1).strip(), match.group(2).strip()
            if not validate(case, letter, policy):
                return Documents(letter, policy, "free-form (out-of-generator)", attempt)
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    cases = sample_ood_cases()
    verdicts = Counter(evaluate(c.category, c.facts).verdict.value for c in cases)
    console.print(f"{len(cases)} cases: {dict(Counter(c.category.value for c in cases))}")
    console.print(f"verdicts {dict(verdicts)}, moratorium edge {sum(c.is_moratorium_edge for c in cases)}")
    tokens_in = sum(len(ood_messages(c)[0]["content"]) // 4 for c in cases) * MAX_ATTEMPTS
    tokens_out = len(cases) * TEACHER_MAX_TOKENS * MAX_ATTEMPTS
    cost = (tokens_in * ASSUMED_PRICE_IN + tokens_out * ASSUMED_PRICE_OUT) / 1e6
    console.print(f"Worst case (every case retried {MAX_ATTEMPTS}x at full budget): ~{tokens_in:,} in + {tokens_out:,} out, under US${cost:.2f} at an assumed US${ASSUMED_PRICE_IN}/{ASSUMED_PRICE_OUT} per M")
    if cost > 5:
        raise SystemExit("Estimate above US$5; not starting.")
    if args.dry_run:
        return

    from arzi.tinker_client import available_models, make_completer, service_client

    service = service_client()
    name = next(m for m in WRITERS if m in available_models(service))
    console.print(f"Writer: {name}")
    writer = make_completer(service, name, temperature=0.8, max_tokens=TEACHER_MAX_TOKENS)

    async def run() -> list[dict]:
        RAW_DIR.mkdir(parents=True, exist_ok=True)

        async def one(case: Case) -> dict | None:
            cache = RAW_DIR / f"{case.case_id}.json"
            if cache.exists():
                docs = Documents(**json.loads(cache.read_text()))
            else:
                docs = await write(case, writer)
                if docs is None:
                    return None
                cache.write_text(json.dumps(docs.__dict__, ensure_ascii=False, indent=1))
            result = evaluate(case.category, case.facts)
            rng = random.Random(f"{SEED}:{case.case_id}:row")
            target = render_target(case.category, result.verdict, case.facts, reason_for(result, case.facts, rng), list(result.ask_insurer_for))
            return {
                "messages": [*build_messages(docs.letter, docs.policy), {"role": "assistant", "content": target}],
                "meta": {
                    "case_id": case.case_id,
                    "category": case.category.value,
                    "verdict": result.verdict.value,
                    "scenario": case.scenario,
                    "reason_codes": list(result.reason_codes),
                    "moratorium_edge": case.is_moratorium_edge,
                    "style": docs.style,
                    "writer": name,
                    "noisy": False,
                },
            }

        return [r for r in await asyncio.gather(*(one(c) for c in cases)) if r]

    rows = asyncio.run(run())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    console.print(f"kept {len(rows)}/{len(cases)}; verdicts {dict(Counter(r['meta']['verdict'] for r in rows))}; edge {sum(r['meta']['moratorium_edge'] for r in rows)}")
    console.print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
