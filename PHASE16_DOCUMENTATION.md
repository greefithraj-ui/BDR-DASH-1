# Phase 16: Comprehensive BDR Dashboard Documentation

## 1. Project Overview
- **Name**: BDR Dashboard
- **Purpose**: Real-time monitoring system for battery discharge rate testing across AQC hardware test rings
- **Tech Stack**: FastAPI (Python) backend, PostgreSQL database, vanilla JS frontend, Vite build, Tailwind CSS, PM2 process manager
- **Architecture**: Hybrid - main dashboard is monolithic vanilla JS (~6800 lines), React app exists but is commented out/disabled
- **Entry Point**: `index.html` → `app.js` (DOMContentLoaded → init())

## 2. File Structure & Purpose
```
app.js - Core dashboard logic (~6800 lines) - all rendering, data loading, polling, KPI calculations, charts, heatmap, floorplan, filters, state management
index.html - Main HTML template with all dashboard DOM structure, inline SVG icons, widget containers
index.css - All CSS styles including slot states, heatmap colors, layout, animations
src/App.jsx - React stub (returns null) - placeholder for future migration
src/main.jsx - React entry point (mounts to #react-root, commented out in HTML)
data/api.py - FastAPI backend with all API endpoints, SSE streaming, diagnostics routing
data/main.py - CLI/background service that downloads ring data from AQC machines via SSH
data/postgres_db.py - PostgreSQL connection pool, all DB queries, schema initialization, fallback queries
data/diagnostics.py - Remote SSH diagnostics (button scan, LED control, MCP repair, Bluetooth, motor status)
data/ring_status.py - Ring status upsert table schema and logic
machines.json - Machine registry (34 AQC machines with IP/user/removed_slots)
rings_config.json - Ring configuration data (900 lines, per-slot ring info)
serve-dist.js - Express production server serving dist/ and proxying /api/* to FastAPI
vite.config.ts - Vite build config with React plugin, Tailwind, API proxy
package.json - Dependencies and scripts
ecosystem.config.cjs - PM2 config for bdr-api service
.env - Environment config (PG credentials, API target, Gemini key)
data/archive.db - SQLite legacy archive database
```

## 3. Database Schema
### PostgreSQL (bdr_dashboard)
**Tables:**
1. `archive_entries` - Time-series snapshots (append-only)
   - id (serial primary key)
   - timestamp (timestamptz, indexed)
   - slots (jsonb) - array of slot data
   - rings (jsonb) - array of ring occupancy data
   - rings_config (jsonb)
   - summary (jsonb)
   - archive_type (text) - 'folder', 'session', 'manual'
   - session_id (uuid)
   
2. `ring_status` - Latest-state upsert table
   - id (serial primary key)
   - serial (text, unique per machine+slot)
   - machine (text)
   - slot (integer)
   - status (text) - 'PASSED', 'FAILED', 'RUNNING'
   - battery (float)
   - bdr (float)
   - workouts (integer)
   - last_update (timestamptz)
   
3. `machines` - Machine registry
   - name (text primary key)
   - ip (text)
   - user (text)
   - removed_slots (jsonb)
   - created_at (timestamptz)
   - updated_at (timestamptz)

4. `sessions` - Session tracking
   - id (uuid primary key)
   - machine (text)
   - started_at (timestamptz)
   - ended_at (timestamptz)

### SQLite (archive.db) - Legacy/fallback
   - archive table with similar structure but simpler schema

## 4. API Endpoints
**Base URL**: http://127.0.0.1:8000 (FastAPI)

**Data Endpoints:**
- GET `/api/bdr` - All machines BDR data
- GET `/api/bdr/{machine}` - Single machine BDR data
- GET `/api/rings` - All machines rings data
- GET `/api/rings/{machine}` - Single machine rings data
- GET `/api/archive` - Archive entries
- GET `/api/archive/dates` - Available archive dates
- POST `/api/archive/backfill` - Backfill archive
- GET `/api/search` - Search serials across machines
- GET `/api/search/{serial}` - Search specific serial
- GET `/api/machines` - List all machines
- GET `/api/rings_config` - Ring configuration
- GET `/api/health` - Health check

**Old Data Endpoints:**
- GET `/api/old-data/search/{serial}` - Search old data single serial
- POST `/api/old-data/search` - Search old data multiple serials

