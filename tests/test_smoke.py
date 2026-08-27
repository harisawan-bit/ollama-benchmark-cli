"""Smoke tests that do NOT require a live Ollama server."""

from click.testing import CliRunner

import cli
import benchmarks


def test_imports_ok():
    assert cli is not None
    assert benchmarks is not None
    assert hasattr(cli, "cli")


def test_cli_help_exits_zero():
    runner = CliRunner()
    result = runner.invoke(cli.cli, ["--help"])
    assert result.exit_code == 0
    assert "Benchmark local Ollama models" in result.output


def test_default_prompts_non_empty():
    prompts = benchmarks.get_default_prompts()
    assert isinstance(prompts, list)
    assert len(prompts) > 0
    for item in prompts:
        assert "category" in item
        assert "prompt" in item
