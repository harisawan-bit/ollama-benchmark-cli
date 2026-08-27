# Contributing to ollama-benchmark-cli

Thanks for helping improve the project! This guide covers local setup and how to open a pull request.

## Development setup

You need Python 3.10 or newer and Git.

```bash
# Clone your fork
git clone https://github.com/harisawan-bit/ollama-benchmark-cli.git
cd ollama-benchmark-cli

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Install the project in editable mode
pip install -e .

# Install the test runner
pip install pytest
```

## Running

```bash
# Show the CLI help (no Ollama server required)
ollama-benchmark --help
python main.py --help

# Run the smoke tests (no live Ollama required)
pytest -q
```

To run a real benchmark you also need a local Ollama instance with at least one
model pulled:

```bash
ollama pull llama3.2:3b
ollama-benchmark --model llama3.2:3b
```

## Environment configuration

Copy the example file to create your local `.env`:

```bash
cp .env.example .env          # Windows: copy .env.example .env
```

Never commit a real `.env` file. The placeholder `OLLAMA_API_KEY` is safe to keep.

## Opening a pull request

1. Create a feature branch from `main`:
   ```bash
   git checkout -b feat/your-change main
   ```
2. Make your change and add tests where it makes sense.
3. Run `pytest -q` and `ollama-benchmark --help` locally so they pass.
4. Commit and push the branch to your fork.
5. Open a pull request against `main` and describe what you changed and why.

CI runs a smoke test on Python 3.10, 3.11, and 3.12. A PR can only be merged
when all checks are green.
