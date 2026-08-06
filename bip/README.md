# Battery Intelligence Platform

Phase 0 creates only the application foundation for the Battery Intelligence Platform.

This project is intentionally separate from the existing BDR Dashboard and BIC Collector. No existing dashboard, collector, database, API, or integration code is modified by this foundation.

## Start

```bash
npm install
npm run dev:web
```

```bash
pip install -r apps/api/requirements.txt
npm run dev:api
```

## Scope

- React 18, TypeScript, Vite shell
- React Router route placeholders
- TanStack Query and Zustand provider architecture
- FastAPI application with `/api/health`
- Shared API contract placeholders
- Documentation for folders, decisions, standards, and development

Out of scope for Phase 0: AI, analytics, reports, charts, SQL, database queries, BIC integration, dashboard integration, and business logic.
