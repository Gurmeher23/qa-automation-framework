# qa-automation-framework

A Playwright + pytest test-automation framework for UI and API testing, built around a small but realistic web application ("Order Desk"). It shows how to build QA from zero: a test strategy, a production-like stage environment, deterministic test data, parallel runs, CI pipelines for GitHub and GitLab, and a tool that groups failures by similar stack trace so a red pipeline can be read in a minute.

The application is the vehicle; the framework is the point. Everything in `tests/` and `triage/` is written to be reusable on a real product.

## What problem this solves in practice

When a team has little or no test automation, the usual blockers are not the test scripts themselves:

* there is no stable environment to test against (solved here with a Docker stage: the app image plus PostgreSQL),
* tests share data and break each other (solved with per-test users and API-based seeding),
* the suite is too slow or too flaky to trust (solved with a pyramid that keeps UI tests few, parallel workers, auto-waiting and no sleeps),
* nobody can tell why 30 tests are red (solved with evidence on failure plus failure triage).

## Architecture

```
                          +-----------------------------+
   pytest (xdist workers) |  tests/                     |
   -n auto                |   api/   httpx -------------+--+
                          |   ui/    Playwright (POM) --+  |   HTTP
                          |   unit/  triage tests       |  |
                          |   data/  factories + seed --+  |
                          |   conftest.py: live_server  |  |
                          +-------------+---------------+  |
                                        | starts per worker|
                                        v                  v
                          +-----------------------------------+
                          | app/  FastAPI "Order Desk"        |
                          |  routers/api.py   JSON /api/...   |
                          |  routers/web.py   Jinja2 HTML     |
                          |  services.py      business rules  |
                          |  SQLAlchemy  ---> SQLite (local)  |
                          |              ---> PostgreSQL      |
                          |                   (docker stage)  |
                          +-----------------------------------+

  reports/  report.html  junit.xml  playwright/<test>/{screenshot,trace.zip}
        |
        v
  triage/   parse JUnit -> normalise traces -> TF-IDF cosine clusters -> cause hint
            (optional LLM summary behind TRIAGE_LLM=1, offline by default)

  CI: .github/workflows/ci.yml  |  .gitlab-ci.yml  (lint -> api+unit -> ui -> artifacts)
```

### The application under test

* Login with a signed session cookie, HTML (Jinja2) and JSON (`/api/...`).
* Orders: create (optional `Idempotency-Key`), list with pagination and status filter, update. Rules: status moves only `new -> paid -> shipped` or `-> cancelled`; quantity is editable only while `new`; users see only their own orders.
* Admin: user provisioning API, order statistics, and an admin page with a client-side text and status filter.

### The framework

| Area | Where | Notes |
|---|---|---|
| Live server fixture | `tests/server.py`, `tests/conftest.py` | One uvicorn thread per xdist worker on a pre-bound free port, own SQLite file. `BASE_URL` points the suite at any deployment instead. |
| API tests | `tests/api/` | httpx against the live server: auth, CRUD, validation matrix, idempotency, pagination, ownership. |
| UI tests | `tests/ui/` | Playwright for Python with Page Objects in `tests/ui/pages/`. Arrange via API, drive only the screen under test. |
| Test data | `tests/data/` | Seeded RNG factories; API-based seeding; unique tokens for parallel safety. |
| Reporting | `reports/` | pytest-html, JUnit XML, screenshot + trace on UI failure. |
| Triage | `triage/` | Offline failure clustering, optional LLM summary. |

## Test strategy (summary)

Full text: [docs/TEST_STRATEGY.md](docs/TEST_STRATEGY.md).

* **Pyramid:** many fast API tests, a few UI journeys, unit tests for the tooling.
* **Smoke** (13 tests, about 3 seconds locally): the critical path; runs on every push and merge request. **Regression:** everything; runs on pull requests and nightly.
* **Flakiness policy:** no sleeps, no blanket retries, a flaky test is fixed or quarantined within a week.
* **Data strategy:** each test provisions its own user, so parallel runs never share mutable state; seeding goes through the public API so the same code works on any environment.

## How to run

Requirements: Python 3.12.

