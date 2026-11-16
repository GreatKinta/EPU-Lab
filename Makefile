.PHONY: start check doctor
start:
	./scripts/start.sh

doctor:
	python3 scripts/check_environment.py

check:
	backend/.venv/bin/ruff check backend scripts
	python3 scripts/backend.py --test-db pytest -q
	npm --prefix frontend test
	npm --prefix frontend run build
	npm --prefix blockchain test
