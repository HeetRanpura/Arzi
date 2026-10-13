"""facts -> labels (rules.py) -> teacher-written documents -> noise -> JSONL splits.

    python -m arzi.generate.build_dataset --split pilot     # 40 cases for the M2 go/no-go
    python -m arzi.generate.build_dataset --split all       # train, val, eval_synth

Case facts and labels are deterministic in --seed. Teacher output is cached in
data/generated/raw/ (gitignored), so reruns only pay for cases not yet written.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from rich.console import Console

from arzi.generate.facts import Case, sample_cases
from arzi.generate.letters import Documents, pick_style, teacher_messages, write_documents
from arzi.generate.noise import add_noise
from arzi.generate.reasons import reason_for
from arzi.prompts import build_messages, render_target
from arzi.rules import evaluate

OUT_DIR = Path("data/generated")
RAW_DIR = OUT_DIR / "raw"
SPLITS = {"pilot": 40, "train": 600, "val": 60, "eval_synth": 80}
HELD_OUT_STYLE_SPLITS = {"eval_synth"}
NOISE_SHARE = 0.30
TEACHER_MAX_TOKENS = 3000
console = Console()


def build_row(case: Case, docs: Documents, seed: int) -> dict:
    rng = random.Random(f"{seed}:{case.case_id}:row")
    result = evaluate(case.category, case.facts)
    noisy = rng.random() < NOISE_SHARE
    letter, policy = docs.letter, docs.policy
    if noisy:
        letter, policy = add_noise(letter, rng), add_noise(policy, rng)
    target = render_target(case.category, result.verdict, case.facts, reason_for(result, case.facts, rng), list(result.ask_insurer_for))
    return {
        "messages": [*build_messages(letter, policy), {"role": "assistant", "content": target}],
        "meta": {
            "case_id": case.case_id,
            "category": case.category.value,
            "verdict": result.verdict.value,
            "scenario": case.scenario,
            "reason_codes": list(result.reason_codes),
            "moratorium_edge": case.is_moratorium_edge,
            "style": docs.style,
            "noisy": noisy,
        },
    }


async def build_split(split: str, n: int, seed: int, teacher, concurrency: int) -> list[dict]:
    cases = sample_cases(n, seed, split)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    gate = asyncio.Semaphore(concurrency)

    async def one(case: Case) -> dict | None:
        cache = RAW_DIR / f"{seed}-{case.case_id}.json"
        if cache.exists():
            docs = Documents(**json.loads(cache.read_text()))
        else:
            style = pick_style(random.Random(f"{seed}:{case.case_id}:style"), split in HELD_OUT_STYLE_SPLITS)
            async with gate:
                docs = await write_documents(case, style, teacher)
            if docs is None:
                return None
            cache.write_text(json.dumps(asdict(docs), ensure_ascii=False, indent=1))
        return build_row(case, docs, seed)

    rows = await asyncio.gather(*(one(c) for c in cases))
    kept = [r for r in rows if r]
    console.print(f"[bold]{split}[/bold]: kept {len(kept)}/{n} (dropped {n - len(kept)} after failed validation)")
    for key in ("category", "verdict"):
        console.print(f"  {key}: {dict(Counter(r['meta'][key] for r in kept).most_common())}")
    console.print(f"  noisy: {sum(r['meta']['noisy'] for r in kept)}, moratorium edge: {sum(r['meta']['moratorium_edge'] for r in kept)}")
    return kept


def estimate_teacher_tokens(splits: dict[str, int], seed: int) -> int:
    """Rough upper bound (chars / 4 in, full budget out) for cases not already cached."""
    total = 0
    for split, n in splits.items():
        for case in sample_cases(n, seed, split):
            if not (RAW_DIR / f"{seed}-{case.case_id}.json").exists():
                total += len(teacher_messages(case, "x" * 120)[0]["content"]) // 4 + TEACHER_MAX_TOKENS
    return total


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--split", choices=[*SPLITS, "all"], default="all")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--n", type=int, help="override the split size (single split only)")
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--dry-run", action="store_true", help="print the token estimate and stop")
    args = parser.parse_args()

    splits = {k: v for k, v in SPLITS.items() if k != "pilot"} if args.split == "all" else {args.split: args.n or SPLITS[args.split]}
    console.print(f"Teacher token estimate for uncached cases (upper bound): ~{estimate_teacher_tokens(splits, args.seed):,}")
    if args.dry_run:
        return

    from arzi.tinker_client import make_completer, pick_teacher, service_client

    service = service_client()
    teacher_name = pick_teacher(service)
    console.print(f"Teacher: {teacher_name}")
    teacher = make_completer(service, teacher_name, temperature=0.8, max_tokens=TEACHER_MAX_TOKENS)

    async def run() -> None:
        for split, n in splits.items():
            rows = await build_split(split, n, args.seed, teacher, args.concurrency)
            path = OUT_DIR / f"{split}.jsonl"
            path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
            console.print(f"  wrote {path}")

    asyncio.run(run())


if __name__ == "__main__":
    main()