```bash
make install        # venv, dependencies, Chromium
make test           # everything, parallel (pytest -n auto)
make test-smoke     # critical path only
make test-api       # API tests
make test-ui        # browser tests (headless)
make test-unit      # triage tool tests
make lint           # ruff
make triage         # cluster the failures of the last run
make report         # open reports/report.html
```

Debugging a UI test with a visible browser: `.venv/bin/pytest tests/ui -n0 --headed --slowmo 300 -k login`.

Opening a failure trace: `.venv/bin/playwright show-trace reports/playwright/<test>/trace.zip`.

### Production-like stage (Docker Compose, PostgreSQL)

```bash
cp .env.example .env     # then change the passwords
make stage-up            # builds the image, starts app + PostgreSQL, waits for healthy
make stage-test          # runs the same suite against http://localhost:8000
make stage-down
```

### Failure triage

```bash
python -m triage reports/junit.xml
```

Optional LLM summary (any OpenAI-compatible endpoint). Without these variables, or on any network error, the offline rules are used:

```bash
TRIAGE_LLM=1 OPENAI_API_KEY=... [OPENAI_BASE_URL=...] [TRIAGE_LLM_MODEL=...] python -m triage reports/junit.xml
```

Example output on the fixture report used by the unit tests (`tests/unit/fixtures/sample_junit.xml`, hand-written, 7 failures):

```
7 failing test(s) in 4 group(s)

[1] 3 test(s): playwright._impl._errors.TimeoutError: Locator.click: Timeout Nms exceeded.
    Likely cause: A UI element did not appear or change in time. ... Most common location: .../orders_page.py:48. Affects 3 test(s).
[2] 2 test(s): assert N == N
    Likely cause: Authentication or authorisation failed. ... Affects 2 test(s).
[3] 1 test(s): KeyError: '<str>'
[4] 1 test(s): httpx.ConnectError: [Errno N] Connection refused
```

How clustering works: failure message and traceback are normalised (addresses, UUIDs, paths, numbers, quoted literals masked), turned into TF-IDF vectors, and greedily grouped when cosine similarity is at least 0.8. No external service is involved.

## Actual test results

Run on a MacBook (10 cores), Python 3.12.10, headless Chromium, `pytest -n auto`:

```
$ make test
102 passed in 6.42s        (three consecutive runs: 6.42s, 5.09s, 7.24s, 102 passed each time)

$ make test-smoke          13 passed in 2.63s
$ make test-api            60 passed in 2.08s
$ make test-ui             23 passed in 5.50s
$ make test-unit           19 passed in 1.55s
```

Counts per layer: 60 API, 23 UI, 19 unit. `make lint`: ruff reports no issues. The numbers are from my machine; CI runners are slower, so expect larger wall-clock times there.

## Limitations (honest)

* The application is small and written by me for this purpose. It demonstrates test engineering, not domain depth in any specific product.
* UI tests run on Chromium only; there is no cross-browser or mobile matrix.
* The Docker stage (`docker-compose.stage.yml`) and the GitLab pipeline are written but I did not execute them in this environment (no Docker daemon was running; no GitLab runner). The GitHub workflow runs on every push; check the Actions tab for its status. Locally the suite runs on SQLite, so PostgreSQL-specific behaviour is only covered once `make stage-test` is run.
* Not covered: performance/load, accessibility, visual regression, security testing, contract testing. The app has no CSRF protection and uses a development secret by default; it is a test target, not a template for production code.
* The triage tool is a heuristic. Clustering on text similarity can merge distinct problems that fail with the same message, and the offline cause hints are keyword rules, not diagnosis. Its unit tests use a hand-written fixture report, not data from a real incident.
* No flaky-test history is stored between runs; the flakiness policy is a process, and tooling for it (quarantine job, trend dashboard) is not implemented.

## Repository layout

```
app/            FastAPI application under test (routers, services, models, templates)
tests/api/      API tests            tests/ui/   Playwright tests + pages/
tests/data/     factories and seeding  tests/unit/ tests for the triage tool
triage/         failure clustering and summaries
docs/           TEST_STRATEGY.md
Dockerfile, docker-compose.stage.yml, Makefile, .github/workflows/ci.yml, .gitlab-ci.yml
```
