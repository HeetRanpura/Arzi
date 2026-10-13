# Arzi

A private, at-home check that tells a family whether their rejected health insurance claim is worth fighting, without giving false hope.

Arzi reads an Indian health insurance claim rejection letter and the policy text, then returns the rejection category, a contestability verdict, the facts behind it, what to ask the insurer for, and drafted complaint letters for the escalation path. It runs on your own computer; your documents are never uploaded.

**Status:** work in progress, built during the DEV Hacktoberfest 2026 "Side Hustle" challenge (Oct 12 to 18, 2026).

**This is not legal advice.** The rules in [RULES.md](RULES.md) are a simplified prototype and regulations change. Review everything yourself before sending any letter.

## Setup

```bash
uv venv --python 3.11
uv pip install -e ".[dev]"
.venv/bin/pytest
```

## License

Code is MIT (see [LICENSE](LICENSE)). The fine-tuned model is derived from `Qwen/Qwen3.5-4B` and is subject to that model's own license.
