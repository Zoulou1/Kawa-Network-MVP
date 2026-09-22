# Kawa Network MVP

This repository contains the Formative 1 increment for Kawa Network. It is a small Django REST API for registering farmers and plots, recording cherry deliveries, showing a washing-station feed, and recording queued land-risk checks.

The `f1` Git tag is the intended Formative 1 submission point.

## Technology stack

The project uses Python 3.11 or newer, Django, Django REST Framework, and SQLite for local development. The risk worker uses a database-backed queue and a Django management command, so Redis is not required for this formative.

## Quick start

```bash
git clone <repository-url>
cd kawa-network-mvp
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # optional; the default values run locally
python manage.py migrate
python manage.py test
python manage.py runserver
```

The API will be available at `http://127.0.0.1:8000`.

In another terminal, with the virtual environment active, start the background worker:

```bash
python manage.py process_risk_checks
```

For a one-off local check, use `python manage.py process_risk_checks --once`.

## Environment variables

`DJANGO_SECRET_KEY` sets the Django secret key. `DJANGO_DEBUG` controls debug mode. `ALLOWED_HOSTS` is a comma-separated list. `RISK_REGISTRY_URL` optionally points to a compatible external registry endpoint. If it is empty, the worker uses a clearly marked local demo response so the project is runnable without an external service. `RISK_WORKER_POLL_SECONDS` controls how often the worker checks for queued work.

## Main API endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET`, `POST` | `/api/farmers/` | List or register farmers |
| `GET`, `POST` | `/api/stations/` | List or register washing stations |
| `GET`, `POST` | `/api/plots/` | List or register plots |
| `GET` | `/api/plots/{id}/risk-checks/` | See recorded risk-check attempts |
| `GET`, `POST` | `/api/deliveries/` | List or record deliveries |
| `GET` | `/api/stations/{code}/deliveries/` | Paginated station delivery feed |
| `GET` | `/api/price-schedule/` | Current configured price schedule |

The full OpenAPI artifact is in [`docs/openapi.yaml`](docs/openapi.yaml).

## Example requests

Register a farmer:

```bash
curl -X POST http://127.0.0.1:8000/api/farmers/ \
  -H 'Content-Type: application/json' \
  -d '{"national_id":"RW1234567","full_name":"Aline Mukamana","phone_number":"+250788123456"}'
```

Register a station and a plot. The plot response has `risk_status: "queued"` and a `latest_risk_attempt` object. The request does not wait for the external registry.

```bash
curl -X POST http://127.0.0.1:8000/api/plots/ \
  -H 'Content-Type: application/json' \
  -d '{"plot_code":"PLOT-001","farmer":1,"administrative_sector":"Mbuye","washing_station":1,"area_hectares":"1.25","latitude":-2.45,"longitude":29.65}'
```

Record a delivery. The washing station must match the plot's registered station.

```bash
curl -X POST http://127.0.0.1:8000/api/deliveries/ \
  -H 'Content-Type: application/json' \
  -d '{"plot":1,"washing_station":1,"delivery_date":"2026-09-17","weight_kg":"12.50","cherry_grade":"A","recorded_by":"Emmanuel"}'
```

Read the station feed with pagination:

```bash
curl 'http://127.0.0.1:8000/api/stations/NYA-01/deliveries/?page=1&page_size=25'
```

Validation errors use this shape:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Validation failed.",
    "fields": {"delivery_date": ["delivery_date cannot be in the future."]}
  }
}
```

## Async workflow

`POST /api/plots/` creates a `RiskCheckAttempt` with status `queued` in the same transaction as the plot. The API does not call the slow registry. The worker claims the work by changing the attempt to `running`, calls the configured registry, and records `succeeded` or `failed` with timestamps and an error message. Use `GET /api/plots/{id}/risk-checks/` to inspect the evidence. The policy and failure trade-off are documented in [`ADR.md`](ADR.md).

## Performance approach

The chosen performance feature is page-number pagination on the station delivery feed. The default page contains 25 rows and the client can request up to 100 rows. This keeps responses smaller for Emmanuel's 2G phone and is directly related to the expected harvest peak. The price schedule endpoint is included as required but is not cached in this increment.

## Project structure

`kawa/` contains Django settings and URL configuration. `api/models.py` contains the provenance and workflow data model. `api/serializers.py` contains input validation and response shapes. `api/views.py` contains the API endpoints. `api/tasks.py` and `api/management/commands/process_risk_checks.py` contain the queued risk workflow. `docs/openapi.yaml` is the API documentation artifact.

## Tests

The test suite covers farmer registration, plot creation, queued risk evidence, the worker, delivery validation, station-feed pagination, future dates, and the price schedule.

```bash
python manage.py test
```

## Development history and milestone

The repository is intended to be developed on `main` with meaningful commits. Before submission, verify the milestone locally with:

```bash
git log --oneline --decorate -8
git tag f1
```

If a remote is configured, push the branch and tag with `git push origin main` and `git push origin f1`.

## AI-use annex

AI assistance was used to help plan the API structure, draft some implementation and documentation text, and review the assignment checklist. The project was then assembled and checked locally with Django migrations and tests. The final author remains responsible for understanding, reviewing, and explaining the code.
