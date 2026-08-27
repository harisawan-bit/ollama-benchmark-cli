# ollama-benchmark-cli

![CI](https://github.com/harisawan-bit/ollama-benchmark-cli/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

`ollama-benchmark-cli` is a Python terminal tool for benchmarking local Ollama models with a standard prompt set. It streams responses from Ollama, measures speed, and prints a color-coded Rich table.

## Features

- Run 10 built-in benchmark prompts across math reasoning, coding, summarization, creative writing, and factual recall
- Use `--model` to benchmark any installed Ollama model
- Use `--prompts` for a custom `.txt`, `.md`, `.json`, or `.jsonl` prompt file
- Measure tokens/second, time to first token, total response time, and CLI RAM usage
- Show a Rich progress bar while prompts run
- Export benchmark results to CSV with `--output`
- Loads local config from `.env` with `python-dotenv`
- Includes `.env.example`, `.gitignore`, and `SECURITY.md`

## Requirements

- Python 3.10+
- Ollama installed and running locally
- At least one Ollama model pulled, for example:

```bash
ollama pull llama3.2:3b
```

## Install

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

On macOS or Linux, activate the environment with:

```bash
source .venv/bin/activate
```

## Configure

Copy the example environment file:

```bash
copy .env.example .env
```

On macOS or Linux:

```bash
cp .env.example .env
```

Default `.env` values:

```env
OLLAMA_HOST=http://127.0.0.1:11434
OLLAMA_REQUEST_TIMEOUT=120
OLLAMA_API_KEY=YOUR_API_KEY_HERE
```

Ollama does not need an API key for normal local use. Leave `OLLAMA_API_KEY` as the placeholder unless you later put Ollama behind a protected proxy.

## Usage

Run the built-in benchmark prompt set:

```bash
python main.py --model llama3.2:3b
```

Export results to CSV:

```bash
python main.py --model llama3.2:3b --output benchmark-results.csv
```

Use a custom prompt file:

```bash
python main.py --model llama3.2:3b --prompts prompts.txt
```

Text and Markdown prompt files can use one prompt per line, or separate multi-line prompts with a line containing at least three dashes:

```text
Explain TCP/IP in simple terms.
---
Write a Python function that validates email addresses.
```

JSON prompt file format:

```json
[
  {
    "category": "coding",
    "prompt": "Write a Python function that checks whether a number is prime."
  },
  {
    "category": "reasoning",
    "prompt": "If a clinic sees 24 patients in 3 hours, what is the average per hour?"
  }
]
```

JSONL prompt file format:

```jsonl
{"category":"coding","prompt":"Write a Python function that reverses a string."}
{"category":"summary","prompt":"Summarize why local AI benchmarking matters."}
```

## Sample Output Screenshot

```text
Benchmarking llama3.2:3b at http://127.0.0.1:11434
Running 10 prompt(s).
⠋ Running benchmark prompts ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 10/10 0:02:11

       Ollama Benchmark Results: llama3.2:3b
┏━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━┳━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━┓
┃ #  ┃ Category         ┃ Prompt                       ┃ Tok/s  ┃ TTFT  ┃ Total  ┃ RAM Δ    ┃ Tokens ┃
┣━━━━╋━━━━━━━━━━━━━━━━━━╋━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╋━━━━━━━━╋━━━━━━━╋━━━━━━━━╋━━━━━━━━━━╋━━━━━━━━┫
┃ 1  ┃ math reasoning   ┃ A train travels 180 km...    ┃ 31.42  ┃ 0.42s ┃ 4.02s  ┃ +1.2 MB  ┃ 126    ┃
┃ 2  ┃ math reasoning   ┃ Solve this step by step...   ┃ 29.88  ┃ 0.39s ┃ 3.51s  ┃ +0.4 MB  ┃ 105    ┃
┃ 3  ┃ coding           ┃ Write a Python function...    ┃ 24.16  ┃ 0.55s ┃ 6.79s  ┃ +0.8 MB  ┃ 164    ┃
┃ .. ┃ ...              ┃ ...                          ┃ ...    ┃ ...   ┃ ...    ┃ ...      ┃ ...    ┃
┗━━━━┻━━━━━━━━━━━━━━━━━━┻━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┻━━━━━━━━┻━━━━━━━┻━━━━━━━━┻━━━━━━━━━━┻━━━━━━━━┛
Averages  27.84 tok/s  0.48s TTFT  4.91s total
CSV written to: C:\path\to\benchmark-results.csv
```

## Security Notes

- Never commit real `.env` files or secrets.
- This CLI does not expose API endpoints, run SQL, accept uploads, use `eval()`, or perform web scraping.
- Inputs are length-limited and validated before being sent to Ollama or written to CSV.
- Errors are handled without printing stack traces or internal Python tracebacks.

## Development

This repository is already on GitHub, so you just clone and install — no `git init` needed.

```bash
git clone https://github.com/harisawan-bit/ollama-benchmark-cli.git
cd ollama-benchmark-cli
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e .
ollama-benchmark --help
```

Run the smoke tests (they do not need a live Ollama server):

```bash
pip install pytest
pytest -q
```

## Contributing

1. Create a feature branch from `main`:
   ```bash
   git checkout -b feat/your-change main
   ```
2. Make your change and add tests where it makes sense.
3. Run `pytest -q` and `ollama-benchmark --help` locally so they pass.
4. Push the branch and open a pull request against `main`.

CI runs a smoke test on Python 3.10, 3.11, and 3.12. A PR can only be merged when all checks are green. See [CONTRIBUTING.md](CONTRIBUTING.md) for full details.
