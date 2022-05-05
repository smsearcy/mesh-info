all: format lint mypy tests

format:
	pre-commit run --all-files

lint:
	flake8 meshinfo tests

mypy:
	mypy meshinfo

tests:
	pytest --cov=meshinfo --cov-report html --cov-report term

make-migration:
	alembic revision --autogenerate

migrate-db:
	alembic upgrade head

.PHONY: all format lint mypy tests
