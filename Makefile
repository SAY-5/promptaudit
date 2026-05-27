.PHONY: install lint typecheck test cov fmt fmt-check bench bench-regress action-self-test clean

install:
	pip install -e ".[dev]"

fmt:
	black src tests
	ruff check --fix src tests

fmt-check:
	black --check src tests
	ruff check src tests

lint: fmt-check

typecheck:
	mypy

test:
	pytest

cov:
	pytest --cov --cov-report=term-missing --cov-fail-under=85

bench:
	python -m promptaudit.bench

bench-regress:
	python -m promptaudit.bench --regress 30

action-self-test:
	promptaudit run --provider fake --baseline baselines/model_v1.json --report-dir /tmp/pa-report --battery batteries/jailbreaks.yaml --taxonomy batteries/harm_taxonomy.yaml --evalset evalsets/quality_v1.jsonl

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage dist build
	find . -type d -name __pycache__ -exec rm -rf {} +
