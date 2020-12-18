all: format lint tests

format:
	pre-commit run --all-files

lint:
	poetry run flake8

tests:
	poetry run pytest

.PHONY: all format lint tests
