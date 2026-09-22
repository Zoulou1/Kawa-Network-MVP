# ADR-001: Queue plot risk checks and paginate the station feed

**Status:** Accepted for Formative 1  
**Date:** 2026-09-17

## Context

The pilot station needs to record a farmer's delivery quickly on a phone and a slow connection. At the same time, the external land-risk registry can take between two and forty seconds to answer and can be unavailable for hours. Waiting for that service inside `POST /api/plots/` would make registration unreliable and would make it harder to add a delivery workflow later.

The API also needs to preserve the provenance chain. A delivery points to a plot, the plot points to a farmer and a washing station, and the plot stores its administrative sector. These relationships are more important than making a large number of endpoints for this first increment.

## Decision

The MVP uses a small Django REST Framework API with SQLite for local development. A plot registration creates the plot and a `RiskCheckAttempt` row in one database transaction. The HTTP request does not call the external registry. A separate `process_risk_checks` management command acts as the queue worker and processes queued attempts. The worker records `queued`, `running`, `succeeded`, or `failed` states, timestamps, errors, and an external reference when available.

A delivery is allowed even when a plot is queued, failed, or flagged. The delivery still records the plot and station, so traceability and same-day payment do not stop because a third-party registry is down. A flagged plot is accepted for this MVP but is visible through its risk status and should be reviewed before later compliance decisions. Formative 2 can add permissions and a policy that blocks settlement if that is required.

The selected performance feature is page-number pagination on the station delivery feed. The default page is 25 deliveries and the client can request up to 100. This choice addresses Emmanuel's concrete 2G and harvest-peak problem directly. Price schedule remains a small configured endpoint in this increment rather than adding cache invalidation that is not needed by the brief.

## Consequences

This improves non-blocking behaviour, traceability, and feed response size. It also gives developers evidence of every risk-check attempt instead of hiding failures in a log file. The design is simple to run locally because it does not require Redis for the formative.

The trade-off is that the database-backed worker is less powerful than a production queue such as Celery with Redis. It needs a separate process, and two workers would need a later claim/locking improvement to prevent duplicate work. The local registry response is deterministic when `RISK_REGISTRY_URL` is empty; a real deployment must configure the external URL and add authentication, retry limits, and monitoring.

If the registry never succeeds, the plot remains `failed` and its attempts contain the error. Deliveries can still be recorded, because stopping the scale would harm Jeanne's same-day payment and Emmanuel's workflow. Patrick's compliance path is protected by keeping the risk status and provenance visible for later review.

## Stakeholder and quality impact

Emmanuel benefits most from the paginated feed and the non-blocking registration path. Jeanne benefits from deliveries not being blocked by an unavailable registry. Patrick benefits from the explicit provenance chain and recorded risk history. The main non-functional requirement is responsiveness under slow connectivity; reliability and observability are supporting requirements.

The choice makes immediate compliance enforcement harder because the API intentionally accepts a delivery before a successful risk result. That is an explicit product trade-off, not an assumption that the external registry is always available.
