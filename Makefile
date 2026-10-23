VENV ?= .venv
PY   := $(VENV)/bin/python
PYTEST := $(VENV)/bin/pytest
WORKERS ?= auto

.PHONY: install lint test test-api test-smoke test-ui test-unit triage report run stage-up stage-down stage-test clean

install:  ## create venv, install deps and the Chromium browser
	python3.12 -m venv $(VENV)
	$(VENV)/bin/pip install -r requirements.txt
	$(VENV)/bin/playwright install chromium

lint:  ## static checks
	$(VENV)/bin/ruff check .

test:  ## everything, in parallel
	$(PYTEST) -n $(WORKERS)

test-api:
	$(PYTEST) -n $(WORKERS) -m api

test-ui:
	$(PYTEST) -n $(WORKERS) -m ui

test-unit:
	$(PYTEST) -n0 -m unit

test-smoke:  ## critical path only, run on every commit
	$(PYTEST) -n $(WORKERS) -m smoke

triage:  ## cluster the failures of the last run
	$(PY) -m triage reports/junit.xml

report:  ## open the HTML report of the last run
	open reports/report.html 2>/dev/null || xdg-open reports/report.html

run:  ## start the app locally on :8000 (SQLite)
	$(VENV)/bin/uvicorn app.main:app_factory --factory --reload

stage-up:  ## production-like stage: app + PostgreSQL in Docker (needs a .env, see .env.example)
	docker compose -f docker-compose.stage.yml up --build -d --wait

stage-down:
	docker compose -f docker-compose.stage.yml down -v

stage-test:  ## run the suite against the running stage (no local server is started)
	set -a; . ./.env; set +a; BASE_URL=http://localhost:8000 $(PYTEST) -n $(WORKERS)

clean:
	rm -rf reports/* .pytest_cache .ruff_cache
	touch reports/.gitkeep
