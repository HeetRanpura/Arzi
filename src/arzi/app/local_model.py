"""Run the exported model on this machine. Used by the app and for the real-letter eval.

The fine-tuned model runs as a 4-bit GGUF (models/arzi-4b-q4_k_m.gguf) under llama.cpp's
llama-server, bound to 127.0.0.1 only. Prompt tokens come from the same cookbook renderer
used in training and Tinker eval (qwen3_5_disable_thinking) and are sent as token ids, so
local and Tinker inputs are identical. Greedy decoding.
"""

from __future__ import annotations

import json
import shutil
import socket
import subprocess
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from arzi.prompts import MAX_OUTPUT_TOKENS
from arzi.tinker_client import JUDGE_RENDERER

GGUF_PATH = Path("models/arzi-4b-q4_k_m.gguf")
TOKENIZER_DIR = Path("models/arzi-4b-tokenizer")  # tokenizer files kept from the merged model
CONTEXT_TOKENS = 8192
STARTUP_TIMEOUT_S = 120


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@dataclass
class LocalModel:
    name: str
    renderer: object
    server: subprocess.Popen
    port: int
    load_seconds: float

    @classmethod
    def load(cls, fine_tuned: bool = True, gguf: Path = GGUF_PATH) -> "LocalModel":
        from tinker_cookbook import renderers
        from tinker_cookbook.tokenizer_utils import get_tokenizer

        if not fine_tuned:
            raise SystemExit("Only the fine-tuned model is kept locally (the base weights were deleted to save disk).")
        if not gguf.exists():
            raise SystemExit(f"{gguf} not found: see README, 'Local model'")
        binary = shutil.which("llama-server")
        if binary is None:
            raise SystemExit("llama-server not found: brew install llama.cpp")

        start = time.perf_counter()
        port = _free_port()
        server = subprocess.Popen(
            [binary, "-m", str(gguf), "--host", "127.0.0.1", "--port", str(port), "-c", str(CONTEXT_TOKENS), "-ngl", "99", "--no-webui"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        model = cls(gguf.name, renderers.get_renderer(JUDGE_RENDERER, get_tokenizer(str(TOKENIZER_DIR))), server, port, 0.0)
        model._wait_ready()
        model.load_seconds = time.perf_counter() - start
        return model

    def _wait_ready(self) -> None:
        deadline = time.monotonic() + STARTUP_TIMEOUT_S
        while time.monotonic() < deadline:
            if self.server.poll() is not None:
                raise RuntimeError("llama-server exited during startup")
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/health", timeout=2) as r:
                    if json.load(r).get("status") == "ok":
                        return
            except OSError:
                pass
            time.sleep(0.5)
        self.unload()
        raise RuntimeError("llama-server did not become ready")

    def generate(self, messages: list[dict[str, str]], max_new_tokens: int = MAX_OUTPUT_TOKENS) -> str:
        from tinker_cookbook import renderers

        prompt = self.renderer.build_generation_prompt(messages).to_ints()
        body = {"prompt": prompt, "n_predict": max_new_tokens, "temperature": 0, "top_k": 1, "return_tokens": True, "cache_prompt": False}
        request = urllib.request.Request(f"http://127.0.0.1:{self.port}/completion", json.dumps(body).encode(), {"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=600) as r:
            tokens = json.load(r)["tokens"]
        message, _ = self.renderer.parse_response(tokens)
        return renderers.get_text_content(message)

    def unload(self) -> None:
        if self.server.poll() is None:
            self.server.terminate()
            try:
                self.server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.server.kill()

    def __enter__(self) -> "LocalModel":
        return self

    def __exit__(self, *exc) -> None:
        self.unload()
