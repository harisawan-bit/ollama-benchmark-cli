"""Command line interface for ollama-benchmark-cli."""

from __future__ import annotations

import csv
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import click
import httpx
import psutil
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from benchmarks import get_default_prompts

console = Console()
error_console = Console(stderr=True)

MAX_MODEL_LENGTH = 128
MAX_PROMPT_LENGTH = 8_000
MAX_PROMPT_COUNT = 100
MODEL_PATTERN = re.compile(r"^[A-Za-z0-9._:/@-]+$")
ALLOWED_PROMPT_EXTENSIONS = {".txt", ".md", ".json", ".jsonl"}
ALLOWED_OUTPUT_EXTENSIONS = {".csv"}


class BenchmarkError(Exception):
    """Friendly error raised for expected CLI failures."""


@dataclass
class PromptCase:
    index: int
    category: str
    prompt: str


@dataclass
class BenchmarkResult:
    index: int
    category: str
    prompt_preview: str
    tokens: int
    tokens_per_second: float
    time_to_first_token: float
    total_time: float
    ram_delta_mb: float
    response_preview: str


def _parse_positive_int_env(name: str, default: int, minimum: int, maximum: int) -> int:
    raw_value = os.getenv(name, str(default)).strip()
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise BenchmarkError(f"{name} must be an integer.") from exc
    if not minimum <= value <= maximum:
        raise BenchmarkError(f"{name} must be between {minimum} and {maximum}.")
    return value


def _get_ollama_host() -> str:
    host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").strip().rstrip("/")
    if not host:
        raise BenchmarkError("OLLAMA_HOST cannot be empty.")
    if not host.startswith(("http://", "https://")):
        raise BenchmarkError("OLLAMA_HOST must start with http:// or https://.")
    if len(host) > 255:
        raise BenchmarkError("OLLAMA_HOST is too long.")
    return host


def _get_optional_api_key() -> str | None:
    # Sensitive config: put real tokens only in .env, never in committed code.
    api_key = os.getenv("OLLAMA_API_KEY", "").strip()
    if not api_key or api_key == "YOUR_API_KEY_HERE":
        return None
    if len(api_key) > 1_000:
        raise BenchmarkError("OLLAMA_API_KEY is unexpectedly long.")
    return api_key


def _validate_model_name(model: str) -> str:
    cleaned = model.strip()
    if not cleaned:
        raise BenchmarkError("--model is required.")
    if len(cleaned) > MAX_MODEL_LENGTH:
        raise BenchmarkError(f"--model must be {MAX_MODEL_LENGTH} characters or fewer.")
    if not MODEL_PATTERN.fullmatch(cleaned):
        raise BenchmarkError("Model names can only contain letters, numbers, '.', '_', '-', ':', '/', and '@'.")
    return cleaned


def _validate_prompt_text(prompt: str, label: str) -> str:
    cleaned = prompt.strip()
    if not cleaned:
        raise BenchmarkError(f"{label} is empty.")
    if len(cleaned) > MAX_PROMPT_LENGTH:
        raise BenchmarkError(f"{label} exceeds {MAX_PROMPT_LENGTH} characters.")
    return cleaned


def _safe_resolve_path(raw_path: str, purpose: str) -> Path:
    cleaned = raw_path.strip()
    if not cleaned:
        raise BenchmarkError(f"{purpose} path cannot be empty.")
    if len(cleaned) > 260:
        raise BenchmarkError(f"{purpose} path is too long.")
    return Path(cleaned).expanduser().resolve()