**Diagnostics Endpoints:**
- POST `/api/machine/{name}/diagnose/connect` - Connect to machine
- POST `/api/machine/{name}/diagnose/scan` - Quick scan
- POST `/api/machine/{name}/diagnose/scan/live` - Live scan
- GET `/api/machine/{name}/diagnose/logs` - Get logs
- POST `/api/machine/{name}/diagnose/led/{action}` - LED control
- POST `/api/machine/{name}/diagnose/bt/{action}` - Bluetooth control
- POST `/api/machine/{name}/diagnose/mcp/scan` - MCP scan
- POST `/api/machine/{name}/diagnose/mcp/repair` - MCP repair
- POST `/api/machine/{name}/diagnose/button/advanced-repair` - Button repair
- POST `/api/machine/{name}/diagnose/full` - Full diagnostics
- POST `/api/machine/{name}/diagnose/motor` - Motor check
- POST `/api/machine/{name}/diagnose/audit` - Audit
- POST `/api/machine/{name}/diagnose/troubleshoot/{fix}` - Troubleshooting
- POST `/api/machine/{name}/diagnose/kill-conflicts` - Kill conflicting processes
- POST `/api/machine/{name}/diagnose/bt/connection-check` - BT connection check
- POST `/api/machine/{name}/diagnose/bt/live-log` - BT live log stream
- POST `/api/machine/{name}/diagnose/bt/fix-crash-loop` - Fix BT crash loop
- POST `/api/machine/{name}/diagnose/bt/fix-pairing-popup` - Fix pairing popup
- POST `/api/machine/{name}/diagnose/bt/fix-pairing-popup-persistent` - Persistent pairing fix

**SSE Endpoint:**
- GET `/api/stream` - Server-Sent Events for real-time updates

## 5. State Management
### Global Variables
- `SESSION_DATA` - Current machine's raw data from API
- `ALL_MACHINE_DATA` - Object containing all machines' data
- `ALL_MACHINE_NAMES` - Array of all machine names
- `CURRENT_MACHINE` - Currently selected machine name
- `globalHeatmapData` - Array of heatmap cell objects (one per slot)
- `globalFwVersion` - Current firmware version string
- `chartA`, `chartB` - ApexCharts bar chart instances
- `detailLineChart` - ApexCharts detail line chart
- `currentSlotPanel` - Currently selected slot ID (or null)
- `ringsData` - Current machine's rings data
- `window.heatmapFilterActive` - Set of active health class filters
- `window.firmwareFilterActive` - Set of active firmware version filters
- `window.__isGraphLocked` - Boolean for graph freeze/unfreeze
- `window.__preservingUi` - Boolean for optimized DOM refresh
- `window.firmwareFilterActive` - Set for firmware filtering

### IndexedDB
- Used for caching data offline
- Persists across sessions

### LocalStorage
- Theme preference
- Custom floorplan machine-to-position assignments
- Heatmap color customizations

## 6. Business Logic
### BDR (Battery Discharge Rate) Calculation
- **Formula**: `bdr = drop / hours` where drop = battery % drop between cycle start points, hours = time elapsed
- **Workout Calculation**: 
  - From `bdr_data.cycles`: drop between consecutive cycle start percentages
  - From `bdr_state.completed_cycles`: count of completed charge/discharge cycles
  - Battery percentage normalization: 100% = full, 0% = empty

### Ring Status Logic
- **Status Classification**: 
  - RUNNING: Active test in progress
  - PASSED: Test completed successfully (battery reached threshold)
  - FAILED: Test failed (error condition)
- **Data Aggregation**: 
  - Per-slot: Individual battery/BDR readings
  - Per-machine: Aggregate statistics across all slots
  - Global: Cross-machine comparisons

### Archival System
- **Trigger**: Automatic on data change, manual via API
- **Storage**: Append-only time-series in PostgreSQL
- **Retention**: Configurable, with backfill capability for missing intervals
- **Query**: Time-range based with machine/slot filtering

### Diagnostics Engine
- **SSH Connection**: Direct to AQC machines (port 22)
- **Capabilities**: 
  - Button mapping verification
  - LED functionality test
  - MCP (Motor Control Panel) repair
  - Bluetooth pairing troubleshooting
  - Motor calibration
- **Logging**: All operations logged to machine-specific files

## 7. Frontend Architecture
### Component Structure
- **Monolithic Design**: Single `app.js` file handling all UI logic
- **Rendering Pipeline**:
  1. Data fetch from API (polling every 30s)
  2. State update (global variables)
  3. DOM manipulation (direct element updates)
  4. Chart refresh (ApexCharts instances)

### Key UI Modules
1. **Dashboard View**: KPI cards, machine selector, slot grid
2. **Heatmap View**: Color-coded battery/BDR visualization
3. **Floorplan View**: Physical layout representation
4. **Ring Slots View**: Detailed per-slot analysis
5. **Diagnostics Panel**: Machine-specific troubleshooting
6. **Serial Browser**: Search and filter across all machines

### Rendering Optimizations
- `__preservingUi` flag for batch DOM updates
- IndexedDB caching to reduce API calls
- Chart instance reuse (not recreation)
- Selective element updates vs full re-renders

