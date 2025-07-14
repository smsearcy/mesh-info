default: pre-commit fix mypy test-all docs

export SQLALCHEMY_WARN_20 := "1"
export PYTHONWARNINGS := "always::DeprecationWarning"

# Run pre-commit hooks
pre-commit:
	uvx pre-commit run --all-files

# Format with Ruff
fmt:
  uv run ruff format .

# Format and lint with Ruff
fix: fmt
	uv run ruff check . --fix

# Type checking with mypy
mypy:
	uv run mypy meshinfo

# Run entire test suite
test-all:
	uv run pytest --cov=meshinfo --cov-report html --cov-report term

# Run tests filtered via expression (pytest -k)
test expression:
  uv run pytest -k {{expression}}

# Generate docs
docs:
	uv run sphinx-build -W --keep-going -b html docs docs/_build/html

# Run collector and web service
run:
  uv run --script scripts/local_dev.py

# Create new database migration
make-migration:
	uv run alembic revision --autogenerate

# Apply database migrations
migrate-db:
	uv run alembic upgrade head