def _load_prompts_from_file(raw_path: str) -> list[PromptCase]:
    path = _safe_resolve_path(raw_path, "Prompt file")
    if not path.exists() or not path.is_file():
        raise BenchmarkError("Prompt file not found. Check the path and try again.")
    if path.suffix.lower() not in ALLOWED_PROMPT_EXTENSIONS:
        raise BenchmarkError(
            "Prompt file must be one of: " + ", ".join(sorted(ALLOWED_PROMPT_EXTENSIONS))
        )
    if path.stat().st_size > 1_000_000:
        raise BenchmarkError("Prompt file is too large. Limit it to 1 MB.")

    text = path.read_text(encoding="utf-8")
    prompts: list[PromptCase] = []

    if path.suffix.lower() == ".json":
        parsed = json.loads(text)
        if not isinstance(parsed, list):
            raise BenchmarkError("JSON prompt file must contain a list.")
        for index, item in enumerate(parsed, start=1):
            if isinstance(item, str):
                prompt = _validate_prompt_text(item, f"Prompt {index}")
                prompts.append(PromptCase(index=index, category="custom", prompt=prompt))
            elif isinstance(item, dict):
                prompt = _validate_prompt_text(str(item.get("prompt", "")), f"Prompt {index}")
                category = str(item.get("category", "custom")).strip()[:80] or "custom"
                prompts.append(PromptCase(index=index, category=category, prompt=prompt))
            else:
                raise BenchmarkError("JSON prompt items must be strings or objects with a prompt field.")
    elif path.suffix.lower() == ".jsonl":
        for index, line in enumerate(text.splitlines(), start=1):
            if not line.strip():
                continue
            item = json.loads(line)
            if not isinstance(item, dict):
                raise BenchmarkError("JSONL prompt lines must be objects.")
            prompt = _validate_prompt_text(str(item.get("prompt", "")), f"Prompt {index}")
            category = str(item.get("category", "custom")).strip()[:80] or "custom"
            prompts.append(PromptCase(index=len(prompts) + 1, category=category, prompt=prompt))
    else:
        blocks = [block.strip() for block in re.split(r"\n-{3,}\n", text) if block.strip()]
        if len(blocks) == 1:
            blocks = [line.strip() for line in text.splitlines() if line.strip()]
        for index, prompt in enumerate(blocks, start=1):
            prompts.append(
                PromptCase(index=index, category="custom", prompt=_validate_prompt_text(prompt, f"Prompt {index}"))
            )

    if not prompts:
        raise BenchmarkError("Prompt file did not contain any prompts.")
    if len(prompts) > MAX_PROMPT_COUNT:
        raise BenchmarkError(f"Prompt file contains too many prompts. Limit: {MAX_PROMPT_COUNT}.")
    return prompts


def _get_prompt_cases(raw_path: str | None) -> list[PromptCase]:
    if raw_path:
        return _load_prompts_from_file(raw_path)
    return [
        PromptCase(
            index=index,
            category=_validate_prompt_text(item["category"], f"Category {index}")[:80],
            prompt=_validate_prompt_text(item["prompt"], f"Prompt {index}"),
        )
        for index, item in enumerate(get_default_prompts(), start=1)
    ]


def _validate_output_path(raw_path: str | None) -> Path | None:
    if raw_path is None:
        return None
    path = _safe_resolve_path(raw_path, "Output")
    if path.suffix.lower() not in ALLOWED_OUTPUT_EXTENSIONS:
        raise BenchmarkError("Only CSV output is supported. Use a .csv file.")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not path.is_file():
        raise BenchmarkError("Output path must be a file.")
    return path


def _headers() -> dict[str, str]:
    headers = {"Accept": "application/x-ndjson, application/json"}
    api_key = _get_optional_api_key()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def _ensure_ollama_ready(client: httpx.Client, host: str, model: str) -> None:
    try:
        response = client.get(f"{host}/api/tags", headers=_headers())
    except httpx.ConnectError as exc:
        raise BenchmarkError(
            "Could not connect to Ollama. Start it with `ollama serve` or open the Ollama app."
        ) from exc
    response.raise_for_status()
    content_type = response.headers.get("content-type", "").lower()
    if "application/json" not in content_type:
        raise BenchmarkError("Unexpected response from Ollama /api/tags.")
    installed = response.json().get("models", [])
    installed_names = {item.get("name") for item in installed if isinstance(item, dict)}
    if installed_names and model not in installed_names:
        console.print(
            f"[yellow]Model '{model}' was not listed by Ollama. I will try it anyway in case it is being pulled or aliased.[/yellow]"
        )


