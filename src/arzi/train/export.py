"""Download the fine-tuned adapter from Tinker and merge it into a standalone HF model.

    python -m arzi.train.export                  # adapter -> models/adapter-<run>, merged -> models/arzi-4b
    python -m arzi.train.export --adapter-only   # just the adapter (small; for loading with PEFT)

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
    args = parser.parse_args()

    from tinker_cookbook import weights

    load_dotenv(Path.cwd() / ".env")
    runs = json.loads(RUNS_FILE.read_text())
    run = next(r for r in runs if r["name"] == args.run) if args.run else runs[-1]
    adapter_dir = Path(f"models/adapter-{run['name']}")
    if not adapter_dir.exists():
        download_adapter(run["state_path"], run["name"], adapter_dir)
    print(f"adapter: {adapter_dir}")
    if args.adapter_only:
        return

    # the base model is ~9.3 GB and the merged copy about the same; check before starting
    free_gb = shutil.disk_usage(".").free / 1e9
    if free_gb < 22:
        raise SystemExit(f"Only {free_gb:.0f} GB free; merging needs about 22 GB (base download + merged copy + headroom).")
    weights.build_hf_model(base_model=BASE_MODEL, adapter_path=str(adapter_dir), output_path=str(MERGED_DIR), trust_remote_code=True)
    print(f"merged model: {MERGED_DIR}")


if __name__ == "__main__":
    main()
