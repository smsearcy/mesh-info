all: format lint mypy tests

format:
	pre-commit run --all-files

lint:
	poetry run flake8

mypy:
	poetry run mypy pymeshmap

tests:
	poetry run pytest --cov=pymeshmap --cov-report html --cov-report term

make-migration:
	poetry run alembic revision --autogenerate

migrate-db:
	poetry run alembic upgrade head

.PHONY: all format lint mypy tests
