# Battery Intelligence Platform Architecture

## Phase 0 Boundary

Phase 0 establishes a standalone application foundation. It does not implement AI, analytics, reporting, database access, collector integration, dashboard integration, charts, widgets, or business logic.

## System Shape

The repository uses a separated application structure:

- `apps/web` contains the React client shell.
- `apps/api` contains the FastAPI API shell.
- `shared/contracts` contains cross-boundary contract definitions.
- `docs` records operating and design guidance.
- `scripts` contains project automation.

## Frontend Decisions

React Router owns navigation and route composition. All listed routes resolve to placeholder pages so URL design can stabilize before feature implementation.

TanStack Query is installed and configured at the provider layer for future server-state management. No feature queries are implemented.

Zustand owns local shell state: theme, layout, and notifications. The stores intentionally avoid business state.

The design-system folder exports named component placeholders. This reserves module boundaries for reusable UI without prematurely implementing real components.

The authentication feature contains only a port and null adapter. This provides a replaceable authentication boundary without creating authentication behavior.

## Backend Decisions

FastAPI is composed through an application factory. Settings, logging, middleware, exception handling, dependencies, router registration, database boundaries, and repositories are separated into dedicated modules.

The API currently exposes only `GET /api/health`. The route is version-ready through `app/api/v1` while preserving the required public path.

Database and repository files are abstraction boundaries only. They intentionally contain no engine setup, SQL, queries, services, or database access.
