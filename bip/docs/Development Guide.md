# Development Guide

## Prerequisites

- Node.js 20 or newer
- Python 3.11 or newer

## Ports

| Service | URL |
| --- | --- |
| Web (Vite) | `http://127.0.0.1:3100` |
| API (Uvicorn) | `http://127.0.0.1:8100` |

The Vite dev server proxies every `/api` request to the API at `http://localhost:8100`. The proxy target is configurable through `VITE_BIP_API_PROXY_TARGET`.

## Environment

Create `.env` from `.env.example` when local overrides are needed. Mode-specific files `.env.development` and `.env.production` are loaded automatically by Vite.

## Install Frontend Dependencies

```bash
cd bip
npm install
```

## Start Web

```bash
cd bip
npm run dev:web
```

The web app runs on `http://127.0.0.1:3100`.

## Install API Dependencies

```bash
cd bip
python -m venv .venv
.venv\Scripts\activate
pip install -r apps/api/requirements.txt
```

## Start API

```bash
cd bip
npm run dev:api
```

The API runs on `http://127.0.0.1:8100`.

## Health Check

```bash
npm run health:api
```

Or directly:

```bash
curl http://127.0.0.1:8100/api/health
```

Expected response:

```json
{
  "status": "ok",
  "service": "Battery Intelligence Platform API"
}
```

Through the Vite proxy the same endpoint is available at:

```bash
curl http://127.0.0.1:3100/api/health
```

## Phase 2.5 Guardrails

Do not add business logic, analytics, reports, AI behavior, collector integration, dashboard integration, or database mutations during platform standardization.
