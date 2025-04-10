default: pre-commit fix mypy tests docs

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

# Run test suite
tests:
	uv run pytest --cov=meshinfo --cov-report html --cov-report term

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
