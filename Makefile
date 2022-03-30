all: format lint mypy tests

format:
	pre-commit run --all-files

lint:
	flake8 pymeshmap tests

mypy:
	mypy pymeshmap

tests:
	pytest --cov=pymeshmap --cov-report html --cov-report term

make-migration:
	alembic revision --autogenerate

migrate-db:
	alembic upgrade head

.PHONY: all format lint mypy tests
