"""Metrics from SPEC section 8. A parse failure (pred is None) counts as wrong everywhere."""

from __future__ import annotations

from dataclasses import dataclass

from arzi.schema import CaseFacts, Category, ModelOutput, Verdict

# dates, ints and bools; free-text fields are not scored
FACT_FIELDS = [name for name in CaseFacts.model_fields if name not in ("condition_named_by_insurer", "exclusion_cited")]
MORATORIUM_EDGE = range(55, 66)


@dataclass
class Record:
    gold: ModelOutput
    pred: ModelOutput | None


def is_moratorium_edge(gold: ModelOutput) -> bool:
    return gold.category is Category.NON_DISCLOSURE_PED and gold.facts.months_continuous_coverage in MORATORIUM_EDGE


def _rate(hits: int, total: int) -> float | None:
    return hits / total if total else None


def compute_metrics(records: list[Record]) -> dict:
    n = len(records)
    verdict_ok = [r.pred is not None and r.pred.verdict is r.gold.verdict for r in records]
    contestable = [r for r in records if r.gold.verdict is Verdict.LIKELY_CONTESTABLE]
    valid = [r for r in records if r.gold.verdict is Verdict.LIKELY_VALID]
    edge = [ok for r, ok in zip(records, verdict_ok) if is_moratorium_edge(r.gold)]

    def predicted_contestable(rs: list[Record]) -> int:
        return sum(r.pred is not None and r.pred.verdict is Verdict.LIKELY_CONTESTABLE for r in rs)

    per_field: dict[str, list[int]] = {}
    for r in records:
        for name in FACT_FIELDS:
            gold_value = getattr(r.gold.facts, name)
            if gold_value is None:
                continue
            hit, total = per_field.setdefault(name, [0, 0])
            per_field[name] = [hit + (r.pred is not None and getattr(r.pred.facts, name) == gold_value), total + 1]
    fact_hits = sum(h for h, _ in per_field.values())
    fact_total = sum(t for _, t in per_field.values())

    return {
        "n": n,
        "valid_json_rate": _rate(sum(r.pred is not None for r in records), n),
        "category_accuracy": _rate(sum(r.pred is not None and r.pred.category is r.gold.category for r in records), n),
        "verdict_accuracy": _rate(sum(verdict_ok), n),
        "contestable_recall": _rate(predicted_contestable(contestable), len(contestable)),
        "false_hope_rate": _rate(predicted_contestable(valid), len(valid)),
        "moratorium_edge_accuracy": _rate(sum(edge), len(edge)),
        "fact_accuracy": _rate(fact_hits, fact_total),
        "n_contestable": len(contestable),
        "n_valid": len(valid),
        "n_moratorium_edge": len(edge),
        "fact_accuracy_by_field": {k: _rate(h, t) for k, (h, t) in per_field.items()},
    }
