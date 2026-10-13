from datetime import date

import pytest

from arzi.eval.metrics import Record, compute_metrics
from arzi.schema import CaseFacts, Category, ModelOutput, Verdict

C, W, V = Verdict.LIKELY_CONTESTABLE, Verdict.WORTH_ASKING, Verdict.LIKELY_VALID
PED, WP = Category.NON_DISCLOSURE_PED, Category.WAITING_PERIOD


def out(category, verdict, **facts):
    return ModelOutput(category=category, verdict=verdict, facts=CaseFacts(**facts), reason="r")


def test_perfect_predictions():
    gold = [out(PED, C, months_continuous_coverage=61), out(PED, V, months_continuous_coverage=10), out(WP, W, is_accident=True)]
    m = compute_metrics([Record(g, g) for g in gold])
    assert m["valid_json_rate"] == m["category_accuracy"] == m["verdict_accuracy"] == m["contestable_recall"] == m["fact_accuracy"] == 1.0
    assert m["false_hope_rate"] == 0.0
    assert m["moratorium_edge_accuracy"] == 1.0 and m["n_moratorium_edge"] == 1


def test_false_hope_and_recall():
    records = [
        Record(out(PED, V), out(PED, C)),  # false hope
        Record(out(PED, V), out(PED, V)),
        Record(out(PED, V), out(PED, W)),
        Record(out(PED, V), None),  # parse failure is wrong, but it is not false hope
        Record(out(WP, C), out(WP, C)),
        Record(out(WP, C), out(WP, V)),
        Record(out(WP, C), None),  # counts against recall
        Record(out(WP, W), out(PED, W)),  # right verdict, wrong category
    ]
    m = compute_metrics(records)
    assert m["n"] == 8 and m["n_valid"] == 4 and m["n_contestable"] == 3
    assert m["false_hope_rate"] == 1 / 4
    assert m["over_optimism_rate"] == 1 / 5  # 4 valid + 1 worth asking, one called contestable
    assert m["counts"]["over_optimism_rate"] == [1, 5] and m["counts"]["contestable_recall"] == [1, 3]
    assert m["contestable_recall"] == 1 / 3
    assert m["valid_json_rate"] == 6 / 8
    assert m["verdict_accuracy"] == 3 / 8
    assert m["category_accuracy"] == 5 / 8


def test_moratorium_edge_only_counts_ped_55_to_65():
    records = [
        Record(out(PED, V, months_continuous_coverage=55), out(PED, V)),
        Record(out(PED, V, months_continuous_coverage=59), out(PED, C)),
        Record(out(PED, C, months_continuous_coverage=65), out(PED, C)),
        Record(out(PED, C, months_continuous_coverage=60), None),
        Record(out(PED, C, months_continuous_coverage=66), out(PED, V)),  # outside the band
        Record(out(PED, V, months_continuous_coverage=54), out(PED, C)),  # outside the band
        Record(out(WP, C, months_continuous_coverage=60), out(WP, V)),  # other category
    ]
    m = compute_metrics(records)
    assert m["n_moratorium_edge"] == 4
    assert m["moratorium_edge_accuracy"] == 2 / 4


def test_fact_accuracy_scores_only_non_null_gold_fields():
    gold = out(WP, V, admission_date=date(2024, 3, 5), waiting_period_months=24, is_accident=False, condition_named_by_insurer="cataract")
    pred = out(WP, V, admission_date=date(2024, 3, 5), waiting_period_months=36, is_accident=None, hospital_stay_hours=99, condition_named_by_insurer="x")
    m = compute_metrics([Record(gold, pred)])
    assert m["fact_accuracy"] == pytest.approx(1 / 3)  # the extra hours and the free-text field are ignored
    assert m["fact_accuracy_by_field"] == {"admission_date": 1.0, "waiting_period_months": 0.0, "is_accident": 0.0}
    assert compute_metrics([Record(gold, None)])["fact_accuracy"] == 0.0


def test_empty_denominators_are_none():
    m = compute_metrics([Record(out(WP, W), out(WP, W))])
    assert m["contestable_recall"] is None and m["false_hope_rate"] is None
    assert m["moratorium_edge_accuracy"] is None and m["fact_accuracy"] is None
    assert compute_metrics([])["verdict_accuracy"] is None


def test_report_flags_headline_regressions_and_shows_counts():
    from arzi.eval.report import regressions, render_summary

    def result(preds):
        golds = [out(PED, C, months_continuous_coverage=61), out(PED, V, months_continuous_coverage=12), out(WP, W), out(WP, C)]
        records = [Record(g, p) for g, p in zip(golds, preds)]
        cases = [
            {"case_id": f"c{i}", "scenario": "s", "gold_category": r.gold.category.value, "gold_verdict": r.gold.verdict.value, "pred_verdict": r.pred.verdict.value if r.pred else None}
            for i, r in enumerate(records)
        ]
        return {"metrics": compute_metrics(records), "cases": cases}

    base = result([out(PED, C, months_continuous_coverage=61), out(PED, V), out(WP, W), out(WP, C)])
    worse = result([out(PED, V), out(PED, C), out(WP, W), None])  # lower recall and over-promises
    assert regressions({"base": base, "ft": base}) == []
    flags = regressions({"base": base, "ft": worse})
    assert len(flags) == 2 and all("WORSE" in f for f in flags)

    text = render_summary({"base": base, "ft": worse}, "synth")
    assert "WARNING" in text and "100.0% (2/2)" in text and "50.0% (1/2)" in text
    assert "Months-of-cover fact accuracy | 50.0% (1/2) | 0.0% (0/2)" in text
    assert "| **likely_contestable** | 2 | 0 | 0 | 0 |" in text and "| **likely_contestable** | 0 | 0 | 1 | 1 |" in text
    assert "| c0 | non_disclosure_ped / s | likely_contestable | likely_contestable | likely_valid |" in text
