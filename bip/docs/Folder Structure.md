# Folder Structure

## `bip/`

Standalone root for the Battery Intelligence Platform. This directory is independent from the existing BDR Dashboard and BIC Collector.

## `bip/apps/`

Application entry points. Each app owns its runtime, dependencies, and source tree.

## `bip/apps/web/`

React 18, TypeScript, and Vite web application. It renders only the enterprise shell and route placeholders.

## `bip/apps/web/src/app/`

Application composition: `App.tsx`, providers, and routing.

## `bip/apps/web/src/components/layout/`

Main shell, sidebar, header, and footer layouts. These files define navigation and platform chrome only.

## `bip/apps/web/src/components/design-system/`

Reusable UI component boundaries: Button, Card, Metric Card, Dialog, Drawer, Badge, Avatar, Tabs, Table, Empty State, Loading Skeleton, Error Boundary, Chart Container, Filters, and Search Input placeholders.

## `bip/apps/web/src/features/`

Future feature modules. Phase 0 includes only an authentication abstraction.

## `bip/apps/web/src/state/`

Zustand stores for theme, layout, and notifications. No business state is stored here.

## `bip/apps/web/src/lib/`

Infrastructure helpers such as the API client and utility functions.

## `bip/apps/api/`

FastAPI application shell.

## `bip/apps/api/app/api/`

Versioned API router composition. Phase 0 exposes only `/api/health`.

## `bip/apps/api/app/core/`

Configuration, logging, middleware, and exception infrastructure.

## `bip/apps/api/app/dependencies/`

Dependency injection boundaries for route handlers.

## `bip/apps/api/app/db/`

Database boundary placeholders. No database connections or SQL are implemented.

## `bip/apps/api/app/repositories/`

Read-only repository abstraction placeholders. No queries are implemented.

## `bip/shared/contracts/`

Type-safe API contract placeholders shared across web and API design.

## `bip/docs/`

Architecture, development, folder, and coding-standard documentation.

## `bip/scripts/`

Automation and verification scripts.
