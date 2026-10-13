"""The teacher model writes a rejection letter and a policy excerpt from sampled facts.

The teacher is told what the documents must state, never the verdict. Output is
checked for the key facts and regenerated when one is missing.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass

from arzi.generate.facts import Case
from arzi.tinker_client import Completer

# Styles used for train, val and the pilot.
TRAIN_STYLES = [
    "formal insurer repudiation letter in long legal sentences, with 'Without prejudice' and clause references",
    "terse TPA claim denial note, short lines, almost no pleasantries",
    "TPA letter that opens with a reference block (Claim No / Policy No / Patient / Hospital / DOA) and then two or three paragraphs",
    "email from a claims executive, semi-formal, with a subject line and a signature block",
    "letter with numbered paragraphs (1., 2., 3.) in bureaucratic Indian English ('kindly note', 'we regret to inform', 'the same')",
    "formal letter in Indian English with an occasional Hindi phrase in Roman script (for example 'kripya dhyan dein', 'dhanyavaad')",
    "claim settlement advice with a small plain-text table of amounts, followed by remarks",
    "polite customer-care style letter that apologises a lot and buries the actual ground in the middle",
]
# Held out: used ONLY for eval_synth, so the model cannot win by memorising templates.
EVAL_STYLES = [
    "claim status printout from a customer portal: mostly 'Field: value' lines and a free-text 'Remarks' box",
    "reply to a grievance email, conversational, referring to 'your mail' and restating the decision",
    "two-part document: a three-line SMS-style alert, then a formal annexure headed 'Reasons for decision'",
    "letter from a regional claims hub signed by a medical officer, heavy on clinical wording and abbreviations (DOA, DOD, H/O, k/c/o)",
]

TEACHER_PROMPT = """You are helping build a synthetic dataset. Write two fictional documents about one Indian health insurance claim. Everything is fictional.

DOCUMENT 1: the insurer's rejection or short-settlement letter.
Style: {style}
It must convey every point below. Lines starting with "Do NOT" are restrictions, not content.
{letter_points}

DOCUMENT 2: an excerpt of the policy schedule and policy wording, as the customer would have it (150 to 300 words).
It must convey every point below. Lines starting with "Do NOT" are restrictions, not content.
{policy_points}

Rules:
- Copy every date, amount, number, policy number and name exactly as written above, in the same format.
- Do not add any other dates, amounts, durations, waiting periods, exclusions or diseases. You may add an address, a signatory designation and a grievance contact line.
- Never say or hint whether the rejection is right or wrong, and give the customer no opinion on the merits.
- Write as the insurer would. Do not copy instruction wording such as "Ground of rejection" or "Do NOT".
- Use only the fictional names given. No real companies and no real people.
- Plain text only, no markdown.

Output exactly this structure:
===LETTER===
<document 1>
===POLICY===
<document 2>
===END==="""

_SPLIT = re.compile(r"===LETTER===(.*?)===POLICY===(.*?)(?:===END===|$)", re.DOTALL)
# verdict words, or instruction wording copied through
_LEAKS = ("contestable", "likely valid", "likely_valid", "worth asking", "worth_asking", "do not mention", "do not state", "do not include", "do not say")


@dataclass
class Documents:
    letter: str
    policy: str
    style: str
    attempts: int


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().replace(",", ""))


def validate(case: Case, letter: str, policy: str) -> list[str]:
    """Problems with a generated pair; empty means it states the key facts."""
    problems = []
    nl, np_ = _norm(letter), _norm(policy)
    problems += [f"letter missing {s!r}" for s in case.letter_must if _norm(s) not in nl]
    problems += [f"policy missing {s!r}" for s in case.policy_must if _norm(s) not in np_]
    problems += [f"policy must not contain {s!r}" for s in case.policy_must_not if _norm(s) in np_]
    problems += [f"leaks {s!r}" for s in _LEAKS if s in nl or s in np_]
    if len(letter) < 200 or len(policy) < 150:
        problems.append("too short")
    return problems


def teacher_messages(case: Case, style: str) -> list[dict[str, str]]:
    prompt = TEACHER_PROMPT.format(
        style=style,
        letter_points="\n".join(f"- {p}" for p in case.letter_points),
        policy_points="\n".join(f"- {p}" for p in case.policy_points),
    )
    return [{"role": "user", "content": prompt}]


async def write_documents(case: Case, style: str, teacher: Completer, max_attempts: int = 3) -> Documents | None:
    """None when every attempt failed validation; the caller drops the case."""
    messages = teacher_messages(case, style)
    for attempt in range(1, max_attempts + 1):
        match = _SPLIT.search(await teacher(messages))
        if not match:
            continue
        letter, policy = match.group(1).strip(), match.group(2).strip()
        if not validate(case, letter, policy):
            return Documents(letter, policy, style, attempt)
    return None


def pick_style(rng: random.Random, held_out: bool) -> str:
    return rng.choice(EVAL_STYLES if held_out else TRAIN_STYLES)