def _count_output_tokens(final_payload: dict[str, object], response_text: str) -> int:
    eval_count = final_payload.get("eval_count")
    if isinstance(eval_count, int) and eval_count > 0:
        return eval_count
    return max(1, len(response_text.split()))


def _stream_ollama_generate(
    client: httpx.Client,
    host: str,
    model: str,
    prompt: str,
    timeout: int,
) -> tuple[str, int, float, float]:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": True,
        "options": {
            "temperature": 0,
        },
    }

    start = time.perf_counter()
    first_token_at: float | None = None
    response_chunks: list[str] = []
    final_payload: dict[str, object] = {}

    with client.stream(
        "POST",
        f"{host}/api/generate",
        json=payload,
        headers=_headers(),
        timeout=timeout,
    ) as response:
        response.raise_for_status()
        content_type = response.headers.get("content-type", "").lower()
        if "application/x-ndjson" not in content_type and "application/json" not in content_type:
            raise BenchmarkError("Unexpected Content-Type from Ollama generate endpoint.")

        for line in response.iter_lines():
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                raise BenchmarkError("Ollama returned invalid JSON while streaming.") from exc
            chunk = event.get("response", "")
            if chunk:
                if first_token_at is None:
                    first_token_at = time.perf_counter()
                response_chunks.append(str(chunk))
            if event.get("done"):
                final_payload = event
                break

    total_time = time.perf_counter() - start
    response_text = "".join(response_chunks)
    if first_token_at is None:
        first_token_at = time.perf_counter()
    tokens = _count_output_tokens(final_payload, response_text)
    return response_text, tokens, first_token_at - start, total_time


def _benchmark_prompt(
    client: httpx.Client,
    host: str,
    model: str,
    prompt_case: PromptCase,
    timeout: int,
) -> BenchmarkResult:
    process = psutil.Process(os.getpid())
    ram_before = process.memory_info().rss
    response_text, tokens, time_to_first_token, total_time = _stream_ollama_generate(
        client=client,
        host=host,
        model=model,
        prompt=prompt_case.prompt,
        timeout=timeout,
    )
    ram_after = process.memory_info().rss
    ram_delta_mb = (ram_after - ram_before) / (1024 * 1024)
    tokens_per_second = tokens / total_time if total_time > 0 else 0.0
    return BenchmarkResult(
        index=prompt_case.index,
        category=prompt_case.category,
        prompt_preview=_preview(prompt_case.prompt),
        tokens=tokens,
        tokens_per_second=tokens_per_second,
        time_to_first_token=time_to_first_token,
        total_time=total_time,
        ram_delta_mb=ram_delta_mb,
        response_preview=_preview(response_text, limit=80),
    )


def _preview(text: str, limit: int = 60) -> str:
    single_line = " ".join(text.split())
    if len(single_line) <= limit:
        return single_line
    return single_line[: limit - 3] + "..."


def _render_results(results: Iterable[BenchmarkResult], model: str) -> None:
    table = Table(title=f"Ollama Benchmark Results: {model}", show_lines=False)
    table.add_column("#", style="dim", justify="right")
    table.add_column("Category", style="cyan")
    table.add_column("Prompt", overflow="fold")
    table.add_column("Tok/s", justify="right")
    table.add_column("TTFT", justify="right")
    table.add_column("Total", justify="right")
    table.add_column("RAM Δ", justify="right")
    table.add_column("Tokens", justify="right")

    for result in results:
        speed_style = "green" if result.tokens_per_second >= 20 else "yellow" if result.tokens_per_second >= 8 else "red"
        table.add_row(
            str(result.index),
            result.category,
            result.prompt_preview,
            f"[{speed_style}]{result.tokens_per_second:.2f}[/{speed_style}]",
            f"{result.time_to_first_token:.2f}s",
            f"{result.total_time:.2f}s",
            f"{result.ram_delta_mb:+.1f} MB",
            str(result.tokens),
        )
    console.print(table)


