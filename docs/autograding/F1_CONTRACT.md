# F1 Contract Coverage

This project implements the minimum Formative 1 contract in a runnable Django REST API.

- Farmer registration: `POST /api/farmers/`
- Plot registration and listing: `POST, GET /api/plots/`
- Delivery recording: `POST /api/deliveries/`
- Station feed: `GET /api/stations/{station_code}/deliveries/`
- Price schedule: `GET /api/price-schedule/`
- Queued risk-check evidence: `GET /api/plots/{plot_id}/risk-checks/`
- Performance feature: page-number pagination on the station feed
- Documentation: `README.md`, `ADR.md`, and `docs/openapi.yaml`
