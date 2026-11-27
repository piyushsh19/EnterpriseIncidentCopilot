.PHONY: install check seed ask run test e2e docker-up docker-seed docker-restart docker-logs docker-down

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

e2e:
	E2E_BASE_URL=http://localhost:8000 .venv/bin/pytest tests/e2e -v

docker-up:
	docker compose up --build -d

docker-seed:
	docker compose exec copilot python scripts/seed_ingest.py

docker-restart:
	docker compose restart

docker-logs:
	docker compose logs -f

docker-down:
	docker compose down