def _write_csv(results: Iterable[BenchmarkResult], output_path: Path) -> None:
    fieldnames = [
        "index",
        "category",
        "prompt_preview",
        "tokens",
        "tokens_per_second",
        "time_to_first_token",
        "total_time",
        "ram_delta_mb",
        "response_preview",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            writer.writerow(
                {
                    "index": result.index,
                    "category": result.category,
                    "prompt_preview": result.prompt_preview,
                    "tokens": result.tokens,
                    "tokens_per_second": f"{result.tokens_per_second:.4f}",
                    "time_to_first_token": f"{result.time_to_first_token:.4f}",
                    "total_time": f"{result.total_time:.4f}",
                    "ram_delta_mb": f"{result.ram_delta_mb:.4f}",
                    "response_preview": result.response_preview,
                }
            )


def _print_summary(results: list[BenchmarkResult]) -> None:
    if not results:
        return
    avg_tps = sum(item.tokens_per_second for item in results) / len(results)
    avg_ttft = sum(item.time_to_first_token for item in results) / len(results)
    avg_total = sum(item.total_time for item in results) / len(results)
    console.print(
        f"[bold]Averages[/bold]  [green]{avg_tps:.2f} tok/s[/green]  "
        f"[cyan]{avg_ttft:.2f}s TTFT[/cyan]  [magenta]{avg_total:.2f}s total[/magenta]"
    )


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--model", "-m", required=True, help="Installed Ollama model name, e.g. llama3.2:3b")
@click.option(
    "--prompts",
    "-p",
    "prompts_path",
    type=str,
    default=None,
    help="Optional .txt, .md, .json, or .jsonl prompt file.",
)
@click.option("--output", "-o", "output_path", type=str, default=None, help="Optional CSV export path.")
def cli(model: str, prompts_path: str | None, output_path: str | None) -> None:
    """Benchmark local Ollama models from your terminal."""
    try:
        load_dotenv()
        validated_model = _validate_model_name(model)
        prompts = _get_prompt_cases(prompts_path)
        output = _validate_output_path(output_path)
        host = _get_ollama_host()
        timeout = _parse_positive_int_env("OLLAMA_REQUEST_TIMEOUT", default=120, minimum=5, maximum=900)

        console.print(f"[bold]Benchmarking[/bold] [cyan]{validated_model}[/cyan] at [dim]{host}[/dim]")
        console.print(f"[dim]Running {len(prompts)} prompt(s).[/dim]")

        results: list[BenchmarkResult] = []
        with httpx.Client() as client:
            _ensure_ollama_ready(client, host, validated_model)
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("{task.completed}/{task.total}"),
                TimeElapsedColumn(),
                console=console,
            ) as progress:
                task = progress.add_task("Running benchmark prompts", total=len(prompts))
                for prompt_case in prompts:
                    results.append(_benchmark_prompt(client, host, validated_model, prompt_case, timeout))
                    progress.advance(task)

        _render_results(results, validated_model)
        _print_summary(results)
        if output is not None:
            _write_csv(results, output)
            console.print(f"[green]CSV written to:[/green] {output}")

    except OSError:
        error_console.print("[red]Error:[/red] File operation failed. Check the path and permissions.")
        raise click.exceptions.Exit(code=1) from None
    except (BenchmarkError, httpx.HTTPStatusError, httpx.TimeoutException, httpx.RequestError, json.JSONDecodeError) as exc:
        error_console.print(f"[red]Error:[/red] {str(exc)}")
        raise click.exceptions.Exit(code=1) from None
