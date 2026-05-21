PYTHON ?= python3.11
UV_INDEX_URL ?= https://pypi.tuna.tsinghua.edu.cn/simple

.PHONY: venv deps test lint typecheck check clean

venv:
	uv venv --python $(PYTHON) .venv

deps: venv
	UV_INDEX_URL=$(UV_INDEX_URL) uv pip install --python .venv/bin/python -e . --group dev

test: deps
	.venv/bin/python -m pytest

lint: deps
	.venv/bin/ruff check .

typecheck: deps
	.venv/bin/mypy .

check: lint typecheck test

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache
