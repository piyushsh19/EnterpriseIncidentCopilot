.PHONY: install check seed ask run test docker-up docker-down

PYTHON ?= python3.12

install:
	$(PYTHON) -m venv .venv && .venv/bin/pip install -r requirements.txt

check:
	.venv/bin/python scripts/check_setup.py

seed:
	.venv/bin/python scripts/seed_ingest.py

ask:
	.venv/bin/python scripts/ask.py INC-cli "RDS CPU at 98%, queries slow"

run:
	.venv/bin/uvicorn app.main:app --reload --port 8000

test:
	.venv/bin/pytest -q

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down
