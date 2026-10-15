# Arzi: Build Spec for Claude Code

> Read this whole file before writing code. Build milestone by milestone, in order. Stop at every **CHECKPOINT** and report results to Heet before continuing.

## 0. Context

- **What:** Arzi reads an Indian health insurance claim rejection letter plus the policy text and returns: the rejection category, a contestability verdict, the facts behind it, what to ask the insurer for, and drafted complaint letters for the escalation path. It runs locally on the user's laptop.
- **Why it exists:** submission to the DEV Hacktoberfest 2026 "Side Hustle" challenge, entering **Best Use of Tinker** (fine-tune a model with Tinker and show a clear improvement over a baseline).
- **Deadline:** submissions close Oct 18, 11:59 PM PDT = **Mon Oct 19, ~12:29 PM IST**. Target: post published **Sun Oct 18 night IST**.
- **Hard rules from the challenge:** the repo must be **new**, started and finished inside the window (Oct 12 to 18). Commits after the deadline must be noted in the README. No reused old code.
- **Core story for the write-up:** "A private, at-home check that tells a family whether their rejected claim is worth fighting, without giving false hope." The fine-tune must measurably reduce wrong "contestable" calls while keeping recall on genuinely contestable cases.

## 1. Non-negotiables

1. **Privacy:** user documents are processed only on the local machine. No cloud API sees user documents. Tinker is used only for training and for evaluating on **synthetic** data.
2. **Never commit real letters.** `data/real/` is gitignored. Real letters are anonymised by hand before they enter the repo, and even then stay out of git.
3. **Not legal advice.** Every output screen and every drafted letter carries a short disclaimer. The user reviews and sends letters themselves; the app never sends anything.
4. **Honest evaluation.** Baseline and fine-tuned model use the **same prompt, same eval set, same parser**. Report numbers as they come out. Never tune on the eval set.
5. Secrets in `.env` (`TINKER_API_KEY`), never committed. Provide `.env.example`.
6. License: MIT for code. README notes the base model's own license.

## 2. Tech stack

- Python 3.11+, `uv` or `pip` + `venv`.
- `tinker`, `tinker-cookbook` (install: `uv pip install tinker tinker-cookbook`).
- `pydantic` v2 for schemas, `pytest` for tests.
- `pypdf` for PDF text; `pytesseract` + system Tesseract for scanned images/photos (OCR); `Pillow`.
- `gradio` for the local UI (single page).
- Local inference: `transformers` + `torch` loading the **merged** fine-tuned model (see M6). Optional stretch: GGUF via llama.cpp for lower RAM.
- `rich` for CLI output, `python-dotenv` for env.

## 3. Repo layout

```
arzi/
  README.md
  SPEC.md                      # this file
  RULES.md                     # human-readable rule set (generated from rules.py docstrings + reviewed by Heet)
  LICENSE
  .env.example
  .gitignore                   # includes data/real/, data/generated/raw/, models/, .env
  pyproject.toml
  src/arzi/
    __init__.py
    schema.py                  # pydantic models: CaseFacts, ModelOutput, Verdict, Category
    rules.py                   # deterministic rule engine: facts -> verdict + reason codes
    prompts.py                 # THE single system prompt + user template (shared by baseline, training, app)
    extract.py                 # PDF/image -> text (pypdf, OCR fallback)
    generate/
      facts.py                 # sample structured CaseFacts per category with target distribution
      letters.py               # teacher model writes rejection letter + policy excerpt from facts
      noise.py                 # OCR-like noise, formatting variation
      build_dataset.py         # orchestrates: facts -> letters -> labels -> JSONL splits
    train/
      sft.py                   # Tinker LoRA SFT on train.jsonl
      export.py                # download sampler checkpoint, merge into HF model
    eval/
      run_eval.py              # sample from a Tinker sampling client (base or fine-tuned) on eval set
      metrics.py               # all metrics in section 8
      report.py                # writes eval/results/*.json and a markdown table for the post
    drafting/
      letters.py               # template-based complaint letters from ModelOutput + user details
      deadlines.py             # escalation timeline from dates
    app/
      local_model.py           # loads merged model locally, runs inference with prompts.py
      ui.py                    # gradio app
  data/
    generated/                 # train.jsonl, val.jsonl, eval_synth.jsonl (committed: synthetic only)
    real/                      # gitignored, hand-labelled real letters
  eval/results/                # metrics json + markdown tables (committed)
  tests/
    test_rules.py
    test_schema.py
    test_metrics.py
    test_parse.py
```

