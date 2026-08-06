# BDR Dashboard — UX Discovery & Product Understanding Report

**Prepared for**: Dashboard Redesign Initiative  
**Date**: July 2026  
**Classification**: Internal — Design Team Only  
**Status**: Pre-Redesign Discovery

---

## Table of Contents

- [PART 1 — USER PERSONAS](#part-1--user-personas)
- [PART 2 — COMPLETE USER JOURNEYS](#part-2--complete-user-journeys)
- [PART 3 — FEATURE USAGE ANALYSIS](#part-3--feature-usage-analysis)
- [PART 4 — INFORMATION PRIORITY](#part-4--information-priority)
- [PART 5 — COGNITIVE LOAD ANALYSIS](#part-5--cognitive-load-analysis)
- [PART 6 — WORKFLOW EFFICIENCY](#part-6--workflow-efficiency)
- [PART 7 — CURRENT UX PROBLEMS](#part-7--current-ux-problems)
- [PART 8 — BUSINESS CRITICAL FEATURES](#part-8--business-critical-features)
- [PART 9 — OPERATOR MENTAL MODEL](#part-9--operator-mental-model)
- [PART 10 — FUTURE SCALABILITY](#part-10--future-scalability)
- [PART 11 — DESIGN CONSTRAINTS](#part-11--design-constraints)
- [PART 12 — DESIGN OPPORTUNITIES](#part-12--design-opportunities)
- [PART 13 — MISSING INFORMATION](#part-13--missing-information)

---

# PART 1 — USER PERSONAS

## Persona 1: Shift Operator

**Role**: Monitors ongoing battery discharge tests across the fleet during a work shift.

| Attribute | Detail |
|-----------|--------|
| **Name** | (Inferred) Operations Staff |
| **Reports To** | Production Supervisor |
| **Shift Pattern** | 8-hour shifts, likely rotating day/night |
| **Technical Skill** | Medium — knows battery testing, less familiar with hardware repair |

### Goals
- Ensure all machines are running tests without failures
- Identify failing slots as quickly as possible
- Escalate hardware issues to maintenance
- Meet shift throughput targets (slots tested per shift)

### Daily Workflow (Inferred from Implementation)
1. **Shift Start**: Opens dashboard, scans KPI cards for fleet overview
2. **Continuous Monitoring**: Glances at heatmap every 5–10 minutes looking for red/orange cells
3. **Issue Detection**: Clicks failing slot to investigate in Detail Panel
4. **Triage**: Decides if issue is software (note for engineer) or hardware (call technician)
5. **Escalation**: Provides slot ID, machine name, and symptoms to maintenance
6. **Verification**: After repair, confirms slot turns green
7. **Shift End**: Exports anomaly data for shift report

### Frustrations (Inferred from Implementation Gaps)
- Must actively watch dashboard — no push alerts when failures occur
- Filters reset when switching machines — must re-apply each time
- Cannot compare multiple machines side-by-side
- No historical trend view — can only see current snapshot
- Detail panel compresses main content when open

### Success Metrics (Inferred from Business Logic)
- Fewer than X failed slots per shift
- Mean time to detect failure < 5 minutes
- Mean time to resolution < 30 minutes
- Zero missed critical failures

### Primary Screens
- BDR Dashboard (primary — 80% of time)
- Detail Panel (secondary — 20% of time)

### Frequency of Use
- **Continuous** during shift (8 hours)
- **Dashboard always open** on primary or secondary monitor

---

## Persona 2: Quality Engineer

**Role**: Analyzes test results, identifies patterns, root-causes failures.

| Attribute | Detail |
|-----------|--------|
| **Name** | (Inferred) Engineering Staff |
| **Reports To** | Engineering Manager |
| **Shift Pattern** | Day shift, flexible hours |
| **Technical Skill** | High — understands BDR calculations, firmware, battery chemistry |

### Goals
- Identify systemic issues across machines
- Root-cause why specific slots or serials fail
- Validate firmware changes don't degrade BDR
- Ensure test methodology is consistent

### Daily Workflow (Inferred from Implementation)
1. **Opens Data Visualization View** — examines serial categories and SKU breakdown
2. **Opens Old Data View** — searches historical data for specific serials
3. **Cross-references** serial performance across multiple machines
4. **Generates AI Analysis Report** — gets fleet-wide pattern summary
5. **Reviews Cycle Analysis** — examines workout distribution for anomalies
6. **Uses Serial Browser** — finds specific serials across the fleet

### Frustrations (Inferred from Implementation Gaps)
- Old Data search is single-threaded and slow for large queries
- No built-in comparison tool for serials across time periods
- AI Report is text-based — no drill-down into underlying data
- Cannot export analysis findings directly to reports
- Cycle Analysis lacks trend visualization (only current snapshot)

### Success Metrics (Inferred from Business Logic)
- Root-cause identification within 24 hours
- Firmware regression detection within 1 shift
- 100% of critical anomalies investigated

### Primary Screens
- Data Visualization (primary)
- Old Data (primary)
- AI Analysis Report (secondary)
- Cycle Analysis (secondary)

### Frequency of Use
- **Daily** during investigation work
- **Session length**: 30–60 minutes per investigation
- **Ad-hoc** when issues are reported

---

## Persona 3: Maintenance Technician

**Role**: Fixes hardware issues on AQC machines via remote diagnostics.

| Attribute | Detail |
|-----------|--------|
| **Name** | (Inferred) Hardware/Maintenance Staff |
| **Reports To** | Maintenance Supervisor |
| **Shift Pattern** | On-call, covers multiple shifts |
| **Technical Skill** | Very High — understands I2C, MCP registers, Bluetooth, SPI LEDs |

### Goals
- Diagnose hardware faults remotely without physical inspection
- Repair MCP register corruption, stuck buttons, LED failures
- Restore Bluetooth connectivity
- Minimize machine downtime

### Daily Workflow (Inferred from Implementation)
1. **Receives repair request** from operator (slot ID, machine, symptoms)
2. **Opens Diagnostics View** — selects machine from dropdown
3. **Connects via SSH** — establishes remote connection
4. **Runs Quick Scan** — identifies button press/release states across 64 slots
5. **Identifies faulty component** — stuck button, corrupted MCP, dead LED
6. **Runs repair tool** — MCP repair, advanced repair, LED restore
7. **Verifies fix** — re-scans to confirm component works
8. **Monitors Live Logs** — watches for error messages during repair
9. **Returns to BDR Dashboard** — confirms slot status improves

### Frustrations (Inferred from Implementation)
- SSH connection can timeout (5s connect, 20s per-machine)
- No visual indication of connection quality
- Live Log monitor polls every 2 seconds — not truly real-time
- No repair history — must remember what was fixed before
- No guided diagnostic workflow — must know which tool to use

### Success Metrics (Inferred from Business Logic)
- Mean time to repair < 15 minutes
- First-time fix rate > 90%
- Zero false repairs (fixing working components)

### Primary Screens
- Diagnostics (primary — 90% of time)
- BDR Dashboard (secondary — 10% of time for verification)

### Frequency of Use
- **Ad-hoc** when repairs are needed
- **Session length**: 10–30 minutes per repair
- **Multiple repairs per day** during high-failure periods

---

## Persona 4: Production Supervisor

**Role**: Oversees fleet status, tracks throughput, identifies bottlenecks.

| Attribute | Detail |
|-----------|--------|
| **Name** | (Inferred) Management Staff |
| **Reports To** | Plant Manager |
| **Shift Pattern** | Day shift, visits floor periodically |
| **Technical Skill** — Low-Medium — understands output metrics, less on hardware

### Goals
- Ensure fleet is meeting throughput targets
- Identify machines that are underperforming
- Make staffing decisions based on workload
- Report production metrics to management

### Daily Workflow (Inferred from Implementation)
1. **Checks KPI cards** — total slots, avg battery, avg BDR at a glance
2. **Scans Floorplan** — visual overview of all machines by zone
3. **Reviews AI Analysis Report** — fleet-wide summary with alerts
4. **Checks Cycle Analysis** — workout distribution across machines
5. **Generates shift report** — exports data for management

### Frustrations (Inferred from Implementation Gaps)
- No single "fleet overview" screen — must navigate multiple views
- Cannot compare machine performance side-by-side
- No historical throughput trends
- Cannot set thresholds for alerts
- No scheduled report generation

### Success Metrics (Inferred from Business Logic)
- Fleet throughput meets daily targets
- Zero machines offline for > 1 hour
- All critical issues resolved within shift

### Primary Screens
- Floorplan (primary — quick overview)
- AI Analysis Report (primary — summary)
- KPI Cards (primary — metrics)
- Cycle Analysis (secondary — throughput)

### Frequency of Use
- **2–3 times per shift** (10–15 minutes each)
- **Quick glance** pattern — not deep investigation

---

## Persona 5: System Administrator

**Role**: Manages machine registry, maintains system health, oversees data integrity.

| Attribute | Detail |
|-----------|--------|
| **Name** | (Inferred) IT/Systems Staff |
| **Reports To** | IT Manager |
| **Shift Pattern** — On-call, irregular hours |
| **Technical Skill** — Very High — manages PostgreSQL, FastAPI, SSH, PM2 |

### Goals
- Ensure dashboard is online and data is fresh
- Manage machine registry (add/remove machines)
- Monitor database health and archival
- Troubleshoot API and connectivity issues

### Daily Workflow (Inferred from Implementation)
1. **Checks API health** — `/api/health` endpoint
2. **Monitors data freshness** — sync age, staleness indicators
3. **Reviews machine registry** — `machines.json` updates
4. **Checks PostgreSQL** — connection pool, archive growth
5. **Manages background processes** — PM2 restarts, watchdog alerts

### Frustrations (Inferred from Implementation)
- No admin UI — must edit JSON files directly
- No data freshness dashboard — must query API manually
- No automated alerts for system degradation
- Watchdog is incomplete (placeholder restart function)
- No user management or access control

### Success Metrics (Inferred from Business Logic)
- Dashboard uptime > 99.9%
- Data staleness < 5 minutes
- Zero data loss incidents

### Primary Screens
- None (works via CLI/API directly)
- Potentially: Diagnostics View (for system-level checks)

### Frequency of Use
- **Ad-hoc** when issues arise
- **Session length**: 15–60 minutes

---

# PART 2 — COMPLETE USER JOURNEYS

## Journey 1: Morning Shift Monitoring

```
START: Operator arrives at workstation (08:00)
  │
  ▼
Open BDR Dashboard in browser
  │
  ▼
┌─────────────────────────────────────────────────────────────────┐
│ GLANCE PHASE (10 seconds)                                       │
│                                                                  │
│ Check KPI Cards:                                                │
│   - Total Slots: 2,048 (expected ~2,048)                       │
│   - Avg Battery: 87.3% (expected >80%)                         │
│   - Avg BDR: 8.2 (expected 5-12)                               │
│   - Serials: 1,842 (expected stable)                           │
│                                                                  │
│ IF all green → proceed to scan                                  │
│ IF any red → investigate immediately                            │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│ SCAN PHASE (30 seconds)                                         │
│                                                                  │
│ Scan Heatmap Grid visually:                                     │
│   - Look for RED cells (slot-danger)                           │
│   - Look for ORANGE cells (slot-warn)                          │
│   - Look for PURPLE cells (slot-dead)                          │
│                                                                  │
│ Count problems: "3 red, 5 orange, 1 purple"                    │
│                                                                  │
│ IF critical issues found → jump to Investigation Journey       │
│ IF no issues → proceed to monitoring                           │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│ MONITORING PHASE (continuous)                                   │
│                                                                  │
│ Dashboard stays open on monitor                                 │
│ Periodic glance every 5-10 minutes                             │
│ Watch for changes in heatmap colors                             │
│                                                                  │
│ React to:                                                       │
│   - New red cells appearing                                     │
│   - Cells changing color                                        │
│   - Anomaly count increasing                                   │
└─────────────────────────────────────────────────────────────────┘
```

**Duration**: 08:00–08:05 (initial), then continuous  
**Outcome**: Fleet status known, issues identified

---

## Journey 2: Critical Machine Failure

```
TRIGGER: Operator notices 8 red cells on aqc-34
  │
  ▼
┌─────────────────────────────────────────────────────────────────┐
│ DETECTION (5 seconds)                                           │
│                                                                  │
│ Operator sees multiple red cells on same machine               │
│ Mental model: "Something is wrong with aqc-34"                 │
│                                                                  │
│ Action: Click first red cell                                    │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│ INVESTIGATION (2-3 minutes)                                     │
│                                                                  │
│ Detail Panel opens:                                             │
│   - Slot 12: "Dead" — battery <3%, flat >3hr                  │
│   - Workout table shows last workout 4 hours ago               │
│   - Battery chart shows flat line at 3%                        │
│                                                                  │
│ Action: Click next red cell (Slot 15)                           │
│   - Slot 15: "Dead" — same symptoms                            │
│                                                                  │
│ Action: Click next red cell (Slot 23)                           │
│   - Slot 23: "Critical Slanting" — full charge then drain      │
│                                                                  │
│ Pattern: Multiple dead slots on same machine                   │
│ Conclusion: Machine-level hardware failure                     │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│ ESCALATION (1 minute)                                           │
│                                                                  │
│ Operator calls maintenance technician:                         │
│ "aqc-34 has 8 dead slots, looks like hardware failure"        │
│                                                                  │
│ Provides: Machine name, slot IDs, symptoms                    │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│ VERIFICATION (after repair)                                     │
│                                                                  │
│ Technician confirms repair                                      │
│                                                                  │
│ Operator: Refreshes dashboard (wait for 5s poll)               │
│ Watches for cells to change from red → orange → green          │
│                                                                  │
│ IF cells turn green → issue resolved                           │
│ IF cells stay red → escalate further                           │
└─────────────────────────────────────────────────────────────────┘
```

**Duration**: 5–10 minutes detection + 15–30 minutes repair  
**Outcome**: Issue identified, escalated, resolved

---

## Journey 3: Dead Battery Investigation

```
TRIGGER: Operator notices single purple cell (slot-dead)
  │
  ▼
┌─────────────────────────────────────────────────────────────────┐
│ INITIAL ASSESSMENT (30 seconds)                                 │
│                                                                  │
│ Action: Click purple cell                                       │
│                                                                  │
│ Detail Panel shows:                                             │
│   - Battery: 2.1%                                              │
│   - Last workout: 3.5 hours ago                                │
│   - Warning: "Dead — battery <3% for >3hr"                    │
│                                                                  │
│ Mental model: "Battery died during test"                       │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│ DEEPER INVESTIGATION (2 minutes)                                │
│                                                                  │
│ Check workout table:                                            │
│   - Workout 1: 100% → 87% (1.2hr, BDR 10.8)                  │
│   - Workout 2: 100% → 88% (1.1hr, BDR 10.9)                  │
│   - Workout 3: 100% → 3% (4.5hr, BDR 21.3) ← anomaly         │
│                                                                  │
│ Check battery chart:                                            │
│   - Shows normal discharge for first 2 workouts               │
│   - Third workout shows extended discharge to near-zero       │
│                                                                  │
│ Mental model: "Battery capacity degraded mid-test"            │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│ DECISION (30 seconds)                                           │
│                                                                  │
│ Options:                                                        │
│ A) Battery is faulty → swap battery, retest                   │
│ B) Slot has hardware issue → call maintenance                 │
│ C) Normal end-of-life → mark as completed                     │
│                                                                  │
│ Operator decides based on:                                      │
│   - How many workouts completed (2 = early failure)           │
│   - BDR trend (increasing = degradation)                      │
│   - Similar failures on other slots                           │
└─────────────────────────────────────────────────────────────────┘
```

**Duration**: 3–5 minutes  
**Outcome**: Root cause identified, action decided

---

## Journey 4: Firmware Issue Investigation

```
TRIGGER: Operator notices cluster of orange cells on newer firmware
  │
  ▼
┌─────────────────────────────────────────────────────────────────┐
│ PATTERN RECOGNITION (1 minute)                                  │
│                                                                  │
│ Operator notices:                                               │
│   - 5 orange cells all showing "High BDR" (avg >12)           │
│   - All have firmware v1.4                                     │
│   - Older firmware slots (v1.3) are green                     │
│                                                                  │
│ Mental model: "Firmware v1.4 might be causing high BDR"       │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│ FILTER APPLICATION (30 seconds)                                 │
│                                                                  │
│ Action: Click firmware filter button for "v1.4"               │
│                                                                  │
│ Result: Only v1.4 slots shown in heatmap                      │
│ Count: 12 slots with v1.4, 5 are orange                       │
│                                                                  │
│ Action: Also click "v1.3" filter                              │
│                                                                  │
│ Result: Both v1.3 and v1.4 shown                              │
│ Compare: v1.3 slots are mostly green, v1.4 mostly orange     │
│                                                                  │
│ Mental model: "Confirmed — v1.4 has BDR regression"           │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│ DOCUMENTATION (2 minutes)                                       │
│                                                                  │
│ Operator notes:                                                 │
│   - Firmware v1.4 showing high BDR on 5/12 slots             │
│   - v1.3 baseline: avg BDR 8.2                                │
│   - v1.4 affected: avg BDR 14.5                               │
│                                                                  │
│ Action: Take screenshot, send to engineering team              │
│ "Firmware v1.4 regression — BDR increased 77%"                │
└─────────────────────────────────────────────────────────────────┘
```

**Duration**: 3–5 minutes  
**Outcome**: Firmware issue identified and escalated

---

## Journey 5: Hardware Diagnostics

```
TRIGGER: Maintenance technician receives repair request
  "aqc-34 slot 12 — stuck button, can't start test"
  │
  ▼
┌─────────────────────────────────────────────────────────────────┐
│ CONNECTION (30 seconds)                                         │
│                                                                  │
│ Action: Open Diagnostics View                                  │
│ Action: Select "aqc-34" from machine dropdown                 │
│ Action: Click "Connect"                                        │
│                                                                  │
│ System: POST /api/machine/aqc-34/diagnose/connect             │
│ Status: "Connecting..." → "Connected"                         │
│                                                                  │
│ Mental machine: "Establishing SSH connection to 172.16.18.80" │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│ SCANNING (10 seconds)                                           │
│                                                                  │
│ Action: Click "Quick Scan"                                     │
│                                                                  │
│ System: POST /api/machine/aqc-34/diagnose/scan                │
│ Grid: 64 cells update with press/release states               │
│                                                                  │
│ Result:                                                         │
│   - Slot 12: RED (pressed — stuck!)                           │
│   - All others: GREEN (released — normal)                     │
│                                                                  │
│ Mental model: "Confirmed — slot 12 button is physically stuck"│
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│ REPAIR (2-5 minutes)                                            │
│                                                                  │
│ Action: Click "MCP Scan"                                       │
│   → Reads MCP23017 registers (I2C addresses 0x20-0x27)       │
│   → Finds corrupted register at 0x23                          │
│                                                                  │
│ Action: Click "MCP Repair"                                     │
│   → Writes correct values back to register                    │
│   → Register restored                                         │
│                                                                  │
│ Action: Re-scan buttons                                        │
│   → Slot 12 now shows GREEN (released)                        │
│                                                                  │
│ Mental model: "MCP register was corrupted — fixed"            │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│ VERIFICATION (1 minute)                                         │
│                                                                  │
│ Action: Switch to BDR Dashboard                                │
│ Action: Select aqc-34                                          │
│ Action: Check slot 12 in heatmap                              │
│                                                                  │
│ Result: Slot 12 now shows orange (was red)                    │
│ Next test: Operator can start new test on slot 12             │
│                                                                  │
│ Mental model: "Repair successful — slot operational"          │
└─────────────────────────────────────────────────────────────────┘
```

**Duration**: 5–10 minutes total  
**Outcome**: Hardware fault identified, repaired, verified

---

## Journey 6: Historical Lookup

```
TRIGGER: Quality engineer needs to investigate serial "WB-24-001-WB"
  │
  ▼
┌─────────────────────────────────────────────────────────────────┐
│ SEARCH (30 seconds)                                             │
│                                                                  │
│ Action: Open Old Data View                                     │
│ Action: Ensure "Single Serial" mode selected                  │
│ Action: Type "WB-24-001-WB" in search field                  │
│ Action: Click "Search"                                         │
│                                                                  │
│ System: GET /api/old-data/search/WB-24-001-WB                 │
│ Response: Array of historical records                          │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│ ANALYSIS (3-5 minutes)                                          │
│                                                                  │
│ Results table shows:                                            │
│   - 6 records across 2 machines over 2 weeks                  │
│   - aqc-34: 3 tests, avg BDR 8.2, all passed                │
│   - aqc-45: 3 tests, avg BDR 14.5, 2 failed                 │
│                                                                  │
│ Mental model: "Same serial, different results on different    │
│ machines — suggests machine-specific issue, not battery"       │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│ DOCUMENTATION (2 minutes)                                       │
│                                                                  │
│ Action: Click "Export Results CSV"                             │
│ Action: Attach to investigation report                         │
│                                                                  │
│ Mental model: "Need to compare aqc-34 vs aqc-45 setup"       │
└─────────────────────────────────────────────────────────────────┘
```

**Duration**: 5–8 minutes  
**Outcome**: Historical pattern identified

---

## Journey 7: Serial Search Across Fleet

```
TRIGGER: Engineer needs to find all locations of serial "WB-32-045-WB"
  │
  ▼
┌─────────────────────────────────────────────────────────────────┐
│ BULK SEARCH (1 minute)                                          │
│                                                                  │
│ Action: Press Q key (open Serial Browser)                      │
│ Action: Type "WB-32-045-WB"                                   │
│ Action: Click "Search"                                         │
│                                                                  │
│ System: Searches all ringsData across machines                │
│ Result: Found in 2 locations                                   │
│   - aqc-34, slot 23                                           │
│   - aqc-45, slot 8 (duplicate!)                               │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│ DUPLICATE RESOLUTION (2 minutes)                                │
│                                                                  │
│ Duplicate modal appears:                                        │
│ "⚠️ Serial found in multiple locations"                       │
│                                                                  │
│ Action: Click "Go to aqc-34:23"                               │
│                                                                  │
│ System: Switches to aqc-34, opens Detail Panel for slot 23    │
│                                                                  │
│ Mental model: "Same serial on two machines — data integrity   │
│ issue. Need to investigate which is correct."                  │
└─────────────────────────────────────────────────────────────────┘
```

**Duration**: 3 minutes  
**Outcome**: Duplicate detected, locations identified

---

## Journey 8: Floorplan Navigation

```
TRIGGER: Supervisor wants to see physical layout of machines
  │
  ▼
┌─────────────────────────────────────────────────────────────────┐
│ OPEN FLOORPLAN (5 seconds)                                      │
│                                                                  │
│ Action: Click Floorplan button (or press F)                    │
│                                                                  │
│ Result: Floorplan overlay opens showing 4 zones               │
│   - Zone A: 20 machines (blue)                                │
│   - Zone B: 8 machines (green)                                │
│   - Zone C: 8 machines (orange)                               │
│   - Zone D: 6 machines (purple)                               │
│                                                                  │
│ Each machine box shows:                                        │
│   - Machine name (e.g., "aqc-34")                             │
│   - Slot count with color (red→green gradient)                │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│ VISUAL SCANNING (30 seconds)                                    │
│                                                                  │
│ Supervisor scans zones:                                         │
│   - Zone A: Most boxes green (high slot count)                │
│   - Zone B: One box red (aqc-17 = 0 slots)                   │
│   - Zone C: All boxes yellow-green                            │
│   - Zone D: Mixed colors                                       │
│                                                                  │
│ Mental model: "Zone A is healthy, Zone B has a problem"       │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│ DRILL-DOWN (10 seconds)                                         │
│                                                                  │
│ Action: Click on aqc-17 (red box in Zone B)                   │
│                                                                  │
│ Result: Floorplan closes, switches to aqc-17 BDR Dashboard    │
│                                                                  │
│ Shows: 0 occupied slots, machine appears offline              │
│                                                                  │
│ Mental model: "Machine is completely empty — needs attention" │
└─────────────────────────────────────────────────────────────────┘
```

**Duration**: 1 minute  
**Outcome**: Physical layout understood, problem machine identified

---

# PART 3 — FEATURE USAGE ANALYSIS

## Screen Usage Ranking

| Rank | Screen | Purpose | Primary Users | Frequency | Session Length |
|------|--------|---------|---------------|-----------|----------------|
| 1 | BDR Dashboard | Real-time monitoring | Operators, Supervisors | Continuous (8hr) | 8 hours |
| 2 | Detail Panel | Slot investigation | Operators, Engineers | Ad-hoc (10-20x/day) | 2-5 min |
| 3 | Diagnostics | Hardware repair | Technicians | Ad-hoc (3-10x/day) | 10-30 min |
| 4 | Floorplan | Physical overview | Supervisors | 2-3x/day | 1-2 min |
| 5 | Ring Slots | Ring status | Operators | 5-10x/day | 2-5 min |
| 6 | Old Data | Historical search | Engineers | 1-3x/day | 5-10 min |
| 7 | Data Viz | Serial analytics | Engineers | 1-2x/day | 10-20 min |
| 8 | Serial Browser | Quick serial lookup | Engineers | 2-5x/day | 1-2 min |
| 9 | Cycle Analysis | Workout distribution | Supervisors | 1x/day | 2-3 min |
| 10 | AI Report | Fleet summary | Supervisors | 1-2x/day | 3-5 min |

---

## Screen Details

### 1. BDR Dashboard

| Attribute | Detail |
|-----------|--------|
| **Purpose** | Primary real-time monitoring interface |
| **Who Uses** | Operators (primary), Supervisors, Engineers |
| **How Often** | Continuous — always open during shift |
| **When Used** | Entire shift, especially shift start and after alerts |
| **Information Sought** | Which slots are failing, overall fleet health |
| **Session Length** | 8 hours (always open) |
| **Primary Actions** | Scan heatmap, check KPIs, click slots, apply filters |

**Usage Pattern**:
- 70% passive monitoring (dashboard open, occasional glance)
- 20% active investigation (clicking slots, reviewing details)
- 10% filter/search (applying health/firmware filters)

---

### 2. Detail Panel

| Attribute | Detail |
|-----------|--------|
| **Purpose** | Deep-dive into individual slot performance |
| **Who Uses** | Operators (investigation), Engineers (analysis) |
| **How Often** | 10–20 times per shift per operator |
| **When Used** | After identifying failing slot in heatmap |
| **Information Sought** | Workout history, battery chart, warning reasons |
| **Session Length** | 2–5 minutes per slot |
| **Primary Actions** | Review workout table, check chart, navigate slots |

**Usage Pattern**:
- 40% quick check (open, glance, close)
- 40% deep investigation (review all data)
- 20% navigation (move between slots)

---

### 3. Diagnostics View

| Attribute | Detail |
|-----------|--------|
| **Purpose** | Remote hardware diagnostics and repair |
| **Who Uses** | Maintenance Technicians (primary) |
| **How Often** | 3–10 times per day (repair-dependent) |
| **When Used** | When hardware fault is suspected |
| **Information Sought** | Button states, MCP registers, LED status, logs |
| **Session Length** | 10–30 minutes per repair |
| **Primary Actions** | Connect, scan, repair, verify |

**Usage Pattern**:
- 30% connection setup
- 40% scanning and diagnosis
- 30% repair execution

---

### 4. Floorplan

| Attribute | Detail |
|-----------|--------|
| **Purpose** | Physical layout visualization |
| **Who Uses** | Supervisors (primary), Operators |
| **How Often** | 2–3 times per shift |
| **When Used** | Shift start, after major issues, for fleet overview |
| **Information Sought** | Machine status by physical location |
| **Session Length** | 1–2 minutes |
| **Primary Actions** | Visual scan, click machine to navigate |

**Usage Pattern**:
- 80% visual scanning (passive)
- 20% navigation (click to machine)

---

### 5. Ring Slots View

| Attribute | Detail |
|-----------|--------|
| **Purpose** | Ring-specific status monitoring |
| **Who Uses** | Operators (secondary monitoring) |
| **How Often** | 5–10 times per shift |
| **When Used** | When ring-specific issues are suspected |
| **Information Sought** | Ring status (running/passed/failed/assigned) |
| **Session Length** | 2–5 minutes |
| **Primary Actions** | Filter by status, search serial, export CSV |

**Usage Pattern**:
- 50% filtering by status
- 30% searching for specific serials
- 20% exporting data

---

### 6. Old Data View

| Attribute | Detail |
|-----------|--------|
| **Purpose** | Historical archive search |
| **Who Uses** | Quality Engineers (primary) |
| **How Often** | 1–3 times per day |
| **When Used** | During investigation, for historical comparison |
| **Information Sought** | Past test results for specific serials |
| **Session Length** | 5–10 minutes per search |
| **Primary Actions** | Enter serial, search, review results, export |

**Usage Pattern**:
- 60% single serial search
- 30% bulk serial search
- 10% export

---

### 7. Data Visualization View

| Attribute | Detail |
|-----------|--------|
| **Purpose** | Serial analytics and category breakdown |
| **Who Uses** | Quality Engineers (primary) |
| **How Often** | 1–2 times per day |
| **When Used** | During analysis, for pattern identification |
| **Information Sought** | Serial categories, SKU distribution |
| **Session Length** | 10–20 minutes |
| **Primary Actions** | Select category, review chart, drill into serials |

**Usage Pattern**:
- 50% category analysis
- 30% SKU breakdown review
- 20% serial drill-down

---

### 8. Serial Browser

| Attribute | Detail |
|-----------|--------|
| **Purpose** | Quick serial number search |
| **Who Uses** | Engineers, Operators |
| **How Often** | 2–5 times per day |
| **When Used** | When looking for specific serial across fleet |
| **Information Sought** | Serial location, status, duplicate detection |
| **Session Length** | 1–2 minutes |
| **Primary Actions** | Enter serial, search, navigate to result |

**Usage Pattern**:
- 70% single serial lookup
- 20% duplicate detection
- 10% bulk search

---

### 9. Cycle Analysis

| Attribute | Detail |
|-----------|--------|
| **Purpose** | Workout distribution analysis |
| **Who Uses** | Supervisors (primary) |
| **How Often** | 1 time per day |
| **When Used** | Shift start or end, for throughput review |
| **Information Sought** | How many slots have completed how many workouts |
| **Session Length** | 2–3 minutes |
| **Primary Actions** | View histogram, review per-machine breakdown |

**Usage Pattern**:
- 90% passive viewing
- 10% export

---

### 10. AI Analysis Report

| Attribute | Detail |
|-----------|--------|
| **Purpose** | Automated fleet analysis with recommendations |
| **Who Uses** | Supervisors (primary) |
| **How Often** | 1–2 times per day |
| **When Used** | Shift start/end, for management reporting |
| **Information Sought** | Fleet overview, alerts, machine status summary |
| **Session Length** | 3–5 minutes |
| **Primary Actions** | Generate report, review alerts, export |

**Usage Pattern**:
- 80% passive reading
- 20% export/sharing

---

# PART 4 — INFORMATION PRIORITY

## BDR Dashboard Widget Priority

| Widget | Priority | Why |
|--------|----------|-----|
| **Heatmap Grid** | **Critical** | Primary monitoring tool — operators stare at this all day |
| **KPI Cards (4)** | **Critical** | Fleet health at a glance — first thing checked |
| **Spotlight Anomalies** | **Critical** | Top issues requiring immediate attention |
| **Anomaly Table** | **Important** | Full list for investigation, but secondary to heatmap |
| **Health Class Filters** | **Important** | Essential for identifying problem types |
| **Firmware Filters** | **Important** | Firmware-specific issues require filtering |
| **Phase Distribution Chart** | **Supporting** | Context about test stages, not primary |
| **Battery Distribution Chart** | **Supporting** | Context about charge levels, not primary |
| **BDR History Chart** | **Supporting** | Trend analysis, not real-time monitoring |
| **Battery Doughnut** | **Supporting** | Visual summary, redundant with KPI card |
| **Workouts Table** | **Supporting** | Recent activity, not critical for monitoring |
| **Diagnostics Summary** | **Rarely Used** | Hardware status, only checked during repairs |
| **Color Customization** | **Decorative** | Personalization, no business impact |

---

## Detail Panel Widget Priority

| Widget | Priority | Why |
|--------|----------|-----|
| **Slot ID + Machine** | **Critical** | Identifies which slot is being investigated |
| **Status Badge** | **Critical** | Pass/Fail/Warn — immediate understanding |
| **Battery Percentage** | **Critical** | Current test state |
| **Avg BDR** | **Critical** | Test quality indicator |
| **Workout Table** | **Important** | Historical performance for investigation |
| **Battery/Current Chart** | **Important** | Visual trend for pattern recognition |
| **Warning Reason** | **Important** | Explains why slot is flagged |
| **MAC Address** | **Supporting** | Hardware identifier, rarely needed |
| **Firmware Version** | **Supporting** | Context, not primary |
| **Slanting Leak Badge** | **Important** | Specific issue indicator |

---

## Diagnostics View Widget Priority

| Widget | Priority | Why |
|--------|----------|-----|
| **Machine Selector** | **Critical** | Must select machine before any action |
| **Connect Button** | **Critical** | Prerequisite for all diagnostics |
| **Button Grid** | **Critical** | Primary diagnostic visualization |
| **Quick Scan Button** | **Critical** | Most common diagnostic action |
| **Status Bar** | **Important** | Connection status awareness |
| **Live Monitor Button** | **Important** | Continuous monitoring during repair |
| **LED Controls** | **Supporting** | Specific repair scenario |
| **Extended Diagnostics** | **Supporting** | Advanced repairs, less common |
| **Live Log Monitor** | **Supporting** | Debugging, not primary workflow |

---

## Floorplan Widget Priority

| Widget | Priority | Why |
|--------|----------|-----|
| **Machine Boxes** | **Critical** | Core visualization — slot count + color |
| **Zone Labels** | **Important** | Physical location context |
| **Legend** | **Important** | Color interpretation |
| **Unmapped Machines** | **Supporting** | Machines not assigned to positions |
| **Search** | **Supporting** | Find specific machine in layout |

---

# PART 5 — COGNITIVE LOAD ANALYSIS

## BDR Dashboard

**Cognitive Load: HIGH**

| Factor | Assessment | Explanation |
|--------|------------|-------------|
| **Information Density** | High | 64 heatmap cells + 4 KPI cards + 3 charts + 2 tables + filters |
| **Color Complexity** | High | 10 health class colors to distinguish |
| **Real-Time Updates** | Medium | 5-second refresh requires constant attention |
| **Filter Combinations** | High | Health class AND firmware filters with AND logic |
| **Spatial Layout** | Medium | Heatmap is intuitive, but many peripheral elements |
| **Text Readability** | Medium | Small text in tables, hover required for details |

**Why High**:
- Operators must simultaneously monitor 64 cells across 40 machines
- 10 color-coded health states require learned interpretation
- Filters add complexity (health + firmware = AND logic)
- Peripheral charts/tables compete for attention with primary heatmap
- No visual hierarchy guidance — everything appears equally important

---

## Detail Panel

**Cognitive Load: MEDIUM**

| Factor | Assessment | Explanation |
|--------|------------|-------------|
| **Information Density** | Medium | Multiple data fields, but organized |
| **Chart Complexity** | Medium | Dual-axis chart (battery + current) |
| **Table Complexity** | Low | Simple workout table with clear columns |
| **Navigation** | Low | Prev/next arrows, clear controls |

**Why Medium**:
- Information is well-organized in sections
- Chart provides visual pattern recognition
- Table is straightforward
- But: no clear visual hierarchy within panel

---

## Diagnostics View

**Cognitive Load: VERY HIGH**

| Factor | Assessment | Explanation |
|--------|------------|-------------|
| **Technical Complexity** | Very High | I2C registers, MCP chips, Bluetooth, SPI LEDs |
| **Button Grid** | Medium | 64 cells with 3 states (pressed/released/unknown) |
| **Tool Availability** | High | 15+ diagnostic tools to choose from |
| **Decision Complexity** | Very High | Must know which tool to use for which problem |
| **Error Recovery** | High | Failed repairs can make things worse |

**Why Very High**:
- Requires deep technical knowledge of hardware
- Many tools with non-obvious purposes
- Must interpret register states, error codes
- Wrong action can damage hardware
- No guided workflow — expert knowledge required

---

## Ring Slots View

**Cognitive Load: LOW-MEDIUM**

| Factor | Assessment | Explanation |
|--------|------------|-------------|
| **Information Density** | Medium | 64 cells + 5 KPI cards + filters |
| **Color Complexity** | Low | Only 5 status colors |
| **Filter Complexity** | Low | Single-dimension filtering |
| **Search** | Low | Simple text search |

**Why Low-Medium**:
- Simpler than BDR Dashboard (fewer colors, simpler logic)
- Status categories are intuitive (Running/Passed/Failed)
- Search is straightforward

---

## Old Data View

**Cognitive Load: LOW**

| Factor | Assessment | Explanation |
|--------|------------|-------------|
| **Information Density** | Low | Search field + results table |
| **Task Complexity** | Low | Enter serial, click search |
| **Decision Points** | Low | Single/multi serial mode |

**Why Low**:
- Simple search interface
- Clear results table
- Minimal decision points

---

## Overall System Cognitive Load

| Screen | Load | Primary Contributors |
|--------|------|---------------------|
| BDR Dashboard | **High** | 10 colors, 64 cells, filter logic |
| Detail Panel | **Medium** | Dual-axis chart, workout table |
| Diagnostics | **Very High** | Technical complexity, tool selection |
| Ring Slots | **Low-Medium** | Simpler status model |
| Old Data | **Low** | Simple search |
| Data Viz | **Medium** | Category analysis |
| Floorplan | **Low** | Visual scanning only |
| Cycle Analysis | **Low** | Read-only histogram |
| AI Report | **Low** | Read-only summary |

---

# PART 6 — WORKFLOW EFFICIENCY

## Task 1: Check Fleet Status

| Metric | Value |
|--------|-------|
| **Clicks Required** | 0 (passive monitoring) |
| **Context Switches** | 0 |
| **Views Opened** | 1 (BDR Dashboard) |
| **Average Time** | 10 seconds (glance) |
| **Bottlenecks** | None — designed for this |
| **Confusion Points** | KPI card meaning may not be obvious to new users |

**Efficiency**: HIGH — optimized for this task

---

## Task 2: Investigate Failing Slot

| Metric | Value |
|--------|-------|
| **Clicks Required** | 3–5 (click cell → review panel → possibly navigate) |
| **Context Switches** | 1 (dashboard → detail panel) |
| **Views Opened** | 1 (detail panel overlays dashboard) |
| **Average Time** | 2–5 minutes |
| **Bottlenecks** | Must know what to look for in workout table/chart |
| **Confusion Points** | Chart tooltip interpretation, workout table ordering |

**Efficiency**: MEDIUM — could be faster with guided workflow

---

## Task 3: Switch Machine and Monitor

| Metric | Value |
|--------|-------|
| **Clicks Required** | 1 (click machine tab) |
| **Context Switches** | 1 (machine A → machine B) |
| **Views Opened** | 1 (same view, different data) |
| **Average Time** | 5 seconds |
| **Bottlenecks** | Filters reset on switch (must re-apply) |
| **Confusion Points** | No visual indicator that filters were cleared |

**Efficiency**: MEDIUM — filter reset is a friction point

---

## Task 4: Hardware Repair (Diagnostics)

| Metric | Value |
|--------|-------|
| **Clicks Required** | 8–15 (select machine → connect → scan → repair → verify → return) |
| **Context Switches** | 2 (diagnostics → bdr dashboard for verification) |
| **Views Opened** | 2 (diagnostics + bdr dashboard) |
| **Average Time** | 10–30 minutes |
| **Bottlenecks** | Must know which repair tool to use |
| **Confusion Points** | Tool selection, repair verification, no guided workflow |

**Efficiency**: LOW — requires expert knowledge, no guidance

---

## Task 5: Search Historical Data

| Metric | Value |
|--------|-------|
| **Clicks Required** | 3–4 (open view → enter serial → search → review) |
| **Context Switches** | 1 (current view → old data) |
| **Views Opened** | 1 (old data view) |
| **Average Time** | 5–10 minutes |
| **Bottlenecks** | Large result sets may be slow |
| **Confusion Points** | Single vs bulk mode, result interpretation |

**Efficiency**: MEDIUM — straightforward but no drill-down

---

## Task 6: Export Data for Report

| Metric | Value |
|--------|-------|
| **Clicks Required** | 2–3 (navigate to view → apply filters → export) |
| **Context Switches** | 1 (current view → export view) |
| **Views Opened** | 1 (varies by export type) |
| **Average Time** | 1–2 minutes |
| **Bottlenecks** | Export format is CSV only |
| **Confusion Points** | Which export button to use, what data is included |

**Efficiency**: MEDIUM — limited export options

---

## Task 7: Generate Fleet Report

| Metric | Value |
|--------|-------|
| **Clicks Required** | 2 (open AI report → generate) |
| **Context Switches** | 1 (current view → AI report) |
| **Views Opened** | 1 (AI report overlay) |
| **Average Time** | 3–5 minutes |
| **Bottlenecks** | Report generation time, no customization |
| **Confusion Points** | Report content is fixed, cannot tailor |

**Efficiency**: HIGH — simple trigger, automated output

---

## Task 8: Find Duplicate Serials

| Metric | Value |
|--------|-------|
| **Clicks Required** | 4–6 (open browser → search → detect duplicate → navigate) |
| **Context Switches** | 2 (current → serial browser → target machine) |
| **Views Opened** | 2 (serial browser + detail panel) |
| **Average Time** | 2–3 minutes |
| **Bottlenecks** | Must manually check each duplicate location |
| **Confusion Points** | Duplicate modal behavior, which location to investigate |

**Efficiency**: MEDIUM — detection is automatic, resolution is manual

---

## Task 9: Apply Multiple Filters

| Metric | Value |
|--------|-------|
| **Clicks Required** | 2–4 (click filter 1, click filter 2, possibly more) |
| **Context Switches** | 0 |
| **Views Opened** | 0 (same view) |
| **Average Time** | 5–10 seconds |
| **Bottlenecks** | AND logic between health + firmware may confuse |
| **Confusion Points** | Clear button location, filter persistence |

**Efficiency**: MEDIUM — functional but logic unclear

---

## Task 10: Navigate Between Machines Quickly

| Metric | Value |
|--------|-------|
| **Clicks Required** | 1 per switch (click tab) or 0 (keyboard shortcut) |
| **Context Switches** | 1 per switch |
| **Views Opened** | 0 (same view) |
| **Average Time** | 2 seconds per switch |
| **Bottlenecks** | Many machines = scrolling tabs |
| **Confusion Points** | Machine number shortcut (0-9 + Enter) may be undiscoverable |

**Efficiency**: HIGH with keyboard, MEDIUM with mouse

---

# PART 7 — CURRENT UX PROBLEMS

## Information Hierarchy

| Problem | Location | Impact |
|---------|----------|--------|
| No clear focal point | BDR Dashboard | All elements compete for attention |
| KPI cards not differentiated | Top bar | All 4 look identical, no emphasis on most important |
| Heatmap lacks visual grouping | Center | 64 cells feel like a wall of colors |
| Anomaly table below fold | Bottom | Important data requires scrolling |
| Charts compete with heatmap | Right side | Peripheral data draws attention from primary |

---

## Navigation

| Problem | Location | Impact |
|---------|----------|--------|
| Machine tabs overflow | Header | 40+ tabs require scrolling |
| No machine search | Header | Must scroll to find specific machine |
| View toggle not persistent | Header | No indicator of current view |
| No breadcrumbs | All views | No sense of "where am I" |
| Back button behavior unclear | Browser | May not work as expected |
| No machine comparison | All views | Cannot view 2 machines simultaneously |

---

## Filters

| Problem | Location | Impact |
|---------|----------|--------|
| Filter state lost on machine switch | BDR Dashboard | Must re-apply filters every switch |
| AND logic unclear | BDR Dashboard | Users may not understand filter combination |
| No filter count indicator | Filter buttons | No badge showing filtered count |
| Clear button not prominent | Filter bar | Hard to find when filters active |
| No filter presets | BDR Dashboard | Common filter combos not saveable |
| No filter persistence | Session | Filters reset on page reload |

---

## Discoverability

| Problem | Location | Impact |
|---------|----------|--------|
| Keyboard shortcuts undiscoverable | Global | T/F/C/Q/S not documented in UI |
| Floorplan right-click menu | Floorplan | Context menu not obvious |
| Graph freeze toggle | Detail Panel | Feature hidden in toolbar |
| Machine number input | Global | 0-9 + Enter pattern unknown |
| Serial browser (Q key) | Global | Overlay not discoverable |
| Color customization | BDR Dashboard | Hidden in filter bar |

---

## Consistency

| Problem | Location | Impact |
|---------|----------|--------|
| Mixed chart libraries | Charts | D3 for heatmap, ApexCharts for others |
| Inconsistent button styles | All views | Different button designs across views |
| Inconsistent spacing | All views | Variable padding/margins |
| Inconsistent typography | All views | Mixed font sizes/weights |
| Inconsistent status labels | Multiple | "Pass" vs "Passed" vs "pass" |

---

## Spacing

| Problem | Location | Impact |
|---------|----------|--------|
| Dense heatmap cells | BDR Dashboard | Small touch targets |
| Cramped detail panel | Detail Panel | Information packed tightly |
| Overlapping overlays | Overlays | Z-index conflicts possible |
| No breathing room | All views | Everything feels compressed |

---

## Visual Hierarchy

| Problem | Location | Impact |
|---------|----------|--------|
| No size differentiation | KPI cards | All same size regardless of importance |
| No weight differentiation | Headings | All similar visual weight |
| Color overuse | Heatmap | 10 colors compete |
| No progressive disclosure | All views | Everything visible at once |
| No visual grouping | BDR Dashboard | Widgets not clearly separated |

---

## Interaction Patterns

| Problem | Location | Impact |
|---------|----------|--------|
| No loading states | API calls | Stale data shown during fetch |
| No empty states | All views | No guidance when no data |
| No error messages | API failures | Silent failures |
| No confirmation dialogs | Destructive actions | No undo for accidental clicks |
| No drag-and-drop | Floorplan | Manual assignment only |
| No multi-select | Heatmap | Can only select one slot |

---

## Error Prevention

| Problem | Location | Impact |
|---------|----------|--------|
| No input validation | Search fields | Invalid searches possible |
| No rate limiting (UI) | API calls | Rapid clicks could overwhelm |
| No accidental click prevention | All buttons | Single click executes immediately |
| No unsaved changes warning | Filters | State lost without warning |

---

## Accessibility

| Problem | Location | Impact |
|---------|----------|--------|
| No ARIA labels | All elements | Screen readers can't interpret |
| No keyboard navigation | Heatmap grid | Can't navigate without mouse |
| No focus indicators | Buttons/links | Can't see where focus is |
| Low contrast ratios | Some text on dark | Hard to read |
| No color-blind support | Health colors | Relies solely on color |
| No reduced motion | Animations | No preference respect |

---

## Charts

| Problem | Location | Impact |
|---------|----------|--------|
| No chart zoom | BDR History | Can't focus on time period |
| No chart export | All charts | Can't save visualizations |
| No chart tooltips on mobile | All charts | Touch interaction unclear |
| Dual-axis confusion | Detail Panel | Battery + current may confuse |
| No chart legend toggle | All charts | Can't hide series |

---

## Tables

| Problem | Location | Impact |
|---------|----------|--------|
| No column sorting | Anomaly table | Can't sort by severity |
| No row selection | All tables | Can't multi-select |
| No pagination | Anomaly table | Long lists are overwhelming |
| No virtual scrolling | Anomaly table | Performance with many rows |
| No column resize | All tables | Fixed column widths |

---

## Detail Panel

| Problem | Location | Impact |
|---------|----------|--------|
| Panel compresses main content | BDR Dashboard | 40% width reduction |
| No dock/undock option | Detail Panel | Fixed position only |
| No print view | Detail Panel | Can't print slot report |
| No share link | Detail Panel | Can't share specific slot |
| No comparison view | Detail Panel | Can't compare 2 slots |

---

## Overlays

| Problem | Location | Impact |
|---------|----------|--------|
| Single overlay limit | Global | Can't view floorplan + serial browser |
| No overlay history | Global | Can't go back to previous overlay |
| Large overlays block content | All overlays | Can't see underlying dashboard |
| No overlay resize | All overlays | Fixed size |
| No overlay pin | All overlays | Auto-close on outside click |

---

## Scrolling

| Problem | Location | Impact |
|---------|----------|--------|
| Anomaly table requires scroll | BDR Dashboard | Important data below fold |
| Floorplan may overflow | Floorplan | On smaller screens |
| Detail panel scroll conflicts | Detail Panel | Nested scrollable areas |
| No scroll-to-top button | Long pages | Must scroll manually |

---

# PART 8 — BUSINESS CRITICAL FEATURES

## Must Never Change

| Feature | Why | Implementation Reference |
|---------|-----|-------------------------|
| **Health Class Color Semantics** | Operators have learned: Green=Good, Red=Bad, Purple=Dead | `DEFAULT_HEATMAP_COLORS` in app.js |
| **64-Slot Grid Layout** | Physical machine has 64 slots — must map 1:1 | Heatmap grid rendering |
| **Real-Time Updates** | Core value proposition — must see live status | 5-second polling interval |
| **Machine Switching** | Must navigate between 40 machines | Machine tabs |
| **Slot Selection → Detail Panel** | Primary investigation workflow | `openDetailPanel()` |
| **BDR Value Range (5-12)** | Business logic — not arbitrary | `BDR_MIN=5.0, BDR_MAX=12.0` |
| **Status Badges (Pass/Fail/Warn)** | Universal status language | Status badge rendering |
| **Diagnostics SSH Connection** | Only way to repair hardware remotely | `/api/machine/{name}/diagnose/connect` |

---

## Should Preserve

| Feature | Why | Implementation Reference |
|---------|-----|-------------------------|
| **Keyboard Shortcuts** | Operator muscle memory (T/F/C/Q/S) | Keyboard event listeners |
| **Filter Logic (Health + Firmware)** | Established workflow | `applyHeatmapFilter()` |
| **Floorplan Zone Structure** | Physical factory layout | `FP_ALL_MACHINES` array |
| **Workout Table Format** | Engineers expect this structure | `dt-cycles` table |
| **Anomaly Severity Levels** | Issue prioritization system | Priority scoring |
| **CSV Export** | Reporting workflow | Export functions |
| **Dark/Light Theme** | Operator preference | Theme toggle |
| **Serial Browser** | Quick lookup workflow | Overlay panel |
| **AI Analysis Report** | Management reporting | Report generation |

---

## Can Improve

| Feature | Why | Current Limitation |
|---------|-----|-------------------|
| **Machine Tab Overflow** | 40+ tabs scroll horizontally | No search, no grouping |
| **Filter Persistence** | Filters reset on machine switch | In-memory only |
| **Detail Panel Layout** | Compresses main content | Fixed 40% width |
| **Chart Interactivity** | Limited zoom/pan | Basic ApexCharts config |
| **Table Sorting** | No column sorting | Static table rendering |
| **Loading States** | No fetch indicators | Stale data shown |
| **Error Messages** | Silent failures | No error UI |
| **Accessibility** | No ARIA, no keyboard nav | Missing attributes |

---

## Can Completely Redesign

| Feature | Why | Current Implementation |
|---------|-----|----------------------|
| **Visual Design** | CSS/styling only | `index.css` — 55K chars |
| **Layout Structure** | HTML template | `index.html` — DOM structure |
| **Typography** | System fonts | CSS font properties |
| **Spacing System** | Inconsistent | Mixed margins/padding |
| **Animation System** | Basic transitions | CSS transitions |
| **Icon System** | Inline SVGs | Embedded in HTML |
| **Color Palette** | Theme colors | CSS custom properties |
| **Responsive Design** | Desktop only | No mobile breakpoints |

---

# PART 9 — OPERATOR MENTAL MODEL

## Primary Mental Model: "Traffic Light System"

```
┌─────────────────────────────────────────────────────────────────┐
│ OPERATOR'S INTERNAL MONITOR                                     │
│                                                                  │
│ THINKING: "Is everything green?"                                │
│                                                                  │
│ IF all green → "Good, monitor passively"                       │
│ IF yellow → "Watch that one, might turn red"                   │
│ IF red → "Investigate immediately"                             │
│ IF purple → "That one's dead, needs attention"                 │
│                                                                  │
│ This maps directly to:                                         │
│   slot-pass (green) → slot-warn (yellow) → slot-danger (red)  │
│   slot-dead (purple)                                          │
└─────────────────────────────────────────────────────────────────┘
```

## Secondary Mental Model: "Machine → Slot → Why"

```
┌─────────────────────────────────────────────────────────────────┐
│ INVESTIGATION SEQUENCE                                          │
│                                                                  │
│ Step 1: "Which MACHINE has problems?"                          │
│   → Scan heatmap, look for cluster of bad colors               │
│   → Or check KPI cards for fleet-wide issues                   │
│                                                                  │
│ Step 2: "Which SLOT on that machine?"                          │
│   → Click red/orange cells to investigate                      │
│   → Review Detail Panel for that slot                          │
│                                                                  │
│ Step 3: "WHY is it failing?"                                   │
│   → Check workout table for BDR values                         │
│   → Check battery chart for patterns                           │
│   → Read warning reason badge                                  │
│                                                                  │
│ Step 4: "What can I DO about it?"                              │
│   → If hardware → Diagnostics View                             │
│   → If software → Document and escalate                        │
│   → If battery → Swap and retest                               │
│                                                                  │
│ Step 5: "Is it FIXED?"                                         │
│   → Watch slot color change in heatmap                         │
│   → Verify BDR returns to normal range                         │
└─────────────────────────────────────────────────────────────────┘
```

## Tertiary Mental Model: "Fleet Health Score"

```
┌─────────────────────────────────────────────────────────────────┐
│ INTUITIVE FLEET ASSESSMENT                                      │
│                                                                  │
│ Operator glances at heatmap and instantly knows:                │
│                                                                  │
│ "Mostly green" → Fleet is healthy, ~90%+ operational          │
│ "Some yellow" → Fleet has issues, ~80-90% operational         │
│ "Many red" → Fleet is struggling, <80% operational            │
│ "Mostly red" → Crisis, need immediate intervention            │
│                                                                  │
│ This is why heatmap is PRIMARY — it's the fleet health gauge   │
└─────────────────────────────────────────────────────────────────┘
```

## Diagnostic Mental Model: "Tool for the Problem"

```
┌─────────────────────────────────────────────────────────────────┐
│ MAINTENANCE TECHNICIAN'S DECISION TREE                         │
│                                                                  │
│ Problem: "Button stuck"                                        │
│   → Tool: Quick Scan → if stuck → MCP Repair                  │
│                                                                  │
│ Problem: "LED not working"                                     │
│   → Tool: LED Diagnose → LED Restore                          │
│                                                                  │
│ Problem: "Bluetooth disconnecting"                             │
│   → Tool: BT Status → BT Connection Check → BT Fix            │
│                                                                  │
│ Problem: "Motor not responding"                                │
│   → Tool: Motor Status → Full Diagnostics                     │
│                                                                  │
│ Problem: "Unknown issue"                                       │
│   → Tool: Full Diagnostics → Analyze results                  │
│                                                                  │
│ Mental model: "Match symptom to tool"                          │
│ Problem: No guided path — must memorize tool-symptom mapping   │
└─────────────────────────────────────────────────────────────────┘
```

## Temporal Mental Model: "Shift Rhythm"

```
┌─────────────────────────────────────────────────────────────────┐
│ OPERATOR'S SHIFT RHYTHM                                         │
│                                                                  │
│ 08:00 - 08:05: "What's the state of play?"                    │
│   → Check KPIs, scan heatmap                                   │
│                                                                  │
│ 08:05 - 11:00: "Monitor and react"                            │
│   → Passive monitoring, react to issues                        │
│                                                                  │
│ 11:00 - 12:00: "Mid-shift check"                              │
│   → Quick status review                                        │
│                                                                  │
│ 12:00 - 15:00: "Afternoon push"                               │
│   → Continue monitoring, address backlog                       │
│                                                                  │
│ 15:00 - 16:00: "Wrap up"                                      │
│   → Generate report, handoff notes                             │
│                                                                  │
│ Mental model: Dashboard is ALWAYS open, checked periodically   │
└─────────────────────────────────────────────────────────────────┘
```

---

# PART 10 — FUTURE SCALABILITY

## Current Scaling Limitations

### 100 Machines (4x Current)

| Component | Current | At 100 Machines | Scaling Issue |
|-----------|---------|-----------------|---------------|
| **Machine Tabs** | 40 tabs (scrollable) | 100 tabs | Unusable — needs search/grouping |
| **Heatmap** | 64 cells × 1 machine | 64 cells × 1 machine | No change (per-machine view) |
| **Floorplan** | 42 positions | 100+ positions | SVG will be too dense |
| **API Response** | ~50KB per machine | ~50KB per machine | No change (per-machine) |
| **Polling** | 5s × 1 machine | 5s × 1 machine | No change (per-machine) |
| **Database** | ~10K records/day | ~40K records/day | May need archiving optimization |

**Breaking Point**: Machine tabs at ~50 machines become unusable.

---

### 500 Machines (12x Current)

| Component | Current | At 500 Machines | Scaling Issue |
|-----------|---------|-----------------|---------------|
| **Machine Tabs** | 40 tabs | 500 tabs | Impossible — needs hierarchy |
| **Fleet Overview** | Single heatmap | Single heatmap | No fleet-wide view exists |
| **API /api/bdr** | Returns all machines | Returns 500 machines | Response size: ~2.5MB |
| **Database Queries** | Simple SELECT | Complex aggregation | Performance degradation |
| **Floorplan** | 42 positions | 500+ positions | Physical layout unclear |
| **AI Report** | Text summary | Massive text | Unreadable |

**Breaking Point**: No fleet-wide aggregation view exists.

---

### Multiple Factories

| Component | Current | Multi-Factory | Scaling Issue |
|-----------|---------|---------------|---------------|
| **Machine Registry** | Single `machines.json` | Multiple registries | No factory grouping |
| **API** | Single endpoint | Multiple endpoints | No factory routing |
| **Database** | Single schema | Multiple schemas | No isolation |
| **Dashboard** | Single view | Multiple views | No factory selector |
| **User Access** | No auth | Factory-level auth | No RBAC |

**Breaking Point**: No concept of "factory" in current system.

---

### Role-Based Users

| Component | Current | RBAC | Scaling Issue |
|-----------|---------|------|---------------|
| **Authentication** | None | Login required | No auth system |
| **Authorization** | None | Role permissions | No role model |
| **UI Visibility** | All features visible | Role-based visibility | No conditional rendering |
| **Diagnostics** | All tools available | Technician-only | No access control |
| **Data Access** | All data visible | Role-based filtering | No data isolation |

**Breaking Point**: No user concept in current system.

---

### Remote Monitoring

| Component | Current | Remote | Scaling Issue |
|-----------|---------|--------|---------------|
| **Network** | Local (172.16.18.x) | WAN/VPN | Latency issues |
| **SSH** | Direct connection | Tunnel/proxy | Connection reliability |
| **Polling** | 5-second | 5-second | Bandwidth consumption |
| **Real-Time** | Synchronous | May need WebSocket | Current SSE may not suffice |
| **Mobile** | Desktop only | Mobile access | No responsive design |

**Breaking Point**: Current architecture assumes local network.

---

## UX Patterns That Won't Scale

| Pattern | Current | 100+ Machines | Issue |
|---------|---------|---------------|-------|
| **Flat Machine List** | Tabs | Tabs | Needs hierarchy/groups |
| **Single Heatmap** | 64 cells | 64 cells | No fleet overview |
| **No Search** | Manual scroll | Manual scroll | Needs machine search |
| **No Filtering** | View one at a time | View one at a time | Needs multi-machine view |
| **No Aggregation** | Per-machine metrics | Per-machine metrics | Needs fleet aggregation |
| **No Alerting** | Passive monitoring | Passive monitoring | Needs push notifications |
| **No Comparison** | Single machine | Single machine | Needs side-by-side |

---

# PART 11 — DESIGN CONSTRAINTS

## Must Preserve

| Constraint | Reason | Implementation Reference |
|------------|--------|-------------------------|
| **64-slot grid layout** | Physical machine has 64 slots — 1:1 mapping | Heatmap rendering |
| **Health class color semantics** | Operators have learned color meanings | `DEFAULT_HEATMAP_COLORS` |
| **Status badge language** | Pass/Fail/Warn is universal | Status rendering |
| **BDR value range (5-12)** | Business logic — not arbitrary | `BDR_MIN=5.0, BDR_MAX=12.0` |
| **Real-time updates (5s)** | Core value — must see live status | Polling interval |
| **Machine switching** | Must navigate 40+ machines | Machine tabs |
| **Slot selection → detail** | Primary investigation flow | `openDetailPanel()` |
| **Keyboard shortcuts** | Operator muscle memory | Event listeners |
| **Filter logic** | Health + firmware AND logic | `applyHeatmapFilter()` |
| **Diagnostics SSH connection** | Only repair method | API endpoint |
| **Workout table format** | Engineers expect this structure | Table rendering |
| **Anomaly severity levels** | Issue prioritization | Priority scoring |

---

## Must Not Break

| Constraint | Reason | Risk if Broken |
|------------|--------|----------------|
| **5-second data refresh** | Operators rely on live data | Missed failures |
| **Heatmap → detail flow** | Investigation workflow | Can't diagnose issues |
| **Machine tab switching** | Navigation foundation | Can't access machines |
| **Filter application** | Issue identification | Can't filter problems |
| **CSV export** | Reporting workflow | Can't generate reports |
| **Diagnostics tools** | Hardware repair | Can't fix machines |
| **Floorplan navigation** | Physical layout understanding | Can't find machines |

---

## Technical Constraints

| Constraint | Reason | Implementation |
|------------|--------|----------------|
| **Vanilla JS** | Current architecture | `app.js` — 6800 LOC |
| **ApexCharts** | Existing chart library | CDN-loaded |
| **D3.js** | Heatmap rendering | Served from `data/` |
| **IndexedDB** | Offline persistence | Client-side storage |
| **FastAPI backend** | API layer | `data/api.py` |
| **PostgreSQL** | Data storage | Connection pool |
| **SSH/Paramiko** | Machine connection | Remote diagnostics |

---

## Business Constraints

| Constraint | Reason | Impact |
|------------|--------|--------|
| **No downtime during redesign** | Production system | Must be incremental |
| **No data migration** | Existing data must be preserved | Schema compatibility |
| **No training budget** | Operators learn by doing | Must be intuitive |
| **No additional hardware** | Works on existing displays | Must fit current screens |
| **No network changes** | Internal network | Must work with existing APIs |

---

# PART 12 — DESIGN OPPORTUNITIES

## Ranked by Impact

### 1. Fleet Overview (Impact: VERY HIGH)

**Current Gap**: No way to see all 40 machines at once without clicking through tabs.

**Opportunity**: Create a fleet-level view that shows aggregate health across all machines.

**Why High Impact**: Supervisors currently have no single screen showing fleet status. They must mentally aggregate from individual machine views.

---

### 2. Alert System (Impact: VERY HIGH)

**Current Gap**: Passive monitoring — operators must watch dashboard constantly.

**Opportunity**: Push notifications when critical failures occur.

**Why High Impact**: Operators can miss failures during busy periods. An alert system would reduce mean time to detection.

---

### 3. Guided Diagnostics (Impact: HIGH)

**Current Gap**: 15+ diagnostic tools with no guidance on which to use.

**Opportunity**: Symptom-based diagnostic workflow.

**Why High Impact**: Technicians must memorize tool-symptom mapping. A guided flow would reduce repair time and errors.

---

### 4. Persistent Filters (Impact: HIGH)

**Current Gap**: Filters reset on machine switch and page reload.

**Opportunity**: Save filter state per machine or per session.

**Why High Impact**: Operators re-apply filters multiple times per shift, wasting time.

---

### 5. Machine Comparison (Impact: HIGH)

**Current Gap**: Can only view one machine at a time.

**Opportunity**: Side-by-side machine comparison.

**Why High Impact**: Engineers investigating systemic issues need to compare machines.

---

### 6. Historical Trends (Impact: HIGH)

**Current Gap**: Only current snapshot — no trend visualization.

**Opportunity**: Time-series charts showing BDR/battery trends over hours/days.

**Why High Impact**: Engineers can't identify gradual degradation patterns.

---

### 7. Responsive Design (Impact: MEDIUM-HIGH)

**Current Gap**: Desktop-only — unusable on tablets/phones.

**Opportunity**: Responsive layout for mobile access.

**Why High Impact**: Supervisors on factory floor need mobile access.

---

### 8. Table Sorting/Filtering (Impact: MEDIUM)

**Current Gap**: Tables are static — no sorting, no pagination.

**Opportunity**: Interactive tables with sort, filter, search.

**Why High Impact**: Large tables (anomaly list) are hard to navigate.

---

### 9. Loading/Error States (Impact: MEDIUM)

**Current Gap**: No visual feedback during API calls or failures.

**Opportunity**: Skeleton loaders, error messages, empty states.

**Why High Impact**: Users see stale data during fetch, don't know if system is working.

---

### 10. Accessibility (Impact: MEDIUM)

**Current Gap**: No ARIA, no keyboard nav, no color-blind support.

**Opportunity**: WCAG compliance, keyboard navigation, pattern+color.

**Why High Impact**: Regulatory compliance, inclusive design.

---

### 11. Export/Reporting (Impact: MEDIUM)

**Current Gap**: CSV only — no PDF, no scheduled reports.

**Opportunity**: Multiple export formats, scheduled reports.

**Why High Impact**: Management reporting requires formatted documents.

---

### 12. Visual Polish (Impact: LOW-MEDIUM)

**Current Gap**: Inconsistent spacing, typography, colors.

**Opportunity**: Design system, consistent styling.

**Why High Impact**: Professional appearance, but not functional.

---

# PART 13 — MISSING INFORMATION

## Cannot Be Determined from Code

### 1. Actual User Behavior

| Missing Info | Why It Matters | Questions to Ask | How Answer Influences Redesign |
|--------------|----------------|------------------|-------------------------------|
| **Which screens do operators actually use?** | Code shows all screens, but usage may be skewed | "Which view do you spend 80% of your time on?" | Prioritize most-used screens |
| **How often are filters used?** | Code implements filters, but usage unknown | "How often do you apply health/firmware filters?" | Decide if filters need prominence |
| **Do operators use keyboard shortcuts?** | Code implements shortcuts, but adoption unknown | "Do you use T/F/C/Q keys?" | Decide if shortcuts need visibility |
| **How long do operators investigate slots?** | Code enables investigation, but duration unknown | "How long do you spend in the detail panel?" | Decide panel complexity |
| **What do operators do when they see a red cell?** | Code enables click, but workflow unknown | "Walk me through what happens when you see a failure." | Design investigation flow |

---

### 2. Feature Usage Frequency

| Missing Info | Why It Matters | Questions to Ask | How Answer Influences Redesign |
|--------------|----------------|------------------|-------------------------------|
| **Which features are never used?** | Dead features add complexity | "Which features do you never use?" | Remove or deprioritize |
| **Which features are used daily?** | Core features need prominence | "Which features do you use every day?" | Make primary |
| **Which features are used weekly?** | Secondary features need accessibility | "Which features do you use weekly?" | Make discoverable |
| **Which features confuse users?** | Confusion = poor UX | "Which features do you find confusing?" | Simplify or remove |

---

### 3. Stakeholder Priorities

| Missing Info | Why It Matters | Questions to Ask | How Answer Influences Redesign |
|--------------|----------------|------------------|-------------------------------|
| **What is the business KPI?** | Design should optimize for it | "What's the #1 metric you care about?" | Make it prominent |
| **What is acceptable downtime?** | Affects reliability requirements | "How long can the dashboard be down?" | Design for availability |
| **What is the budget?** | Affects scope | "What resources are available?" | Scope the redesign |
| **What is the timeline?** | Affects approach | "When must this be done?" | Phase the redesign |
| **What is the success criteria?** | Affects measurement | "How will we know the redesign worked?" | Define metrics |

---

### 4. User Complaints

| Missing Info | Why It Matters | Questions to Ask | How Answer Influences Redesign |
|--------------|----------------|------------------|-------------------------------|
| **What frustrates users most?** | Pain points drive improvement | "What's the most frustrating part?" | Prioritize fixes |
| **What do users wish existed?** | Unmet needs = opportunities | "What feature do you wish you had?" | Add capabilities |
| **What workarounds exist?** | Workarounds = design failures | "What shortcuts do you use?" | Formalize patterns |
| **What causes errors?** | Errors = poor UX | "What mistakes do you make?" | Add prevention |

---

### 5. Factory Environment

| Missing Info | Why It Matters | Questions to Ask | How Answer Influences Redesign |
|--------------|----------------|------------------|-------------------------------|
| **Display size and type?** | Affects layout and density | "What monitors do you use?" | Design for actual displays |
| **Lighting conditions?** | Affects color and contrast | "Is the area well-lit?" | Adjust color palette |
| **Noise level?** | Affects audio cues | "Is it noisy?" | Visual-only feedback |
| **Internet speed?** | Affects data loading | "What's your network speed?" | Optimize payload |
| **Browser used?** | Affects compatibility | "Which browser do you use?" | Test compatibility |

---

### 6. Operational Policies

| Missing Info | Why It Matters | Questions to Ask | How Answer Influences Redesign |
|--------------|----------------|------------------|-------------------------------|
| **Shift handoff process?** | Affects reporting features | "How do you hand off to next shift?" | Design handoff tools |
| **Escalation procedure?** | Affects alert design | "Who do you call when something fails?" | Design escalation flow |
| **Documentation requirements?** | Affects export features | "What reports must you generate?" | Design report templates |
| **Audit requirements?** | Affects data retention | "How long must data be kept?" | Design archival |

---

### 7. Future Roadmap

| Missing Info | Why It Matters | Questions to Ask | How Answer Influences Redesign |
|--------------|----------------|------------------|-------------------------------|
| **Planned machine additions?** | Affects scaling | "How many machines will be added?" | Design for growth |
| **New test types?** | Affects data model | "Will new test types be added?" | Design for extensibility |
| **Integration plans?** | Affects API design | "Will this integrate with other systems?" | Design for APIs |
| **Mobile requirements?** | Affects responsive design | "Will operators use tablets/phones?" | Design for mobile |
| **AI/ML plans?** | Affects architecture | "Will predictive analytics be added?" | Design for intelligence |

---

## Summary of Missing Information

| Category | Items Missing | Priority |
|----------|---------------|----------|
| **User Behavior** | 5 items | HIGH — directly impacts design decisions |
| **Feature Usage** | 4 items | HIGH — determines what to keep/remove |
| **Stakeholder Priorities** | 5 items | HIGH — scopes the redesign |
| **User Complaints** | 4 items | HIGH — identifies pain points |
| **Factory Environment** | 5 items | MEDIUM — affects layout decisions |
| **Operational Policies** | 4 items | MEDIUM — affects workflow design |
| **Future Roadmap** | 5 items | MEDIUM — affects scalability |

**Total**: 32 items of missing information that would significantly influence the redesign.

---

# APPENDIX A: Code References

This report references the following implementation artifacts:

| Artifact | Location | Purpose |
|----------|----------|---------|
| `app.js` | `D:\BDR\app.js` | Frontend logic (6800 lines) |
| `index.html` | `D:\BDR\index.html` | HTML template |
| `index.css` | `D:\BDR\index.css` | CSS styles |
| `api.py` | `D:\BDR\data\api.py` | FastAPI backend |
| `main.py` | `D:\BDR\data\main.py` | Data collection |
| `postgres_db.py` | `D:\BDR\data\postgres_db.py` | Database layer |
| `diagnostics.py` | `D:\BDR\data\diagnostics.py` | SSH diagnostics |
| `machines.json` | `D:\BDR\machines.json` | Machine registry |

---

# APPENDIX B: Glossary

| Term | Definition |
|------|------------|
| **BDR** | Battery Discharge Rate — percentage of battery capacity discharged per hour |
| **AQC** | Assembly Quality Control — hardware test machine |
| **Ring** | Physical slot holding a battery during testing |
| **Slot** | Logical position in a ring (64 per machine) |
| **Workout** | Complete discharge cycle from 100% to target percentage |
| **Health Class** | Classification of slot state (pass, ok, warn, danger, dead, etc.) |
| **MCP** | MCP23017 — I2C GPIO expander chip for button scanning |
| **SFTP** | Secure File Transfer Protocol — used for data collection |
| **Paramiko** | Python SSH library used for remote machine access |
| **ApexCharts** | JavaScript charting library used for line/bar/doughnut charts |
| **D3.js** | JavaScript library for data visualization (heatmap) |

---

**End of Report**

*This document represents a comprehensive UX discovery analysis of the BDR Dashboard system, prepared to inform a redesign initiative without proposing specific design solutions.*
