"""LoRA supervised fine-tuning of Qwen3.5-4B on Tinker, using the cookbook training loop.

    python -m arzi.train.sft --dry-run     # token and cost estimate only
    python -m arzi.train.sft --name v1

Trains on the last assistant message of data/generated/train.jsonl, tracks loss
on val.jsonl, and appends the final sampler checkpoint to train/runs.json.
Only synthetic data is uploaded.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

from rich.console import Console

from arzi.tinker_client import BASE_MODEL, JUDGE_RENDERER

TRAIN_FILE = Path("data/generated/train.jsonl")
VAL_FILE = Path("data/generated/val.jsonl")
RUNS_FILE = Path("train/runs.json")
LOG_ROOT = Path("train/logs")  # gitignored
MAX_LENGTH = 4096
PRICE_PER_M_TRAIN_TOKENS = 0.737  # Qwen3.5-4B on Tinker, US$
MAX_RUN_COST_USD = 5.0
console = Console()


def estimate_tokens(path: Path) -> int:
    """Exact token count of the rendered training conversations (capped at MAX_LENGTH each)."""
    from tinker_cookbook.tokenizer_utils import get_tokenizer

    tokenizer = get_tokenizer(BASE_MODEL)
    total = 0
    for line in path.read_text().splitlines():
        text = "\n".join(m["content"] for m in json.loads(line)["messages"])
        total += min(len(tokenizer.encode(text)) + 20, MAX_LENGTH)  # + chat template tokens
    return total


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--name", default="v1")
    parser.add_argument("--train-file", type=Path, default=TRAIN_FILE)
    parser.add_argument("--epochs", type=int, default=2)
    parser.add_argument("--lora-rank", type=int, default=32)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--learning-rate", type=float, help="default: cookbook get_lr for the base model")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    from dotenv import load_dotenv
    from tinker_cookbook import checkpoint_utils, cli_utils, hyperparam_utils
    from tinker_cookbook.renderers import TrainOnWhat
    from tinker_cookbook.supervised import train
    from tinker_cookbook.supervised.data import FromConversationFileBuilder
    from tinker_cookbook.supervised.nll_evaluator import NLLEvaluator
    from tinker_cookbook.supervised.types import ChatDatasetBuilderCommonConfig

    load_dotenv()
    lr = args.learning_rate or hyperparam_utils.get_lr(BASE_MODEL)
    n_rows = sum(1 for line in args.train_file.read_text().splitlines() if line.strip())
    tokens = estimate_tokens(args.train_file) * args.epochs
    cost = tokens * PRICE_PER_M_TRAIN_TOKENS / 1e6
    steps = (n_rows // args.batch_size) * args.epochs
    console.print(
        f"{n_rows} rows x {args.epochs} epochs = ~{tokens:,} training tokens, about US${cost:.2f} "
        f"({steps} steps, batch {args.batch_size}, rank {args.lora_rank}, lr {lr:.2e}, renderer {JUDGE_RENDERER})"
    )
    if cost > MAX_RUN_COST_USD:
        raise SystemExit(f"Estimated cost is above US${MAX_RUN_COST_USD:.0f}. Not starting; ask Heet first.")
    if args.dry_run:
        return

    common = ChatDatasetBuilderCommonConfig(
        model_name_for_tokenizer=BASE_MODEL,
        renderer_name=JUDGE_RENDERER,
        max_length=MAX_LENGTH,
        batch_size=args.batch_size,
        train_on_what=TrainOnWhat.LAST_ASSISTANT_MESSAGE,
    )

    def val_evaluator():
        dataset, _ = FromConversationFileBuilder(common_config=common, file_path=str(VAL_FILE))()
        return NLLEvaluator.from_dataset(dataset, name="val")

    log_path = LOG_ROOT / args.name
    cli_utils.check_log_dir(str(log_path), behavior_if_exists="raise")
    config = train.Config(
        log_path=str(log_path),
        model_name=BASE_MODEL,
        recipe_name="arzi_sft",
        renderer_name=JUDGE_RENDERER,
        dataset_builder=FromConversationFileBuilder(common_config=common, file_path=str(args.train_file)),
        learning_rate=lr,
        lr_schedule="linear",
        num_epochs=args.epochs,
        lora_rank=args.lora_rank,
        evaluator_builders=[val_evaluator],
        eval_every=20,
        save_every=50,
    )
    asyncio.run(train.main(config))

    last = checkpoint_utils.get_last_checkpoint(str(log_path), required_key="sampler_path")
    if last is None:
        raise SystemExit(f"training finished but no sampler checkpoint was recorded in {log_path}")
    runs = json.loads(RUNS_FILE.read_text()) if RUNS_FILE.exists() else []
    runs.append(
        {
            "name": args.name,
            "finished_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "base_model": BASE_MODEL,
            "renderer": JUDGE_RENDERER,
            "train_file": str(args.train_file),
            "rows": n_rows,
            "epochs": args.epochs,
            "lora_rank": args.lora_rank,
            "batch_size": args.batch_size,
            "learning_rate": lr,
            "sampler_path": last.sampler_path,
            "state_path": last.state_path,
        }
    )
    RUNS_FILE.parent.mkdir(exist_ok=True)
    RUNS_FILE.write_text(json.dumps(runs, indent=1) + "\n")
    console.print(f"sampler checkpoint: {last.sampler_path}\nrecorded in {RUNS_FILE}")


if __name__ == "__main__":
    main()