## 4. Schemas (`schema.py`)

```python
from enum import Enum
from datetime import date
from pydantic import BaseModel, Field

class Category(str, Enum):
    NON_DISCLOSURE_PED = "non_disclosure_ped"
    WAITING_PERIOD = "waiting_period"
    PERMANENT_EXCLUSION = "permanent_exclusion"
    NO_HOSPITALISATION_NEEDED = "no_hospitalisation_needed"
    ROOM_RENT_PROPORTIONATE = "room_rent_proportionate"
    DOCUMENTS_OR_LATE_INTIMATION = "documents_or_late_intimation"
    POLICY_LAPSED = "policy_lapsed"
    SUM_INSURED_EXHAUSTED = "sum_insured_exhausted"
    OTHER = "other"

class Verdict(str, Enum):
    LIKELY_CONTESTABLE = "likely_contestable"
    WORTH_ASKING = "worth_asking"
    LIKELY_VALID = "likely_valid"

class CaseFacts(BaseModel):
    # all optional: a letter may not state them
    policy_inception_date: date | None = None          # first policy with continuous cover, incl. portability
    admission_date: date | None = None
    months_continuous_coverage: int | None = None      # derived; see rules.py
    condition_named_by_insurer: str | None = None
    ped_disclosed_in_proposal: bool | None = None
    condition_related_to_claim: bool | None = None
    waiting_period_months: int | None = None           # the waiting period the insurer relies on
    is_accident: bool | None = None
    accident_exempt_in_wording: bool | None = None     # does the wording exempt accidents from this waiting period
    exclusion_cited: str | None = None
    exclusion_in_policy_wording: bool | None = None
    hospital_stay_hours: int | None = None
    is_listed_daycare_procedure: bool | None = None
    room_rent_limit_per_day: int | None = None         # INR
    room_rent_charged_per_day: int | None = None       # INR
    premium_paid_within_grace: bool | None = None
    restore_benefit_available_unused: bool | None = None
    crc_approval_mentioned: bool | None = None         # Claims Review Committee

class ModelOutput(BaseModel):
    category: Category
    verdict: Verdict
    facts: CaseFacts
    reason: str = Field(max_length=600)                # plain English, <= ~80 words
    ask_insurer_for: list[str] = Field(default_factory=list, max_length=6)
```

