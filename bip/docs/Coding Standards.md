# Coding Standards

## General

- Keep BIP isolated under `bip/`.
- Prefer explicit module boundaries over cross-folder imports.
- Use type annotations for public functions and contracts.
- Do not couple Phase 0 modules to BDR Dashboard, BIC Collector, or PostgreSQL.

## Frontend

- Use React function components for UI composition.
- Keep pages free of business logic.
- Use React Router for route ownership.
- Use TanStack Query only for future server-state boundaries.
- Use Zustand only for shell and UI state in Phase 0.
- Keep design-system exports reusable and feature-neutral.

## Backend

- Use the FastAPI application factory.
- Register routers centrally.
- Keep settings in `core/config.py`.
- Keep middleware and exception registration isolated.
- Do not add SQL, database connections, or services in Phase 0.

## Contracts

- Shared API shapes belong in `shared/contracts`.
- API responses should remain Pydantic-modeled on the backend and TypeScript-modeled on the frontend.