### Chart Implementation
- **Library**: ApexCharts (bar, line, heatmap)
- **Instances**: 
  - `chartA`/`chartB`: Side-by-side machine comparisons
  - `detailLineChart`: Time-series for selected slot
  - Heatmap: Custom SVG implementation

### Theme System
- Light/dark mode toggle
- CSS custom properties for colors
- LocalStorage persistence
- Heatmap color customization

## 8. Build & Development
### Development Workflow
```bash
# Start full stack (API + frontend)
npm run dev

# Frontend only (Express serving dist/)
npm run dev:frontend

# Vite dev server with HMR
npm run dev:vite

# API only
npm run dev:api
```

### Production Build
```bash
# Build optimized dist/
npm run build

# Start PM2 services
npm start

# Manage services
npm run stop
npm run restart
npm run status
```

### Build Pipeline
1. **Vite**: Bundles React/TypeScript, processes Tailwind
2. **esbuild**: Minifies vanilla JS files (`app.js`, `wake-lock.js`)
3. **Output**: `dist/` directory with optimized assets

### Process Management
- **PM2**: Manages FastAPI backend as `bdr-api`
- **Auto-restart**: Enabled with 10s delay
- **Logging**: Merged stdout/stderr
- **Environment**: Injected via `ecosystem.config.cjs`

## 9. Configuration & Environment
### Environment Variables
```env
# Database
PG_HOST="localhost"
PG_PORT=5432
PG_DB="bdr_dashboard"
PG_USER="postgres"
PG_PASSWORD="postgres"

# API
API_TARGET="http://127.0.0.1:8000"

# AI Integration
GEMINI_API_KEY="MY_GEMINI_API_KEY"

# Hardware
AQC_PASSWORD="1234"
```

### Machine Registry (`machines.json`)
- 34 AQC machines defined
- Fields: `name`, `ip`, `user`, `removed_slots`
- Example: `{"name": "AQC-01", "ip": "192.168.1.101", "user": "root", "removed_slots": []}`

### Ring Configuration (`rings_config.json`)
- 900+ lines of per-slot configuration
- Maps physical slots to ring identifiers
- Includes hardware metadata (charger status, firmware version)

### Vite Configuration
- **React Plugin**: Enables JSX/TSX compilation
- **Tailwind CSS**: Utility-first styling
- **Proxy**: `/api/*` → FastAPI backend
- **HMR**: WebSocket-based hot module replacement
- **Aliases**: `@` → project root

## 10. Security & Authentication
### Current Implementation
- **No Authentication**: Dashboard is open to local network
- **SSH Keys**: Direct password authentication to AQC machines
- **API Exposure**: All endpoints publicly accessible
- **Environment Variables**: Secrets stored in `.env` (not encrypted)

### Security Considerations
- **Network Isolation**: Expected to run on isolated test network
- **Machine Access**: AQC machines use default credentials (`root:1234`)
- **Database**: PostgreSQL with default postgres user
- **No HTTPS**: HTTP-only communication
- **No Rate Limiting**: API endpoints unprotected

### Potential Vulnerabilities
1. **SSH Credential Exposure**: Passwords in plaintext
2. **SQL Injection**: Parameterized queries used (safe)
3. **XSS**: Direct DOM manipulation (potential risk)
4. **CSRF**: No protection on API endpoints
5. **Information Disclosure**: Detailed error messages

## 11. Performance & Optimization
### Data Fetching
- **Polling Interval**: 30 seconds for live data
- **SSE Stream**: Real-time updates via `/api/stream`
- **IndexedDB Cache**: Offline data persistence
- **Lazy Loading**: On-demand data fetching for diagnostics

### Rendering Performance
- **Batch Updates**: `__preservingUi` flag for DOM batching
- **Chart Reuse**: Instance preservation vs recreation
- **Selective Updates**: Targeted element modifications
- **Debounced Events**: Scroll/resize handlers throttled

### Database Optimization
- **Indexes**: On `timestamp` column in `archive_entries`
- **Connection Pooling**: PostgreSQL pool in `postgres_db.py`
- **Query Optimization**: Parameterized queries, selective columns
- **Archival Strategy**: Append-only with time-based partitioning

### Memory Management
- **Global State**: Limited to essential variables
- **Chart Disposal**: Proper cleanup on view switches
- **Event Listeners**: Removed on component destruction
- **Garbage Collection**: Minimal closure retention

## 12. Error Handling & Logging
### Frontend Error Handling
- **Global Handler**: `window.onerror` for uncaught exceptions
- **API Errors**: HTTP status checking with user notifications
- **Chart Errors**: Graceful degradation on render failures
- **Network Errors**: Retry logic with exponential backoff