The model must output **only** a JSON object matching `ModelOutput`. `test_parse.py` covers: valid JSON, JSON wrapped in ``` fences, trailing text, missing fields, invalid enum values. A parse failure counts as a wrong answer in eval.

## 5. Rule engine (`rules.py`) and RULES.md

The rule engine turns `CaseFacts` + `Category` into `(Verdict, reason_codes)`. It is the **source of truth for synthetic labels** and a cross-check in the app.

v1 rules (simplified prototype set; Heet must review RULES.md before training):

| Category | Rule | Verdict |
| --- | --- | --- |
| NON_DISCLOSURE_PED | months_continuous_coverage >= 60 (moratorium: after 60 months, no contest on non-disclosure except established fraud) | LIKELY_CONTESTABLE |
| | ped_disclosed_in_proposal is True | LIKELY_CONTESTABLE |
| | condition_related_to_claim is False | WORTH_ASKING |
| | otherwise | LIKELY_VALID |
| WAITING_PERIOD | is_accident is True and waiting_period_months <= 1 (initial waiting does not apply to accidents) | LIKELY_CONTESTABLE |
| | is_accident is True, waiting_period_months > 1 and accident_exempt_in_wording is True | LIKELY_CONTESTABLE |
| | months_continuous_coverage >= waiting_period_months (includes ported continuous cover) | LIKELY_CONTESTABLE |
| | otherwise | LIKELY_VALID |
| PERMANENT_EXCLUSION | exclusion_in_policy_wording is False | LIKELY_CONTESTABLE |
| | otherwise | LIKELY_VALID |
| NO_HOSPITALISATION_NEEDED | hospital_stay_hours >= 24 or is_listed_daycare_procedure | LIKELY_CONTESTABLE |
| | otherwise | WORTH_ASKING |
| ROOM_RENT_PROPORTIONATE | room_rent_charged_per_day <= room_rent_limit_per_day | LIKELY_CONTESTABLE |
| | otherwise | WORTH_ASKING (check the deduction maths) |
| DOCUMENTS_OR_LATE_INTIMATION | always | WORTH_ASKING (resubmit / explain delay) |
| POLICY_LAPSED | premium_paid_within_grace is True | LIKELY_CONTESTABLE |
| | otherwise | LIKELY_VALID |
| SUM_INSURED_EXHAUSTED | restore_benefit_available_unused is True | WORTH_ASKING |
| | otherwise | LIKELY_VALID |
| OTHER | always | WORTH_ASKING |

Evaluation order (decided at Checkpoint 1): check every LIKELY_CONTESTABLE rule of the category first. If any is decidably true, return LIKELY_CONTESTABLE, whatever else is unknown. If none is true but at least one was undecidable because a fact is `None`, return **WORTH_ASKING** (never guess). Only when every contestable rule is decidable and false, try the remaining rules top to bottom (first match wins; an undecidable one also gives WORTH_ASKING).

Cross-cutting: If `crc_approval_mentioned` is not True, add "Confirmation that the Claims Review Committee approved this repudiation" to `ask_insurer_for`. Always add "The exact policy clause relied on". These two required items come first and the list is capped at 6 in code. If both dates are known and a stated month count differs from the computed one by more than 1, add "Confirm policy inception date and continuity of cover, including portability" (dates win).

`months_continuous_coverage` = whole months from `policy_inception_date` to `admission_date`.

Write `test_rules.py` with at least 2 tests per row of the table, plus the None-fact rule.

## 6. Synthetic data (`generate/`)

**Pipeline:** sample facts (code) -> label with rules.py (code) -> teacher model writes the documents from the facts (LLM) -> add noise (code) -> JSONL.

1. **facts.py:** sample `CaseFacts` + `Category` with this category mix (approx.): non_disclosure 25%, waiting_period 20%, permanent_exclusion 10%, no_hospitalisation 8%, room_rent 10%, documents/late 10%, lapsed 6%, sum_insured 6%, other 5%. Within each category, balance verdicts so that **LIKELY_VALID is at least 30%** of the set (the model must learn to say "valid"). Make **moratorium edge cases** (coverage 55 to 65 months) at least 15% of non-disclosure cases. Dates between 2019 and 2026. Sample `accident_exempt_in_wording` for accident cases in the waiting-period category.
2. **letters.py:** use a large open model via Tinker sampling as the teacher (default `openai/gpt-oss-120b`; alternative `Qwen/Qwen3.5-397B-A17B`; check `service_client.get_server_capabilities()` for availability). Prompt it with the facts and a randomly chosen style (insurer tone, TPA letterhead style, terse vs verbose, Indian English, partial Hindi phrases occasionally) to write: (a) a rejection or short-settlement letter, (b) a short policy schedule/excerpt (inception date, sum insured, room rent limit, waiting periods, exclusions list). The teacher must **not** state the verdict. Use fictional insurer names only (e.g. "Suraksha General Insurance"), never real insurer names or real people.
3. **Validation:** after generation, run a cheap check that each key fact appears in the text (dates, amounts). Drop and regenerate cases that fail.
4. **noise.py:** for 30% of cases, add OCR-like noise (broken line wraps, `0`/`O` swaps, stray headers/footers, missing punctuation).
5. **Splits:** `train.jsonl` ~600, `val.jsonl` ~60, `eval_synth.jsonl` ~80. The eval set uses **held-out letter styles** (styles never used in train) so the model can't win by memorising templates.
6. **Training target:** for each case, the assistant message is the `ModelOutput` JSON built from the sampled facts + rules.py verdict + a templated reason (vary wording across 4 to 6 templates per verdict path).

JSONL row format (chat, as tinker-cookbook expects):
```json
{"messages": [
  {"role": "system", "content": "<SYSTEM_PROMPT from prompts.py>"},
  {"role": "user", "content": "<user template filled with letter + policy text>"},
  {"role": "assistant", "content": "<ModelOutput JSON>"}
], "meta": {"case_id": "...", "category": "...", "verdict": "...", "style": "...", "noisy": true}}
```

## 7. Training (`train/sft.py`)

- Base model: `Qwen/Qwen3.5-4B` (dense 4B, vision-capable; we use text only).
- Renderer: list `get_registered_renderer_names()` and use the Qwen3.5 **disable-thinking** variant if one exists, otherwise `qwen3_5`. Outputs must be plain JSON with no `<think>` block. Same renderer for baseline eval.
- Method: LoRA SFT with `tinker_cookbook.supervised.train.Config` and a JSONL conversation dataset builder (`FromConversationFileBuilder`), train on the last assistant message only.
- Starting hyperparameters: `lora_rank=32`, `learning_rate` from `tinker_cookbook.hyperparam_utils.get_lr("Qwen/Qwen3.5-4B")`, `num_epochs=2`, batch size 8, `max_length=4096`, `eval_every` ~20 steps on val loss, `save_every` ~50.
- Save a **sampler checkpoint** at the end (`tinker://<run_id>/sampler_weights/final`) and record its path in `train/runs.json`.
- Budget sanity check: print estimated training tokens before starting.

