"""Turn eval/results/<model>_<set>.json into a markdown comparison table.

    python -m arzi.eval.report --set synth    # writes eval/results/summary.md
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from rich.console import Console

RESULTS_DIR = Path("eval/results")
LABELS = {"base": "Base Qwen3.5-4B", "ft": "Fine-tuned", "teacher": "Large model reference"}
# (metric key, label, True if higher is better)
ROWS = [
    ("valid_json_rate", "Valid JSON rate", True),
    ("category_accuracy", "Category accuracy", True),
    ("verdict_accuracy", "Verdict accuracy", True),
    ("contestable_recall", "Contestable recall", True),
    ("false_hope_rate", "**False hope rate** (lower is better)", False),
    ("moratorium_edge_accuracy", "Moratorium edge accuracy", True),
    ("fact_accuracy", "Fact accuracy", True),
]
console = Console()


def pct(x: float | None) -> str:
    return "n/a" if x is None else f"{100 * x:.1f}%"


def render_summary(results: dict[str, dict], set_name: str) -> str:
    models = [m for m in LABELS if m in results]
    first = results[models[0]]["metrics"]
    lines = [
        f"# Eval summary: `{set_name}`",
        "",
        f"{first['n']} cases ({first['n_contestable']} labelled contestable, {first['n_valid']} labelled valid, "
        f"{first['n_moratorium_edge']} moratorium edge). Same prompt, renderer, parser and temperature 0 for every model.",
        "",
        "| Metric | " + " | ".join(LABELS[m] for m in models) + " |",
        "| --- |" + " ---: |" * len(models),
    ]
    for key, label, _ in ROWS:
        lines.append(f"| {label} | " + " | ".join(pct(results[m]["metrics"][key]) for m in models) + " |")
    return "\n".join(lines) + "\n"


def disagreements(base: dict, ft: dict, k: int = 5) -> list[dict]:
    by_id = {c["case_id"]: c for c in ft["cases"]}
    out = []
    for b in base["cases"]:
        f = by_id.get(b["case_id"])
        if f and b["pred_verdict"] != f["pred_verdict"]:
            out.append({"case_id": b["case_id"], "scenario": b["scenario"], "gold": b["gold_verdict"], "base": b["pred_verdict"], "ft": f["pred_verdict"]})
    return out[:k]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--set", default="synth", dest="set_name")
    args = parser.parse_args()

    results = {}
    for model in LABELS:
        path = RESULTS_DIR / f"{model}_{args.set_name}.json"
        if path.exists():
            results[model] = json.loads(path.read_text())
    if not results:
        raise SystemExit(f"no results for set {args.set_name!r} in {RESULTS_DIR}; run arzi.eval.run_eval first")

    summary = render_summary(results, args.set_name)
    out = RESULTS_DIR / ("summary.md" if args.set_name == "synth" else f"summary_{args.set_name}.md")
    out.write_text(summary)
    console.print(summary)
    console.print(f"wrote {out}")
    if "base" in results and "ft" in results:
        console.print("Cases where base and fine-tuned disagree:")
        for d in disagreements(results["base"], results["ft"]):
            console.print(f"  {d['case_id']} ({d['scenario']}): gold={d['gold']} base={d['base']} ft={d['ft']}")


if __name__ == "__main__":
    main()
