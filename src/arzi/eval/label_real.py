"""Hand-label one anonymised real letter for the real-letter eval.

    python -m arzi.eval.label_real --letter path/to/letter.txt --policy path/to/policy.txt

Asks for the category, each fact and the verdict, and writes data/real/<case_id>.json in
the format `run_eval --set real` reads. The letter and policy text are read from the
files and stored in the JSON, but never printed to the terminal or logs: only their
file names and character counts are shown. Open the files yourself to answer.

Anonymise the documents before running this. data/real/ is gitignored.
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from arzi.rules import evaluate
from arzi.schema import CaseFacts, Category, ModelOutput, Verdict

REAL_DIR = Path("data/real")


def read_text(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        from pypdf import PdfReader

        return "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
    return path.read_text()


def ask(prompt: str, parse, allow_blank: bool = True):
    while True:
        raw = input(prompt).strip()
        if not raw and allow_blank:
            return None
        try:
            return parse(raw)
        except ValueError as e:
            print(f"  not understood ({e}); try again")


def parse_bool(raw: str) -> bool:
    if raw.lower() in ("y", "yes", "true", "t", "1"):
        return True
    if raw.lower() in ("n", "no", "false", "f", "0"):
        return False
    raise ValueError("answer y or n, or leave blank for unknown")


def parse_choice(options: list[str]):
    def parse(raw: str) -> str:
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1]
        if raw in options:
            return raw
        raise ValueError(f"pick 1 to {len(options)}")

    return parse


PARSERS = {date: date.fromisoformat, int: int, bool: parse_bool, str: str}


def ask_facts() -> CaseFacts:
    print("\nFacts. Leave blank when the documents do not state or show it. Dates are YYYY-MM-DD.")
    values = {}
    for name, field in CaseFacts.model_fields.items():
        kind = next(t for t in (date, bool, int, str) if t in getattr(field.annotation, "__args__", (field.annotation,)))
        hint = {date: "YYYY-MM-DD", bool: "y/n", int: "number", str: "text"}[kind]
        if name == "months_continuous_coverage":
            print("  months_continuous_coverage: leave blank to compute it from the two dates")
        values[name] = ask(f"  {name} ({hint}): ", PARSERS[kind])
    facts = CaseFacts(**values)
    if facts.months_continuous_coverage is None and facts.policy_inception_date and facts.admission_date:
        from arzi.rules import months_between

        facts.months_continuous_coverage = months_between(facts.policy_inception_date, facts.admission_date)
        print(f"  computed months_continuous_coverage = {facts.months_continuous_coverage}")
    return facts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--letter", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--case-id", help="default: real-NNN")
    args = parser.parse_args()

    letter, policy = read_text(args.letter), read_text(args.policy)
    print(f"Letter: {args.letter.name} ({len(letter)} characters). Policy: {args.policy.name} ({len(policy)} characters).")
    print("Text is not shown here; open the files yourself.")

    categories = [c.value for c in Category]
    print("\nCategory:")
    for i, c in enumerate(categories, 1):
        print(f"  {i}. {c}")
    category = Category(ask("Category number: ", parse_choice(categories), allow_blank=False))
    facts = ask_facts()

    rules = evaluate(category, facts)
    print(f"\nRules engine says: {rules.verdict.value} ({', '.join(rules.reason_codes)})")
    verdicts = [v.value for v in Verdict]
    print("Your verdict (the label used for scoring):")
    for i, v in enumerate(verdicts, 1):
        print(f"  {i}. {v}")
    verdict = Verdict(ask("Verdict number: ", parse_choice(verdicts), allow_blank=False))
    if verdict is not rules.verdict:
        print(f"  Note: this differs from the rules ({rules.verdict.value}). Saved as you chose.")
    reason = ask("One-line reason (optional): ", str) or f"Hand-labelled: {verdict.value}."

    label = ModelOutput(category=category, verdict=verdict, facts=facts, reason=reason[:600], ask_insurer_for=list(rules.ask_insurer_for))
    REAL_DIR.mkdir(parents=True, exist_ok=True)
    case_id = args.case_id or f"real-{len(list(REAL_DIR.glob('*.json'))) + 1:03d}"
    out = REAL_DIR / f"{case_id}.json"
    if out.exists():
        raise SystemExit(f"{out} already exists; pass a different --case-id")
    out.write_text(json.dumps({"case_id": case_id, "letter": letter, "policy": policy, "label": label.model_dump(mode="json")}, ensure_ascii=False, indent=1))
    print(f"\nSaved {out} (gitignored).")


if __name__ == "__main__":
    main()
