"""Run the exported model on this machine. Used by the app and for the real-letter eval.

Prompt tokens come from the same cookbook renderer used in training and Tinker eval
(qwen3_5_disable_thinking), so local and Tinker inputs are identical. Greedy decoding.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from arzi.prompts import MAX_OUTPUT_TOKENS
from arzi.tinker_client import BASE_MODEL, JUDGE_RENDERER

MERGED_DIR = Path("models/arzi-4b")


def pick_device() -> tuple[str, "object"]:
    import torch

    if torch.cuda.is_available():
        return "cuda", torch.bfloat16
    if torch.backends.mps.is_available():
        return "mps", torch.bfloat16
    return "cpu", torch.float32


@dataclass
class LocalModel:
    name: str
    model: object
    renderer: object
    device: str
    load_seconds: float

    @classmethod
    def load(cls, fine_tuned: bool = True, path: Path = MERGED_DIR) -> "LocalModel":
        from tinker_cookbook import renderers
        from tinker_cookbook.tokenizer_utils import get_tokenizer
        from transformers import AutoModelForCausalLM

        source = str(path) if fine_tuned else BASE_MODEL
        if fine_tuned and not path.exists():
            raise SystemExit(f"{path} not found: run python -m arzi.train.export first")
        start = time.perf_counter()
        device, dtype = pick_device()
        model = AutoModelForCausalLM.from_pretrained(source, dtype=dtype, trust_remote_code=True).to(device).eval()
        renderer = renderers.get_renderer(JUDGE_RENDERER, get_tokenizer(BASE_MODEL))
        return cls(source, model, renderer, device, time.perf_counter() - start)

    def generate(self, messages: list[dict[str, str]], max_new_tokens: int = MAX_OUTPUT_TOKENS) -> str:
        import torch
        from tinker_cookbook import renderers

        prompt = self.renderer.build_generation_prompt(messages).to_ints()
        input_ids = torch.tensor([prompt], device=self.device)
        stop_ids = [s for s in self.renderer.get_stop_sequences() if isinstance(s, int)]
        with torch.no_grad():
            output = self.model.generate(
                input_ids,
                attention_mask=torch.ones_like(input_ids),
                max_new_tokens=max_new_tokens,
                do_sample=False,
                eos_token_id=stop_ids or None,
            )
        message, _ = self.renderer.parse_response(output[0, len(prompt) :].tolist())
        return renderers.get_text_content(message)

    def unload(self) -> None:
        import gc

        import torch

        self.model = None
        gc.collect()
        if self.device == "mps":
            torch.mps.empty_cache()
        elif self.device == "cuda":
            torch.cuda.empty_cache()
