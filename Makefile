all: format lint mypy tests

format:
	pre-commit run --all-files

lint:
	poetry run flake8

mypy:
	poetry run mypy pymeshmap

tests:
	poetry run pytest

.PHONY: all format lint mypy tests