Reference pattern (from Tinker's first-SFT tutorial):
```python
service_client = tinker.ServiceClient()
training_client = service_client.create_lora_training_client(base_model="Qwen/Qwen3.5-4B", rank=32)
# ... forward_backward(data, "cross_entropy"), optim_step(tinker.AdamParams(learning_rate=lr))
sampling_client = training_client.save_weights_and_get_sampling_client()
```
Prefer the cookbook `train.main(config)` loop over a hand-written loop.

## 8. Evaluation (`eval/`)

Run on: `eval_synth.jsonl` and, when available, `data/real/*.json` (reported **separately**).

Models compared, all via Tinker sampling, temperature 0, same prompt:
1. **Base** Qwen3.5-4B (the baseline).
2. **Fine-tuned** checkpoint.
3. Optional reference: the teacher model, labelled as "large model reference" (not the baseline).

Metrics (`metrics.py`):
| Metric | Definition |
| --- | --- |
| Valid JSON rate | outputs that parse into `ModelOutput` |
| Category accuracy | exact category match |
| Verdict accuracy | exact verdict match |
| Contestable recall | of cases labelled LIKELY_CONTESTABLE, share predicted LIKELY_CONTESTABLE |
| **False hope rate** | of cases labelled LIKELY_VALID, share predicted LIKELY_CONTESTABLE (the headline number) |
| Moratorium edge accuracy | verdict accuracy on non-disclosure cases with coverage 55 to 65 months |
| Fact accuracy | per-field exact match for dates/ints/bools on non-null gold fields |

`report.py` writes `eval/results/<model>_<set>.json` and `eval/results/summary.md` with one comparison table (base vs fine-tuned) ready to paste into the DEV post. Also print 5 example cases where base and fine-tuned disagree.

## 9. Local app (`app/`)

- **Export (train/export.py):** `tinker_cookbook.weights.download(tinker_path=..., output_dir="./models/adapter")`, then merge into a standalone HF model with `tinker_cookbook.weights.build_hf_model(...)` into `./models/arzi-4b/`. Check the cookbook docs ("Merge into a HuggingFace Model") for exact arguments.
- **local_model.py:** load the merged model with `transformers` (bf16 on Apple Silicon/CUDA, float32 on CPU if needed), apply the same chat template and `prompts.py`, greedy decode, parse with the same parser as eval. If RAM < 16 GB, document the GGUF/llama.cpp route as a stretch.
- **Pipeline per request:** extract text (extract.py) -> local model -> parse -> rules.py cross-check on returned facts -> if model verdict and rules verdict disagree, show **WORTH_ASKING** with both reasons -> drafting.
- **ui.py (gradio, one page):**
  1. Upload rejection letter (PDF/image) and policy document (PDF/image), or paste text.
  2. Optional fields: insured name, policy number, claim number, insurer email (used only to fill letter templates, never stored).
  3. Results card: category, verdict (colour: green contestable / amber worth asking / grey likely valid), reason, "ask your insurer for" list.
  4. Tabs with drafted letters: (a) insurer grievance cell, (b) Bima Bharosa grievance text, (c) Insurance Ombudsman complaint summary. Copy buttons.
  5. Deadlines panel: insurer reply due (complaint date + 30 days); Ombudsman last date (1 year from insurer's final reply, or from the end of the 30-day window if no reply).
  6. Footer: "Runs on your computer. Nothing is uploaded. This is not legal advice."
- **Offline proof for the demo:** document how to run the app with Wi-Fi off.

## 10. Drafting (`drafting/`)

Template-based (Jinja2 or f-strings), not LLM-generated, so letters are predictable. Each letter: subject line, policy/claim numbers, the category in plain words, the specific grounds (from reason codes, e.g. moratorium), the "ask insurer for" items, a request for a written reply within 30 days, and the disclaimer. Escalation facts to state: insurer first; Bima Bharosa if unsatisfied or no reply in 30 days; Ombudsman within one year, free, claims up to INR 50 lakh.

## 11. Milestones and checkpoints

Heet's timetable: Wed 10 to 2 college, Thu 8 to 4 college, **Fri free**, Sat 10 to 2 college, **Sun free**.

**M1 (Tue night / Wed): scaffold + rules**
- Repo scaffold, pyproject, .gitignore, .env.example, README stub, LICENSE.
- schema.py, rules.py, RULES.md, tests passing.
- **CHECKPOINT 1:** show RULES.md to Heet for review.

**M2 (Wed): generator + 40 cases + baseline go/no-go**
- facts.py, letters.py, noise.py; generate 40 cases across all categories.
- prompts.py; run the **base model** on these 40 via Tinker sampling; compute metrics.
- **CHECKPOINT 2 (GO/NO-GO):** if base verdict accuracy >= 90% and false hope rate <= 5%, STOP and tell Heet: the fine-tuning story is weak; suggest making the task harder (more edge cases, noisier text) or switching idea. Otherwise continue.

**M3 (Thu): full dataset + training v1**
- Generate full splits (section 6). Spot-check 10 random cases and print them for Heet.
- Run SFT v1. Save checkpoint path.
- **CHECKPOINT 3:** eval base vs v1 on eval_synth; show summary.md.

**M4 (Fri morning): iterate**
- If v1 has weak spots (e.g. moratorium edge cases, false hope), add targeted training data and train v2. Do not touch eval_synth.
- **CHECKPOINT 4:** final model choice with numbers.

**M5 (Fri afternoon): export + local app + real letters**
- Export and merge weights, local_model.py, extract.py, drafting, ui.py.
- Heet adds anonymised real letters to data/real/ with a small labelling CLI (`python -m arzi.eval.label_real`); run eval on real set.
- **CHECKPOINT 5:** app runs end to end offline on Heet's laptop.

**M6 (Sat): first user + demo**
- Heet runs it with a real person; capture their feedback in `docs/first_user.md`.
- Record a 1 to 2 minute demo (upload letter -> verdict -> letter -> Wi-Fi off).

**M7 (Sun): write-up**
- README: what, why open, how to run, eval table, limitations, disclaimer, model license note.
- Draft DEV post sections from summary.md (Heet writes the final post in his own words).

## 12. Acceptance criteria

- [ ] `pytest` passes.
- [ ] `python -m arzi.generate.build_dataset` reproduces splits from a fixed seed.
- [ ] `python -m arzi.train.sft` trains and records a checkpoint path.
- [ ] `python -m arzi.eval.run_eval --model base|ft --set synth|real` writes results; `summary.md` shows base vs fine-tuned.
- [ ] Fine-tuned model beats base on verdict accuracy **and** has a lower false hope rate on eval_synth.
- [ ] `python -m arzi.app.ui` runs locally with no network access after model download.
- [ ] No real letters, names, or policy numbers in git history.

## 13. Out of scope (do not build)

Accounts, cloud hosting, payments, sending emails, consumer-court drafting, life/motor insurance, mobile app, vision fine-tuning (text only for v1).

## 14. Known limitations to state honestly in README and post

- Rules are a simplified prototype; regulations change; not legal advice.
- Training data is synthetic; real-letter eval set is small.
- Similar tools exist (e.g. cloud-based AI grievance tools in India); Arzi's difference is local, private inference with a measured fine-tune.

## 15. First message to Claude Code

> Read SPEC.md fully. Start Milestone M1. Ask me before anything that would commit real documents, change the eval set, or spend more than ~US$5 of Tinker credits in one run.

## 16. Partner categories: Tinker (primary), Gemma, GitHub Copilot

The project and package are named **Arzi** (`src/arzi/`); earlier drafts of this spec called it ClaimFighter.

### 16a. GitHub Actions

* `.github/workflows/ci.yml`: on push and pull_request, set up Python 3.11, install deps, run pytest (includes the RULES.md drift test).
* `.github/workflows/eval.yml`: on workflow_dispatch only, uses secret TINKER_API_KEY, runs `python -m arzi.eval.run_eval` for base and fine-tuned on eval_synth, writes eval/results/summary.md to the job summary (`$GITHUB_STEP_SUMMARY`) and uploads it as an artifact. Never runs on real data.
* From M5 onward (decided at Checkpoint 4, overriding the Oct 14 push-to-main note): all work happens on feature branches with a PR into main, so Copilot code review can be requested. Never push directly to main. At each STOP point, open or update the PR and wait; Heet merges.

### 16b. Gemma 4 reader (Milestone M5, after the PDF path works)

* `src/arzi/read_image.py`: if the upload is an image, send it to a local Gemma 4 vision model through Ollama (check the exact tag on ollama.com, prefer the E4B size) with a prompt to transcribe the letter verbatim as plain text, no summarising. Fallback to Tesseract if Ollama or the model is unavailable.
* Load Gemma only for image uploads and unload it before running the judge model.
* Eval: `arzi.eval.ocr_eval` renders 50 eval_synth letters to images with phone-photo augmentation (skew, shadow, blur, JPEG compression), runs Gemma and Tesseract, and reports field recall for dates, amounts and policy numbers. Write to eval/results/ocr_summary.md.

### 16c. Gemma explainer (optional, only if M5 is done by Saturday noon)

* After the verdict, Gemma rewrites the reason in Hindi, Marathi or Gujarati (user's choice in the UI). Mark the translated text as "explanation only; the English letter is the official version".
