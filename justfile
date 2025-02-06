test:
    uv run python3 -m unittest

format:
    uv run ruff format mcp_run tests examples

check:
    uv run ruff check mcp_run tests examples