### Backend Error Handling
- **FastAPI Exception Handlers**: Global error middleware
- **SSH Connection Errors**: Timeout and retry mechanisms
- **Database Errors**: Connection pool recovery
- **Validation Errors**: Pydantic model validation

### Logging Strategy
- **Frontend**: `console.log/warn/error` (no structured logging)
- **Backend**: Python `logging` module (file + console)
- **Diagnostics**: Machine-specific log files
- **Audit Trail**: Operation logging in database

### Error Recovery
- **Auto-Reconnect**: SSH connection retry
- **Data Fallback**: SQLite fallback when PostgreSQL unavailable
- **State Recovery**: IndexedDB cache restoration
- **Graceful Degradation**: Partial functionality on errors

## 13. Testing Strategy
### Current State
- **No Automated Tests**: Manual testing only
- **No Test Framework**: Jest/Vitest not configured
- **No CI/CD**: No automated pipelines
- **No Linting**: TypeScript errors only (`npm run lint`)

### Manual Testing Approach
1. **API Testing**: Postman/curl for endpoint verification
2. **UI Testing**: Manual browser interaction
3. **Hardware Testing**: Physical AQC machine verification
4. **Performance Testing**: Ad-hoc load testing

### Testing Gaps
- **Unit Tests**: No function-level testing
- **Integration Tests**: No API/UI integration tests
- **E2E Tests**: No user workflow testing
- **Performance Tests**: No benchmarking
- **Security Tests**: No vulnerability scanning

### Recommended Testing Framework
- **Frontend**: Vitest + React Testing Library
- **Backend**: pytest + FastAPI TestClient
- **E2E**: Playwright for browser automation
- **API**: Postman/Newman for endpoint testing

## 14. Future Considerations & Roadmap
### Technical Debt
1. **Monolithic Frontend**: `app.js` needs decomposition
2. **No Type Safety**: Vanilla JS lacks TypeScript benefits
3. **State Management**: Global variables → proper store
4. **Error Handling**: Inconsistent across codebase
5. **Testing**: Complete absence of automated tests

### Migration Path
1. **React Migration**: Gradual component extraction
2. **TypeScript**: Incremental type adoption
3. **State Management**: Zustand or Redux Toolkit
4. **API Layer**: Axios/fetch wrapper with retry logic
5. **Component Library**: shadcn/ui or similar

### Feature Roadmap
1. **Authentication**: Role-based access control
2. **Multi-User Support**: Concurrent user sessions
3. **Historical Analytics**: Advanced trend analysis
4. **Predictive Maintenance**: ML-based failure prediction
5. **Mobile Responsive**: Touch-optimized interface
6. **Export Capabilities**: PDF/CSV report generation
7. **Notification System**: Email/SMS alerts
8. **Audit Dashboard**: User activity tracking

### Infrastructure Improvements
1. **Containerization**: Docker for consistent environments
2. **Orchestration**: Docker Compose for multi-service
3. **CI/CD Pipeline**: GitHub Actions or GitLab CI
4. **Monitoring**: Prometheus + Grafana
5. **Backup Strategy**: Automated database backups
6. **High Availability**: Load balancing, failover

## 15. Appendix
### API Reference
- **Base URL**: `http://127.0.0.1:8000`
- **Content-Type**: `application/json`
- **Authentication**: None (open access)
- **Rate Limiting**: None implemented

### Database Connection
```python
# PostgreSQL connection string
postgresql://postgres:postgres@localhost:5432/bdr_dashboard

# SQLite fallback
sqlite:///data/archive.db
```

### Environment Setup
```bash
# Clone repository
git clone <repo-url>

# Install dependencies
npm install

# Configure environment
cp .env.example .env

# Start development
npm run dev
```

### Key Files Reference
| File | Purpose | Lines |
|------|---------|-------|
| `app.js` | Core dashboard logic | ~6800 |
| `data/api.py` | FastAPI endpoints | ~1200 |
| `data/postgres_db.py` | Database queries | ~800 |
| `data/main.py` | Background service | ~600 |
| `index.html` | HTML template | ~400 |
| `index.css` | Styles | ~300 |

### Version History
- **Phase 1-15**: Reverse engineering and documentation
- **Phase 16**: Comprehensive documentation synthesis
- **Current Version**: 0.0.0 (pre-release)

### Dependencies
**Runtime**:
- React 18.3.1
- Vite 6.2.3
- Express 4.21.2
- FastAPI (Python)
- PostgreSQL 14+

**Development**:
- TypeScript 5.8.2
- Tailwind CSS 4.1.14
- PM2 (process manager)

### Contact & Support
- **Project Repository**: Internal AQC team
- **Documentation**: This file (`PHASE16_DOCUMENTATION.md`)
- **Issue Tracking**: Internal ticketing system
- **Emergency Support**: AQC hardware team
