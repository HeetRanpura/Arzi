import json
import sys

from arzi.eval import label_real
from arzi.schema import CaseFacts


def test_label_real_writes_case_and_never_prints_text(tmp_path, monkeypatch, capsys):
    letter, policy = tmp_path / "letter.txt", tmp_path / "policy.txt"
    letter.write_text("SECRET-LETTER-TEXT fictional rejection")
    policy.write_text("SECRET-POLICY-TEXT fictional schedule")
    answers = {"policy_inception_date": "2019-06-01", "admission_date": "2025-06-01", "ped_disclosed_in_proposal": "n", "condition_related_to_claim": "y"}
    script = ["1"] + [answers.get(name, "") for name in CaseFacts.model_fields] + ["1", "moratorium applies"]
    feed = iter(script)
    monkeypatch.setattr("builtins.input", lambda prompt="": next(feed))
    monkeypatch.setattr(label_real, "REAL_DIR", tmp_path / "real")
    monkeypatch.setattr(sys, "argv", ["label_real", "--letter", str(letter), "--policy", str(policy)])
    label_real.main()

    printed = capsys.readouterr().out
    assert "SECRET" not in printed
    assert "likely_contestable" in printed  # rules engine hint
    saved = json.loads((tmp_path / "real" / "real-001.json").read_text())
    assert saved["letter"].startswith("SECRET-LETTER-TEXT")
    assert saved["label"]["category"] == "non_disclosure_ped" and saved["label"]["verdict"] == "likely_contestable"
    assert saved["label"]["facts"]["months_continuous_coverage"] == 72
