default: pre-commit fix mypy tests docs

pre-commit:
	uvx pre-commit run --all-files

fmt:
  uv run ruff format .

fix: fmt
	uv run ruff check . --fix

mypy:
	uv run mypy meshinfo

tests:
	uv run pytest --cov=meshinfo --cov-report html --cov-report term

docs:
	uv run sphinx-build -W --keep-going -b html docs docs/_build/html

make-migration:
	uv run alembic revision --autogenerate

migrate-db:
	uv run alembic upgrade head
