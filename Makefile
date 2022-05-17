all: pre-commit lint mypy tests docs

pre-commit:
	pre-commit run --all-files

lint:
	flake8 meshinfo tests

mypy:
	mypy meshinfo

tests:
	pytest --cov=meshinfo --cov-report html --cov-report term

docs:
	sphinx-build -W --keep-going -b html docs docs/_build/html

make-migration:
	alembic revision --autogenerate

migrate-db:
	alembic upgrade head

.PHONY: all docs pre-commit lint mypy tests
