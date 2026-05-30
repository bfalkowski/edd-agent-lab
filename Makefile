.PHONY: test ci

test:
	uv run pytest -q

ci:
	uv run ruff check .
	uv run pytest -q
