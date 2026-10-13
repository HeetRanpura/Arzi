# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Status

This repo starts from `SPEC.md` only. **`SPEC.md` is the source of truth**: read it fully before writing code. Everything below summarises it; where code and this file disagree with the spec, the spec wins (or ask Heet). Update the Commands section here as modules actually land.

Arzi reads an Indian health insurance claim rejection letter plus policy text and returns a rejection category, a contestability verdict, extracted facts, what to ask the insurer for, and drafted complaint letters. It is a submission to the DEV Hacktoberfest 2026 "Best Use of Tinker" track: fine-tune `Qwen/Qwen3.5-4B` with Tinker LoRA SFT and show a measured improvement over the base model.

## Working agreement

- Build milestone by milestone (M1 to M7, SPEC section 11), in order. **Stop at every CHECKPOINT and report to Heet** before continuing. Checkpoint 2 is a go/no-go: if the base model already scores verdict accuracy >= 90% and false hope rate <= 5%, stop and say the fine-tuning story is weak.
- Ask before anything that would: commit real documents, change the eval set, or spend more than ~US$5 of Tinker credits in one run.
- Hard deadline: submissions close **Mon Oct 19 2026, ~12:29 PM IST**. The repo must be new and built inside Oct 12 to 18; no reused old code. Any commit after the deadline must be noted in the README.
- Do not build anything in SPEC section 13 (accounts, cloud hosting, sending emails, vision fine-tuning, etc.).

## Non-negotiables

- **Privacy:** user documents are processed only locally. Tinker is used only for training and for evaluating on **synthetic** data. No cloud API ever sees a user document.
- **Real letters never enter git.** `data/real/` is gitignored; `data/generated/raw/`, `models/`, `.env` too. Synthetic data uses fictional insurer names only.
- **Honest evaluation:** base and fine-tuned models use the same prompt, same eval set, same parser, same renderer, temperature 0. Never tune on `eval_synth.jsonl`; targeted data added in M4 goes to train only. Report numbers as they come out.
- **Not legal advice:** every results screen and every drafted letter carries the disclaimer. The app never sends anything.

## Commands

Working now (M1). Use the project venv (`.venv/bin/...`); system `python3` is 3.9.

```bash
uv venv --python 3.11 && uv pip install -e ".[dev]"   # add ,tinker or ,app extras when needed
.venv/bin/pytest                                       # all tests
.venv/bin/pytest tests/test_rules.py -k moratorium     # subset / single test
.venv/bin/python -m arzi.rules > RULES.md      # regenerate after editing rules.py (a test fails if stale)
```

Planned entry points (SPEC section 12); not built until their milestone:

```bash
python -m arzi.generate.build_dataset # reproducible splits from a fixed seed
python -m arzi.train.sft              # LoRA SFT; records checkpoint in train/runs.json
python -m arzi.eval.run_eval --model base|ft --set synth|real
python -m arzi.eval.label_real        # labelling CLI for anonymised real letters
python -m arzi.app.ui                 # local gradio app, must work offline
```

`TINKER_API_KEY` lives in `.env` (see `.env.example`). OCR needs system Tesseract.

## Architecture

Package is `src/arzi/`. The pieces that only make sense together:

- **`rules.py` is the label source.** A deterministic engine maps `CaseFacts` + `Category` to `(Verdict, reason_codes)`, first matching rule wins. It labels all synthetic data *and* cross-checks the model in the app. Rules are a data table (`RULES`) with three-valued tests: if a rule cannot be decided because a fact is `None`, evaluation stops with `WORTH_ASKING` and a `missing_fact:<field>` code (never guess). `RULES.md` is rendered from that table, never edited by hand, and needs Heet's review before training.
- **The parser lives in `schema.py`** (`parse_model_output`, raises `ParseError`).
- **Synthetic data flows code -> code -> LLM -> code:** `generate/facts.py` samples facts, `rules.py` labels them, a large teacher model (via Tinker sampling) writes the rejection letter and policy excerpt from the facts without stating the verdict, a validation pass checks key facts appear in the text, `noise.py` adds OCR-like noise to ~30%. The verdict is never produced by an LLM.
- **`prompts.py` holds the single system prompt and user template** shared by dataset building, baseline eval, fine-tuned eval, and the local app. Changing it invalidates existing datasets and prior eval numbers.
- **One parser everywhere.** The model must emit only a JSON object matching `ModelOutput` (`schema.py`). The same tolerant parser (code fences, trailing text) is used in eval and in the app; a parse failure counts as a wrong answer.
- **Eval set uses held-out letter styles** never seen in train, so the model cannot win by memorising templates. Synthetic and real-letter results are reported separately.
- **Headline metric is false hope rate:** of cases labelled `LIKELY_VALID`, the share predicted `LIKELY_CONTESTABLE`. The fine-tune must lower it while keeping contestable recall and beating base on verdict accuracy. Moratorium edge cases (55 to 65 months of coverage) are tracked as their own metric.
- **Two inference paths:** Tinker sampling clients for training-time eval (base, fine-tuned, optional teacher reference); a merged HF model in `models/arzi-4b/` loaded with `transformers` for the app (`train/export.py` -> `app/local_model.py`).
- **App pipeline:** `extract.py` (pypdf, OCR fallback) -> local model -> parse -> `rules.py` cross-check on the returned facts -> if model and rules verdicts disagree, show `WORTH_ASKING` with both reasons -> `drafting/` letters and deadlines.
- **Drafting is template-based, not LLM-generated,** so letters are predictable. Escalation path: insurer grievance cell, then Bima Bharosa, then Insurance Ombudsman.

## Tinker specifics

- Use the Qwen3.5 disable-thinking renderer if `get_registered_renderer_names()` lists one, else `qwen3_5`; outputs must have no `<think>` block. Same renderer for the baseline.
- Prefer the cookbook `train.main(config)` loop with `FromConversationFileBuilder` over a hand-written loop. Print estimated training tokens before starting a run.
- Check `service_client.get_server_capabilities()` before assuming the teacher model (`openai/gpt-oss-120b`) is available.
- Verify exact cookbook APIs (especially weight download and `build_hf_model`) against the current tinker-cookbook docs rather than trusting the spec's sketches.
