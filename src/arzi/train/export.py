"""Download the fine-tuned adapter from Tinker, merge it, and convert it to a 4-bit GGUF.

    python -m arzi.train.export                  # adapter -> merged bf16 -> models/arzi-4b-q4_k_m.gguf
    python -m arzi.train.export --adapter-only   # just the adapter
    python -m arzi.train.export --keep-merged    # also keep the 8.7 GB bf16 merged model

The app runs the GGUF with llama.cpp (brew install llama.cpp). Conversion needs llama.cpp's
convert_hf_to_gguf.py and its gguf-py package from a checkout at tools/llama.cpp-src.

Uses the latest run in train/runs.json unless --run is given. models/ is gitignored.

The cookbook's weights.download() goes through the deprecated checkpoint-archive endpoint,
which timed out for us, so the adapter is exported with save_weights_external() and
fetched file by file from the signed URLs instead.
"""

from __future__ import annotations

import argparse
import json
import shutil
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

from arzi.tinker_client import BASE_MODEL

RUNS_FILE = Path("train/runs.json")
MERGED_DIR = Path("models/arzi-4b")
Q8_PATH = Path("models/arzi-4b-q8_0.gguf")
CONVERTER = Path("tools/llama.cpp-src/convert_hf_to_gguf.py")
TOKENIZER_FILES = ["tokenizer.json", "tokenizer_config.json", "vocab.json", "merges.txt", "chat_template.jinja", "config.json"]
BASE_DIR = Path("models/base-src")  # local copy of the base weights, consumed by the merge


def merge_consuming_base(adapter_dir: Path) -> None:
    """Merge with the cookbook's shard path, deleting each base shard once it is in memory.

    The base model (9.3 GB) and the merged copy (about the same) do not both fit on the
    dev machine, so peak disk use is kept to roughly one copy plus one shard. The base
    weights are gone afterwards; the base config and tokenizer files are kept.
    """
    from huggingface_hub import snapshot_download
    from tinker_cookbook.weights import build_hf_model
    from tinker_cookbook.weights._export import _shard_engine

    snapshot_download(BASE_MODEL, local_dir=BASE_DIR)
    original_load = _shard_engine.load_file

    def load_then_delete(path, *args, **kwargs):
        tensors = original_load(path, *args, **kwargs)
        source = Path(path).resolve()
        if source.is_relative_to(BASE_DIR.resolve()) and source.suffix == ".safetensors":
            source.unlink()
        return tensors

    _shard_engine.load_file = load_then_delete
    try:
        build_hf_model(base_model=str(BASE_DIR), adapter_path=str(adapter_dir), output_path=str(MERGED_DIR), trust_remote_code=True)
    finally:
        _shard_engine.load_file = original_load


def to_gguf(keep_merged: bool) -> None:
    """bf16 merged -> Q8_0 GGUF -> Q4_K_M GGUF, keeping the tokenizer files for the renderer."""
    import subprocess
    import sys

    from arzi.app.local_model import GGUF_PATH, TOKENIZER_DIR

    TOKENIZER_DIR.mkdir(parents=True, exist_ok=True)
    for name in TOKENIZER_FILES:
        shutil.copy(MERGED_DIR / name, TOKENIZER_DIR / name)
    # Q8 first: converting straight to bf16 GGUF needs another ~9 GB of disk
    subprocess.run([sys.executable, str(CONVERTER), str(MERGED_DIR), "--outtype", "q8_0", "--outfile", str(Q8_PATH)], check=True)
    subprocess.run(["llama-quantize", "--allow-requantize", str(Q8_PATH), str(GGUF_PATH), "Q4_K_M"], check=True)
    Q8_PATH.unlink()
    if not keep_merged:
        shutil.rmtree(MERGED_DIR)


def download_adapter(state_path: str, name: str, out_dir: Path) -> None:
    import tinker

    service = tinker.ServiceClient()
    saved = service.create_training_client_from_state(state_path).save_weights_external(f"arzi-{name}").result()
    urls = service.create_rest_client().get_external_weights_urls(saved.path).result(timeout=900).urls
    tmp = out_dir.with_suffix(".partial")
    tmp.mkdir(parents=True, exist_ok=True)
    for rel, url in urls.items():
        target = tmp / rel
        if not target.resolve().is_relative_to(tmp.resolve()):
            raise SystemExit(f"refusing unsafe path in export: {rel}")
        target.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(url, target)
    tmp.rename(out_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run", help="run name in train/runs.json (default: latest)")
    parser.add_argument("--adapter-only", action="store_true")
    parser.add_argument("--keep-merged", action="store_true")
    args = parser.parse_args()

    load_dotenv(Path.cwd() / ".env")
    runs = json.loads(RUNS_FILE.read_text())
    run = next(r for r in runs if r["name"] == args.run) if args.run else runs[-1]
    adapter_dir = Path(f"models/adapter-{run['name']}")
    if not adapter_dir.exists():
        download_adapter(run["state_path"], run["name"], adapter_dir)
    print(f"adapter: {adapter_dir}")
    if args.adapter_only:
        return

    free_gb = shutil.disk_usage(".").free / 1e9
    if free_gb < 13:
        raise SystemExit(f"Only {free_gb:.0f} GB free; the merge needs about 13 GB (one model copy plus one shard and headroom).")
    if not MERGED_DIR.exists():
        merge_consuming_base(adapter_dir)
    print(f"merged model: {MERGED_DIR}")
    to_gguf(args.keep_merged)
    print("4-bit model: models/arzi-4b-q4_k_m.gguf")


if __name__ == "__main__":
    main()
