"""Built-in benchmark prompts for ollama-benchmark-cli."""

DEFAULT_PROMPTS = [
    {
        "category": "math reasoning",
        "prompt": (
            "A train travels 180 km in 2 hours, then 120 km in 1.5 hours. "
            "What is its average speed for the whole trip? Show the formula."
        ),
    },
    {
        "category": "math reasoning",
        "prompt": (
            "Solve this step by step: If 3x + 7 = 31 and y = x^2 - 4, "
            "what are x and y?"
        ),
    },
    {
        "category": "coding",
        "prompt": (
            "Write a Python function named is_palindrome that ignores spaces, "
            "punctuation, and capitalization. Include two short tests."
        ),
    },
    {
        "category": "coding",
        "prompt": (
            "Explain why parameterized SQL queries prevent SQL injection, "
            "then show a safe Python sqlite3 example."
        ),
    },
    {
        "category": "summarization",
        "prompt": (
            "Summarize in three bullet points: Local AI models can run without "
            "sending data to a cloud provider. This can improve privacy and "
            "latency, but users still need enough RAM, disk space, and compute. "
            "Benchmarking helps compare speed and quality across models."
        ),
    },
    {
        "category": "summarization",
        "prompt": (
            "Turn this into a one-paragraph executive summary: The team tested "
            "three local language models on coding, reasoning, summarization, "
            "and writing prompts. Model A was fastest, Model B was most accurate, "
            "and Model C used the least memory."
        ),
    },
    {
        "category": "creative writing",
        "prompt": (
            "Write a vivid but concise opening paragraph for a science-fiction "
            "story about a medical student discovering an offline AI in an old lab."
        ),
    },
    {
        "category": "creative writing",
        "prompt": (
            "Create five punchy product names for a desktop app that benchmarks "
            "local AI models."
        ),
    },
    {
        "category": "factual recall",
        "prompt": (
            "What is the capital of Japan, and what is one historically important "
            "district in that city?"
        ),
    },
    {
        "category": "factual recall",
        "prompt": (
            "Name the four bases found in DNA and briefly state how they pair."
        ),
    },
]


def get_default_prompts() -> list[dict[str, str]]:
    """Return a copy of the built-in prompt set."""
    return [prompt.copy() for prompt in DEFAULT_PROMPTS]
