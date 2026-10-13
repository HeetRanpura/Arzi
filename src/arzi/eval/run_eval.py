"""Run a model over an eval set through Tinker sampling and write metrics.

    python -m arzi.eval.run_eval --model base --set pilot
    python -m arzi.eval.run_eval --model ft   --set synth

Same prompt, renderer, parser and temperature 0 for every model. Only synthetic
sets are sent to Tinker; real letters are evaluated with the local model.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from rich.console import Console

from arzi.eval.metrics import Record, compute_metrics
from arzi.prompts import MAX_OUTPUT_TOKENS
from arzi.schema import ParseError, parse_model_output
from arzi.tinker_client import BASE_MODEL, JUDGE_RENDERER

SETS = {"synth": Path("data/generated/eval_synth.jsonl"), "pilot": Path("data/generated/pilot.jsonl")}
RESULTS_DIR = Path("eval/results")
RUNS_FILE = Path("train/runs.json")
console = Console()


def load_rows(path: Path, limit: int | None = None) -> list[dict]:
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    return rows[:limit] if limit else rows


def score(rows: list[dict], outputs: list[str]) -> dict:
    """Parse raw outputs and compute metrics. Pure, so it is testable without Tinker."""
    records, cases = [], []
    for row, raw in zip(rows, outputs):
        gold = parse_model_output(row["messages"][-1]["content"])
        try:
            pred, error = parse_model_output(raw), None
        except ParseError as e:
            pred, error = None, str(e)[:300]
        records.append(Record(gold, pred))
        cases.append(
            {
                "case_id": row["meta"]["case_id"],
                "scenario": row["meta"].get("scenario"),
                "gold_category": gold.category.value,
                "pred_category": pred.category.value if pred else None,
                "gold_verdict": gold.verdict.value,
                "pred_verdict": pred.verdict.value if pred else None,
                "parse_error": error,
                "raw": raw,
            }
        )
    return {"metrics": compute_metrics(records), "cases": cases}


def make_model(service, which: str):
    from arzi.tinker_client import make_completer, pick_teacher

    if which == "teacher":  # large model reference, not the baseline
        name = pick_teacher(service)
        return name, make_completer(service, name, temperature=0.0, max_tokens=MAX_OUTPUT_TOKENS + 2500)
    path = None
    if which == "ft":
        if not RUNS_FILE.exists():
            raise SystemExit(f"{RUNS_FILE} not found: train first (python -m arzi.train.sft)")
        path = json.loads(RUNS_FILE.read_text())[-1]["sampler_path"]
    completer = make_completer(service, BASE_MODEL, model_path=path, renderer_name=JUDGE_RENDERER, temperature=0.0, max_tokens=MAX_OUTPUT_TOKENS)
    return path or BASE_MODEL, completer


async def sample_all(rows: list[dict], completer, concurrency: int) -> list[str]:
    gate = asyncio.Semaphore(concurrency)

    async def one(row: dict) -> str:
        async with gate:
            return await completer(row["messages"][:-1])

    return await asyncio.gather(*(one(r) for r in rows))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--model", choices=["base", "ft", "teacher"], required=True)
    parser.add_argument("--set", choices=[*SETS, "real"], default="synth", dest="set_name")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--concurrency", type=int, default=16)
    parser.add_argument("--rescore", action="store_true", help="recompute metrics from the saved raw outputs, no sampling")
    args = parser.parse_args()
    out = RESULTS_DIR / f"{args.model}_{args.set_name}.json"

    if args.set_name == "real":
        raise SystemExit("Real letters are never sent to Tinker. Evaluate them with the local model (built in M5).")

    rows = load_rows(SETS[args.set_name], args.limit)
    if args.rescore:
        result = json.loads(out.read_text())
        raw = {c["case_id"]: c["raw"] for c in result["cases"]}
        result.update(score(rows, [raw[r["meta"]["case_id"]] for r in rows]))
        out.write_text(json.dumps(result, ensure_ascii=False, indent=1))
        console.print(f"rescored {out}")
        return

    from arzi.tinker_client import service_client

    prompt_tokens = sum(len(m["content"]) for r in rows for m in r["messages"][:-1]) // 4
    console.print(f"{len(rows)} cases, ~{prompt_tokens:,} prompt tokens, up to {len(rows) * MAX_OUTPUT_TOKENS:,} output tokens")

    name, completer = make_model(service_client(), args.model)
    outputs = asyncio.run(sample_all(rows, completer, args.concurrency))
    result = {"model": args.model, "model_name": name, "set": args.set_name, "renderer": JUDGE_RENDERER, **score(rows, outputs)}

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1))
    console.print({k: v for k, v in result["metrics"].items() if k != "fact_accuracy_by_field"})
    console.print(f"wrote {out}")


if __name__ == "__main__":
    main()
