all: lint pre-commit mypy tests docs

pre-commit:
	pdm run pre-commit run --all-files

lint:
	pdm run ruff format .
	pdm run ruff check . --fix

mypy:
	pdm run mypy meshinfo

tests:
	pdm run pytest --cov=meshinfo --cov-report html --cov-report term

docs:
	pdm run sphinx-build -W --keep-going -b html docs docs/_build/html

make-migration:
	pdm run alembic revision --autogenerate

migrate-db:
	pdm run alembic upgrade head

.PHONY: all docs pre-commit lint make-migration migrate-db mypy tests
