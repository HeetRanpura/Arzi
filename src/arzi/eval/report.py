"""Turn eval/results/<model>_<set>.json into a markdown comparison table.

    python -m arzi.eval.report --set synth    # writes eval/results/summary.md
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from rich.console import Console

RESULTS_DIR = Path("eval/results")
# base_thinking results are kept on disk but left out of the table: the base model with thinking on
# finished only 7 of 117 answers within 12,700 tokens, so its rates are not comparable.
LABELS = {"base": "Base Qwen3.5-4B", "ft": "Fine-tuned", "teacher": "Large model reference"}
# (metric key, label, True if higher is better)
ROWS = [
    ("valid_json_rate", "Valid JSON rate", True),
    ("category_accuracy", "Category accuracy", True),
    ("verdict_accuracy", "Verdict accuracy", True),
    ("contestable_recall", "**Contestable recall** (catches fightable claims)", True),
    ("over_optimism_rate", "**Over-optimism rate** (not contestable, called contestable; lower is better)", False),
    ("false_hope_rate", "False hope rate (valid, called contestable; lower is better)", False),
    ("moratorium_edge_accuracy", "Moratorium edge accuracy", True),
    ("fact_accuracy", "Fact accuracy", True),
]
console = Console()


def pct(metrics: dict, key: str) -> str:
    hits, total = metrics["counts"][key]
    return f"{100 * hits / total:.1f}% ({hits}/{total})" if total else "n/a (0)"


VERDICTS = ["likely_contestable", "worth_asking", "likely_valid"]
# worse on either of these is flagged even if verdict accuracy improves
HEADLINE = [("contestable_recall", True), ("over_optimism_rate", False)]


def _frac(hits: int, total: int) -> str:
    return f"{100 * hits / total:.1f}% ({hits}/{total})" if total else "n/a (0)"


def confusion(cases: list[dict]) -> list[str]:
    lines = ["| gold \\ predicted | " + " | ".join(VERDICTS) + " | unparsed |", "| --- |" + " ---: |" * 4]
    for gold in VERDICTS:
        row = [c["pred_verdict"] for c in cases if c["gold_verdict"] == gold]
        lines.append(f"| **{gold}** | " + " | ".join(str(row.count(v)) for v in VERDICTS) + f" | {row.count(None)} |")
    return lines


def per_category(results: dict[str, dict], models: list[str]) -> list[str]:
    lines = ["| Category | " + " | ".join(LABELS[m] for m in models) + " |", "| --- |" + " ---: |" * len(models)]
    for category in sorted({c["gold_category"] for c in results[models[0]]["cases"]}):
        cells = []
        for m in models:
            rows = [c for c in results[m]["cases"] if c["gold_category"] == category]
            cells.append(_frac(sum(c["pred_verdict"] == c["gold_verdict"] for c in rows), len(rows)))
        lines.append(f"| {category} | " + " | ".join(cells) + " |")
    return lines


def disagreements(base: dict, ft: dict, k: int = 5) -> list[dict]:
    """Up to k cases where the two models give different verdicts, spread over categories."""
    by_id = {c["case_id"]: c for c in ft["cases"]}
    out, seen = [], set()
    for prefer_new_category in (True, False):
        for b in base["cases"]:
            f = by_id.get(b["case_id"])
            if not f or b["pred_verdict"] == f["pred_verdict"] or b["case_id"] in {d["case_id"] for d in out}:
                continue
            if prefer_new_category and b["gold_category"] in seen:
                continue
            seen.add(b["gold_category"])
            out.append({"case_id": b["case_id"], "category": b["gold_category"], "scenario": b["scenario"], "gold": b["gold_verdict"], "base": b["pred_verdict"], "ft": f["pred_verdict"]})
    return out[:k]


def regressions(results: dict[str, dict]) -> list[str]:
    """Plain warnings where the fine-tuned model is worse than base on a headline metric."""
    if "base" not in results or "ft" not in results:
        return []
    base, ft = results["base"]["metrics"], results["ft"]["metrics"]
    labels = {key: label for key, label, _ in ROWS}
    out = []
    for key, higher_is_better in HEADLINE:
        if base[key] is None or ft[key] is None:
            continue
        if (ft[key] < base[key]) if higher_is_better else (ft[key] > base[key]):
            out.append(f"**WARNING: fine-tuned is WORSE than base on {labels[key].replace('**', '')}: {pct(ft, key)} vs {pct(base, key)}.**")
    return out


SET_TITLES = {"synth": "Synthetic held-out styles", "ood": "Out-of-generator"}


def load_results(set_name: str, ft_name: str = "ft") -> dict[str, dict]:
    results = {}
    for model in LABELS:
        path = RESULTS_DIR / f"{ft_name if model == 'ft' else model}_{set_name}.json"
        if path.exists():
            results[model] = json.loads(path.read_text())
    return results


def cross_set_table(by_set: dict[str, dict[str, dict]]) -> list[str]:
    """Base and fine-tuned on each eval set, side by side."""
    sets = [s for s in SET_TITLES if "base" in by_set.get(s, {}) and "ft" in by_set.get(s, {})]
    if len(sets) < 2:
        return []
    header = " | ".join(f"{SET_TITLES[s]}: {LABELS[m]}" for s in sets for m in ("base", "ft"))
    lines = [
        "## Synthetic held-out styles vs out-of-generator",
        "",
        "Synthetic held-out styles: written by the training teacher (gpt-oss-120b) in four letter styles never used in training. "
        "Out-of-generator: same rule-derived facts and labels, documents written by a different model family (Kimi-K2.6) "
        "from a free-form prompt with no templates or noise.",
        "",
        f"| Metric | {header} |",
        "| --- |" + " ---: |" * (2 * len(sets)),
    ]
    for key, label, _ in ROWS:
        lines.append(f"| {label} | " + " | ".join(pct(by_set[s][m]["metrics"], key) for s in sets for m in ("base", "ft")) + " |")
    return lines


def render_summary(results: dict[str, dict], set_name: str) -> str:
    models = [m for m in LABELS if m in results]
    first = results[models[0]]["metrics"]
    lines = [
        f"# Eval summary: `{set_name}`",
        "",
        f"{first['n']} cases ({first['n_contestable']} labelled contestable, {first['n_valid']} labelled valid, "
        f"{first['n_moratorium_edge']} moratorium edge). Same prompt, renderer, parser and temperature 0 for every model.",
        "",
        *[w + "\n" for w in regressions(results)],
        "| Metric | " + " | ".join(LABELS[m] for m in models) + " |",
        "| --- |" + " ---: |" * len(models),
    ]
    for key, label, _ in ROWS:
        lines.append(f"| {label} | " + " | ".join(pct(results[m]["metrics"], key) for m in models) + " |")
    months = [_frac(*results[m]["metrics"]["fact_counts_by_field"].get("months_continuous_coverage", [0, 0])) for m in models]
    lines.append("| Months-of-cover fact accuracy | " + " | ".join(months) + " |")
    for m in models:
        lines += ["", f"## Verdict confusion matrix: {LABELS[m]}", "", *confusion(results[m]["cases"])]
    lines += ["", "## Verdict accuracy by category", "", *per_category(results, models)]
    if "base" in results and "ft" in results:
        lines += ["", "## Cases where base and fine-tuned disagree", "", "| Case | Category / scenario | Gold | Base | Fine-tuned |", "| --- | --- | --- | --- | --- |"]
        lines += [f"| {d['case_id']} | {d['category']} / {d['scenario']} | {d['gold']} | {d['base']} | {d['ft']} |" for d in disagreements(results["base"], results["ft"])]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--set", default="synth", dest="set_name")
    parser.add_argument("--ft-name", default="ft", help="result file prefix to use as the fine-tuned model (e.g. ft_best)")
    parser.add_argument("--out", help="output file name inside eval/results/")
    args = parser.parse_args()

    results = load_results(args.set_name, args.ft_name)
    if not results:
        raise SystemExit(f"no results for set {args.set_name!r} in {RESULTS_DIR}; run arzi.eval.run_eval first")

    summary = render_summary(results, args.set_name)
    if args.set_name == "synth":
        extra = cross_set_table({s: load_results(s, args.ft_name) for s in SET_TITLES})
        if extra:
            summary += "\n" + "\n".join(extra) + "\n"
    out = RESULTS_DIR / (args.out or ("summary.md" if args.set_name == "synth" else f"summary_{args.set_name}.md"))
    out.write_text(summary)
    console.print(summary)
    console.print(f"wrote {out}")
    for warning in regressions(results):
        console.print(f"[bold red]{warning}[/bold red]")

if __name__ == "__main__":
    main()
