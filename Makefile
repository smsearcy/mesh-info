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

requirements:
	pip-compile -o requirements.txt pyproject.toml
	pip-compile --extra dev --resolver backtracking -o dev-requirements.txt pyproject.toml

update-deps:
	pre-commit autoupdate
	pip install --upgrade pip-tools pip wheel
	pip-compile --upgrade --resolver backtracking -o requirements.txt pyproject.toml
	pip-compile --extra dev --upgrade --resolver backtracking -o dev-requirements.txt pyproject.toml

init:
	pip install --upgrade pip wheel
	pip install --upgrade -r requirements.txt -r dev-requirements.txt -e .
	pip check

update: update-deps init

.PHONY: all docs pre-commit lint make-migration migrate-db mypy requirements tests update-deps init update
