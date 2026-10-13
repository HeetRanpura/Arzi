"""OCR-like noise and formatting damage for scanned or photographed letters."""

from __future__ import annotations

import random
import re

STRAY_LINES = [
    "Page 1 of 2",
    "Page 2 of 2",
    "-- 1 --",
    "Scanned with CamScanner",
    "Regd. Office: 4th Floor, Plot 12, Sector 9, Insurance Bhavan Marg",
    "IRDAI Regn. No. 000 | CIN: U66010MH2015PLC000000",
    "This is a computer generated document and does not require signature",
    "Toll free 1800 000 0000 | care@example.invalid",
    "CONFIDENTIAL",
]
# typical single-character OCR confusions
SWAPS = {"0": "O", "O": "0", "1": "l", "l": "1", "5": "S", "S": "5", "8": "B"}


def add_noise(text: str, rng: random.Random) -> str:
    # strip markdown emphasis the way OCR would lose it
    text = re.sub(r"\*\*|__", "", text)

    # character confusions, kept rare so most numbers survive
    out = []
    for ch in text:
        if ch in SWAPS and rng.random() < 0.025:
            ch = SWAPS[ch]
        elif ch in ",.:" and rng.random() < 0.08:
            ch = ""  # missing punctuation
        out.append(ch)
    text = "".join(out)

    # broken line wraps: split some lines mid-sentence, join some others
    lines: list[str] = []
    for line in text.split("\n"):
        words = line.split(" ")
        if len(words) > 8 and rng.random() < 0.5:
            cut = rng.randint(4, len(words) - 3)
            lines += [" ".join(words[:cut]), " ".join(words[cut:])]
        elif lines and line.strip() and lines[-1].strip() and rng.random() < 0.12:
            lines[-1] += " " + line.strip()
        else:
            lines.append(line)

    # stray headers and footers
    for _ in range(rng.randint(1, 3)):
        lines.insert(rng.randint(0, len(lines)), rng.choice(STRAY_LINES))
    return "\n".join(lines)
