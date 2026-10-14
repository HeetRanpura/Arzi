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

SETS = {
    "synth": Path("data/generated/eval_synth.jsonl"),
    "pilot": Path("data/generated/pilot.jsonl"),
    "ood": Path("data/ood/ood.jsonl"),  # out-of-generator: different writer model, free-form prompt
}
REAL_DIR = Path("data/real")  # gitignored; only ever evaluated with the local model
RESULTS_DIR = Path("eval/results")
RUNS_FILE = Path("train/runs.json")
console = Console()


def load_rows(path: Path, limit: int | None = None) -> list[dict]:
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    return rows[:limit] if limit else rows


def load_real_rows() -> list[dict]:
    """data/real/*.json, each {"case_id", "letter", "policy", "label": ModelOutput JSON}, as eval rows.

    Written by `python -m arzi.eval.label_real`. Contents are never printed.
    """
    from arzi.prompts import build_messages, render_target
    from arzi.schema import ModelOutput

    rows = []
    for path in sorted(REAL_DIR.glob("*.json")):
        item = json.loads(path.read_text())
        label = ModelOutput.model_validate(item["label"])
        target = render_target(label.category, label.verdict, label.facts, label.reason, label.ask_insurer_for)
        rows.append(
            {
                "messages": [*build_messages(item["letter"], item["policy"]), {"role": "assistant", "content": target}],
                "meta": {"case_id": item.get("case_id", path.stem), "scenario": "real"},
            }
        )
    return rows


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


def make_model(service, which: str, sampler_path: str | None = None, thinking: bool = False):
    from arzi.tinker_client import make_completer, pick_teacher

    if which == "teacher":  # large model reference, not the baseline
        name = pick_teacher(service)
        return name, make_completer(service, name, temperature=0.0, max_tokens=MAX_OUTPUT_TOKENS + 2500)
    path = sampler_path
    if which == "ft" and path is None:
        if not RUNS_FILE.exists():
            raise SystemExit(f"{RUNS_FILE} not found: train first (python -m arzi.train.sft)")
        path = json.loads(RUNS_FILE.read_text())[-1]["sampler_path"]
    # thinking=True is a reference run only: the shipped model and the headline baseline both answer without thinking
    renderer, budget = ("qwen3_5", MAX_OUTPUT_TOKENS + 12000) if thinking else (JUDGE_RENDERER, MAX_OUTPUT_TOKENS)
    completer = make_completer(service, BASE_MODEL, model_path=path, renderer_name=renderer, temperature=0.0, max_tokens=budget)
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
    parser.add_argument("--local", action="store_true", help="run the exported model on this machine instead of Tinker (always used for --set real)")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--concurrency", type=int, default=16)
    parser.add_argument("--sampler-path", help="evaluate this tinker:// checkpoint instead of the latest run (with --model ft)")
    parser.add_argument("--thinking", action="store_true", help="reference run with the thinking renderer and a larger token budget")
    parser.add_argument("--out-name", help="result file prefix, default: the --model value")
    parser.add_argument("--rescore", action="store_true", help="recompute metrics from the saved raw outputs, no sampling")
    args = parser.parse_args()
    out = RESULTS_DIR / f"{args.out_name or args.model}_{args.set_name}.json"

    if args.set_name == "real":
        if args.model != "ft" and args.model != "base":
            raise SystemExit("--set real supports --model base or ft only")
        args.local = True  # real letters never leave this machine
        rows = load_real_rows()[: args.limit] if args.limit else load_real_rows()
    else:
        rows = load_rows(SETS[args.set_name], args.limit)
    if args.rescore:
        result = json.loads(out.read_text())
        raw = {c["case_id"]: c["raw"] for c in result["cases"]}
        result.update(score(rows, [raw[r["meta"]["case_id"]] for r in rows]))
        out.write_text(json.dumps(result, ensure_ascii=False, indent=1))
        console.print(f"rescored {out}")
        return

    if args.local:
        from arzi.app.local_model import LocalModel

        model = LocalModel.load(fine_tuned=args.model == "ft")
        console.print(f"{len(rows)} cases, local model {model.name}")
        outputs = [model.generate(r["messages"][:-1]) for r in rows]
        result = {"model": args.out_name or args.model, "model_name": model.name, "set": args.set_name, "renderer": JUDGE_RENDERER, "backend": "local", **score(rows, outputs)}
        if args.set_name == "real":
            for case in result["cases"]:  # keep only labels and verdicts; no letter text or raw output on disk
                case.pop("raw", None)
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, ensure_ascii=False, indent=1))
        console.print({k: result["metrics"][k] for k in ("verdict_accuracy", "contestable_recall", "over_optimism_rate", "false_hope_rate")})
        console.print(f"wrote {out}")
        return

    from arzi.tinker_client import service_client

    prompt_tokens = sum(len(m["content"]) for r in rows for m in r["messages"][:-1]) // 4
    console.print(f"{len(rows)} cases, ~{prompt_tokens:,} prompt tokens, up to {len(rows) * MAX_OUTPUT_TOKENS:,} output tokens")

    name, completer = make_model(service_client(), args.model, args.sampler_path, args.thinking)
    outputs = asyncio.run(sample_all(rows, completer, args.concurrency))
    result = {"model": args.out_name or args.model, "model_name": name, "set": args.set_name, "renderer": "qwen3_5" if args.thinking else JUDGE_RENDERER, **score(rows, outputs)}

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1))
    console.print({k: v for k, v in result["metrics"].items() if k != "fact_accuracy_by_field"})
    console.print(f"wrote {out}")


if __name__ == "__main__":
    main()
