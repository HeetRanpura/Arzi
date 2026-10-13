"""Thin wrapper around Tinker sampling. Used for the teacher and for eval on SYNTHETIC data only.

User documents and real letters never go through this module.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from dotenv import load_dotenv

BASE_MODEL = "Qwen/Qwen3.5-4B"
# same renderer for baseline, training and fine-tuned eval: plain JSON, no <think> block
JUDGE_RENDERER = "qwen3_5_disable_thinking"
TEACHER_MODELS = ["openai/gpt-oss-120b", "Qwen/Qwen3.5-397B-A17B"]

Completer = Callable[[list[dict[str, str]]], Awaitable[str]]


def service_client():
    import tinker

    load_dotenv()
    return tinker.ServiceClient()


def available_models(service) -> list[str]:
    return [m.model_name for m in service.get_server_capabilities().supported_models if m.model_name]


def pick_teacher(service) -> str:
    available = available_models(service)
    for name in TEACHER_MODELS:
        if name in available:
            return name
    raise RuntimeError(f"no teacher model available; server offers: {available}")


def default_renderer(model: str) -> str:
    from tinker_cookbook import model_info

    names = model_info.get_recommended_renderer_names(model)
    return next((n for n in names if "disable_thinking" in n), names[0])


def make_completer(
    service,
    base_model: str,
    *,
    model_path: str | None = None,
    renderer_name: str | None = None,
    temperature: float = 0.0,
    max_tokens: int = 700,
) -> Completer:
    """messages -> assistant text. `model_path` selects a fine-tuned checkpoint of `base_model`."""
    import tinker
    from tinker_cookbook import renderers
    from tinker_cookbook.tokenizer_utils import get_tokenizer

    renderer = renderers.get_renderer(renderer_name or default_renderer(base_model), get_tokenizer(base_model))
    if model_path:
        sampler = service.create_sampling_client(model_path=model_path)
    else:
        sampler = service.create_sampling_client(base_model=base_model)
    params = tinker.SamplingParams(temperature=temperature, max_tokens=max_tokens, stop=renderer.get_stop_sequences())

    async def complete(messages: list[dict[str, str]]) -> str:
        prompt = renderer.build_generation_prompt(messages)
        response = await sampler.sample_async(prompt, num_samples=1, sampling_params=params)
        message, _ = renderer.parse_response(response.sequences[0].tokens)
        return renderers.get_text_content(message)

    return complete
