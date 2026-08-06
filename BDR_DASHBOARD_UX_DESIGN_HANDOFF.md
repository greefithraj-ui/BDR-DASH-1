# BDR Dashboard - UI/UX Design Handoff Document

**Version**: 1.0  
**Date**: July 2026  
**Purpose**: Enable product designers to redesign the dashboard without reading code

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Screen-by-Screen Breakdown](#2-screen-by-screen-breakdown)
3. [Widget Inventory](#3-widget-inventory)
4. [User Workflow](#4-user-workflow)
5. [Widget Hierarchy](#5-widget-hierarchy)
6. [Information Hierarchy](#6-information-hierarchy)
7. [Interaction Flows](#7-interaction-flows)
8. [Navigation Map](#8-navigation-map)
9. [Widget Dependencies](#9-widget-dependencies)
10. [Filters and Affected Widgets](#10-filters-and-affected-widgets)
11. [Drill-Down Interactions](#11-drill-down-interactions)
12. [Modal and Overlay Behavior](#12-modal-and-overlay-behavior)
13. [Keyboard Shortcuts](#13-keyboard-shortcuts)
14. [Live Update Behavior](#14-live-update-behavior)
15. [Business-Critical UI Elements](#15-business-critical-ui-elements)
16. [Redesignable UI Elements](#16-redesignable-ui-elements)
17. [Semantic Colors](#17-semantic-colors)
18. [Priority Metrics](#18-priority-metrics)
19. [Current UX Pain Points](#19-current-ux-pain-points)
20. [Designer's Mental Model](#20-designers-mental-model)

---

## 1. Executive Summary

### What is BDR Dashboard?

The BDR (Battery Discharge Rate) Dashboard is a **real-time industrial monitoring system** for tracking battery discharge testing across a fleet of **40 AQC (Assembly Quality Control) hardware machines**. Each machine contains **64 ring slots** where batteries undergo discharge testing.

### Primary Users

| User Type | Role | Primary Goals |
|-----------|------|---------------|
| **Test Operators** | Monitor ongoing tests | Spot failures quickly, identify problematic slots |
| **Quality Engineers** | Analyze test results | Identify patterns, root-cause failures |
| **Maintenance Technicians** | Fix hardware issues | Diagnose hardware faults, repair MCP/LED/BT |
| **Shift Supervisors** | Oversee fleet status | Track throughput, identify bottlenecks |

### Core Value Proposition

> "At a glance, know which of the 2,560 battery slots (40 machines × 64 slots) are passing, failing, or need attention."

---

## 2. Screen-by-Screen Breakdown

### Screen Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              HEADER BAR                                      │
│  [Logo] [Machine Tabs: aqc-34 | aqc-37 | ... | aqc-48] [View Toggle] [T] │
├─────────────────────────────────────────────────────────────────────────────┤
│                              MAIN CONTENT                                    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                        5 MAIN VIEWS                                      ││
│  │  [BDR Dashboard] [Ring Slots] [Data Viz] [Diagnostics] [Old Data]     ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                        OVERLAY PANELS                                    ││
│  │  [Floorplan] [Serial Browser] [Cycle Analysis] [AI Report]             ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                        DETAIL PANEL (Right Side)                        ││
│  │  [Slot Details] [Workout Table] [Battery/Current Chart]                ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 2.1 BDR Dashboard View (Primary Screen)

**Purpose**: Real-time fleet monitoring with heatmap overview

**Layout**:
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ KPI CARDS (4 across)                                                         │
│ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐                           │
│ │ Total   │ │ Avg     │ │ Avg     │ │ Serials │                           │
│ │ Slots   │ │ Battery │ │ BDR     │ │ (Unique)│                           │
│ │ 2,048   │ │ 87.3%   │ │ 8.2     │ │ 1,842   │                           │
│ └─────────┘ └─────────┘ └─────────┘ └─────────┘                           │
├─────────────────────────────────────────────────────────────────────────────┤
│ FILTER BAR                                                                   │
│ [Health Class Filters: ○ Pass ○ OK ○ Warn ○ Danger ○ Dead ○ Empty ...]     │
│ [Firmware Filters: ○ v1.2 ○ v1.3 ○ v1.4]                                  │
│ [Color Customization: ●●●●●●●●●●]                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│ HEATMAP GRID (64 cells, 16×4 layout)                  │ CHARTS (Right)      │
│ ┌──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┐  │ ┌─────────────────┐│
│ │01│02│03│04│05│06│07│08│09│10│11│12│13│14│15│16│  │ │ Phase Dist.     ││
│ ├──┼──┼──┼──┼──┼──┼──┼──┼──┼──┼──┼──┼──┼──┼──┼──┤  │ │ (Horizontal Bar)││
│ │17│18│19│20│21│22│23│24│25│26│27│28│29│30│31│32│  │ ├─────────────────┤│
│ ├──┼──┼──┼──┼──┼──┼──┼──┼──┼──┼──┼──┼──┼──┼──┼──┤  │ │ Battery Dist.   ││
│ │33│34│35│36│37│38│39│40│41│42│43│44│45│46│47│48│  │ │ (Vertical Bar)  ││
│ ├──┼──┼──┼──┼──┼──┼──┼──┼──┼──┼──┼──┼──┼──┼──┼──┤  │ └─────────────────┘│
│ │49│50│51│52│53│54│55│56│57│58│59│60│61│62│63│64│  │                     │
│ └──┴──┴──┴──┴──┴──┴──┴──┴──┴──┴──┴──┴──┴──┴──┴──┘  │                     │
├─────────────────────────────────────────────────────────────────────────────┤
│ SPOTLIGHT ANOMALIES (Up to 6 cards)           │ ANOMALY TABLE (Full list)  │
│ ┌─────────┐ ┌─────────┐ ┌─────────┐           │ ┌─────────────────────────┐│
│ │Slot 12  │ │Slot 45  │ │Slot 8   │           │ │Slot│MAC│Serial│Severity ││
│ │CRITICAL │ │WARNING  │ │WARNING  │           │ │ 12 │.. │..    │🔴 HIGH  ││
│ │Slanting │ │High BDR │ │Dead     │           │ │ 45 │.. │..    │🟡 MED   ││
│ └─────────┘ └─────────┘ └─────────┘           │ └─────────────────────────┘│
├─────────────────────────────────────────────────────────────────────────────┤
│ BOTTOM SECTION (Collapsible)                                                 │
│ [BDR History Line Chart] [Battery Doughnut] [Workouts Table] [Diagnostics] │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Widgets on this screen**:

| Widget | Position | Purpose | Refresh Rate |
|--------|----------|---------|--------------|
| KPI Cards (4) | Top | Fleet-wide summary metrics | 5 seconds |
| Health Class Filters | Below KPIs | Filter heatmap by slot health status | User-triggered |
| Firmware Filters | Below KPIs | Filter heatmap by firmware version | User-triggered |
| Heatmap Grid | Center-left | Visual representation of 64 slots | 5 seconds |
| Phase Distribution Chart | Center-right | Bar chart showing slot phases | 5 seconds |
| Battery Distribution Chart | Center-right | Histogram of battery levels | 5 seconds |
| Spotlight Anomalies | Below heatmap | Top 6 critical/warning slots | 5 seconds |
| Anomaly Table | Below heatmap | Full list of all anomalies | 5 seconds |
| BDR History Chart | Bottom | Line chart of BDR over time | 5 seconds |
| Battery Doughnut | Bottom | Pie chart of battery distribution | 5 seconds |
| Workouts Table | Bottom | List of recent workouts | 5 seconds |
| Diagnostics Summary | Bottom | Hardware diagnostics overview | 5 seconds |

---

### 2.2 Ring Slots View

**Purpose**: Ring-specific monitoring with status tracking

**Layout**:
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ STATS KPI CARDS (5 across)                                                   │
│ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐               │
│ │ Total   │ │ Running │ │ Passed  │ │ Failed  │ │ Assigned│               │
│ │ 2,048   │ │ 1,200   │ │ 800     │ │ 48      │ │ 1,848   │               │
│ └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘               │
├─────────────────────────────────────────────────────────────────────────────┤
│ FILTER BAR                                                                   │
│ [Status: ○ All ○ Running ○ Passed ○ Failed ○ Assigned]                     │
│ [Search: _______________] [Export CSV]                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│ RING GRID (64 cells, 16×4 layout)                                          │
│ ┌──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┐                        │
│ │01│02│03│04│05│06│07│08│09│10│11│12│13│14│15│16│                        │
│ ├──┼──┼──┼──┼──┼──┼──┼──┼──┼──┼──┼──┼──┼──┼──┼──┤                        │
│ │..│..│..│..│..│..│..│..│..│..│..│..│..│..│..│..│                        │
│ └──┴──┴──┴──┴──┴──┴──┴──┴──┴──┴──┴──┴──┴──┴──┴──┘                        │
├─────────────────────────────────────────────────────────────────────────────┤
│ DETAIL PANEL (Right side, when slot selected)                               │
│ [Slot Info] [Ring Status] [Serial] [MAC] [Firmware]                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Widgets on this screen**:

| Widget | Position | Purpose | Refresh Rate |
|--------|----------|---------|--------------|
| Stats KPI Cards (5) | Top | Ring status summary | 5 seconds |
| Status Filters | Below KPIs | Filter by ring status | User-triggered |
| Search Input | Below KPIs | Search by serial/MAC | User-triggered |
| Export Button | Below KPIs | Export filtered data to CSV | User-triggered |
| Ring Grid | Center | Visual representation of 64 rings | 5 seconds |
| Detail Panel | Right | Selected ring details | On selection |

---

### 2.3 Data Visualization View

**Purpose**: Serial number analytics and category breakdown

**Layout**:
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ CATEGORY TABS                                                                │
│ [All] [Production] [RT Conversion] [Wabi Sabi]                             │
├─────────────────────────────────────────────────────────────────────────────┤
│ SUMMARY STATS                                                                │
│ Total Serials: 1,842 | Production: 1,600 | RT Conv: 200 | Wabi Sabi: 42   │
├─────────────────────────────────────────────────────────────────────────────┤
│ SKU BREAKDOWN CHART (Bar chart)                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐│
│ │ ████████████████████████████  WB-24 (800)                              ││
│ │ ████████████████████████  WB-32 (600)                                  ││
│ │ ████████████████  STD-24 (400)                                         ││
│ └─────────────────────────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────────────────────┤
│ SERIAL TABLE                                                                │
│ ┌─────────────────────────────────────────────────────────────────────────┐│
│ │ Serial      │ Machine │ Slot │ Status │ BDR   │ Workouts │ Last Update││
│ │ XXX-XXX-XX  │ aqc-34  │ 12   │ ✅ Pass│ 8.2   │ 6        │ 2026-07-18││
│ └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

**Widgets on this screen**:

| Widget | Position | Purpose | Refresh Rate |
|--------|----------|---------|--------------|
| Category Tabs | Top | Filter by serial category | User-triggered |
| Summary Stats | Below tabs | Category counts | On category change |
| SKU Breakdown Chart | Center | Bar chart of SKU distribution | On category change |
| Serial Table | Bottom | Detailed serial list | On category change |

---

### 2.4 Diagnostics View

**Purpose**: Remote hardware diagnostics and repair

**Layout**:
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ MACHINE SELECTOR                                                             │
│ [Select Machine: ▼ aqc-34] [Connect] [Disconnect]                          │
├─────────────────────────────────────────────────────────────────────────────┤
│ STATUS BAR                                                                   │
│ Connection: ✅ Connected | Last Scan: 2026-07-18 14:32 | Firmware: v1.3    │
├─────────────────────────────────────────────────────────────────────────────┤
│ BUTTON GRID (64 cells, 8×8)                                                │
│ ┌──┬──┬──┬──┬──┬──┬──┬──┐                                                  │
│ │01│02│03│04│05│06│07│08│                                                  │
│ ├──┼──┼──┼──┼──┼──┼──┼──┤                                                  │
│ │..│..│..│..│..│..│..│..│                                                  │
│ └──┴──┴──┴──┴──┴──┴──┴──┘                                                  │
│ Legend: 🟢 Released | 🔴 Pressed | 🟡 Unknown                              │
├─────────────────────────────────────────────────────────────────────────────┤
│ CONTROL PANEL                                                                │
│ [Quick Scan] [Live Monitor] [Stop Monitor]                                 │
│                                                                              │
│ LED CONTROL                                                                  │
│ [Color Picker] [Fill] [Set] [Off] [Restore] [Diagnose]                    │
├─────────────────────────────────────────────────────────────────────────────┤
│ EXTENDED DIAGNOSTICS (Collapsible)                                          │
│ [MCP Scan] [MCP Repair] [Advanced Repair] [Full Diagnostics]              │
│ [Motor Status] [Bluetooth Status] [BT Reset] [BT Recover]                 │
│ [Audit Folders] [Audit Processes] [System Check]                           │
├─────────────────────────────────────────────────────────────────────────────┤
│ LIVE LOG MONITOR (Collapsible)                                              │
│ ┌─────────────────────────────────────────────────────────────────────────┐│
│ │ 14:32:01 [INFO] Button scan completed                                  ││
│ │ 14:32:02 [WARN] MCP register 0x23 corrupted                           ││
│ │ 14:32:03 [ERROR] Bluetooth adapter not responding                      ││
│ └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

**Widgets on this screen**:

| Widget | Position | Purpose | Refresh Rate |
|--------|----------|---------|--------------|
| Machine Selector | Top | Choose machine to diagnose | User-triggered |
| Status Bar | Below selector | Connection and firmware info | On connect |
| Button Grid | Center | Visual button press states | 1 second (live) |
| Quick Scan Button | Below grid | Single button scan | User-triggered |
| Live Monitor Button | Below grid | Start 1-second polling | User-triggered |
| LED Control Panel | Below grid | Control slot LEDs | User-triggered |
| Extended Diagnostics | Below LED | Hardware repair tools | User-triggered |
| Live Log Monitor | Bottom | Real-time log streaming | 2 seconds |

---

### 2.5 Old Data View

**Purpose**: Search historical archive data

**Layout**:
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ SEARCH MODE TOGGLE                                                           │
│ [Single Serial] [Bulk Serials]                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│ SEARCH INPUT                                                                 │
│ Serial Number(s): [________________] [Search] [Clear]                      │
│                                                                              │
│ Bulk Mode: [________________] (comma/newline separated)                     │
├─────────────────────────────────────────────────────────────────────────────┤
│ RESULTS TABLE                                                                │
│ ┌─────────────────────────────────────────────────────────────────────────┐│
│ │ Serial      │ Machine │ Slot │ Status │ Avg BDR │ Cycles │ First Seen ││
│ │ XXX-XXX-XX  │ aqc-34  │ 12   │ ✅ Pass│ 8.2     │ 6      │ 2026-07-01││
│ └─────────────────────────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────────────────────┤
│ EXPORT OPTIONS                                                               │
│ [Export Results CSV] [Export All Serials CSV]                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Widgets on this screen**:

| Widget | Position | Purpose | Refresh Rate |
|--------|----------|---------|--------------|
| Search Mode Toggle | Top | Switch single/bulk mode | User-triggered |
| Search Input | Below toggle | Enter serial number(s) | User-triggered |
| Results Table | Center | Search results | On search |
| Export Buttons | Bottom | Export to CSV | User-triggered |

---

### 2.6 Overlay Panels

#### 2.6.1 Floorplan Overlay

**Purpose**: Physical layout visualization of AQC machines

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ FLOORPLAN                                                                    │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │                        ZONE A (Blue)                                    ││
│  │  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐                             ││
│  │  │aqc-1│ │aqc-2│ │aqc-3│ │aqc-4│ │aqc-5│  ... (20 positions)        ││
│  │  │ 32  │ │ 48  │ │ 0   │ │ 64  │ │ 16  │                             ││
│  │  └─────┘ └─────┘ └─────┘ └─────┘ └─────┘                             ││
│  ├─────────────────────────────────────────────────────────────────────────┤│
│  │                        ZONE B (Green)                                   ││
│  │  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐                                     ││
│  │  │aqc-6│ │aqc-7│ │aqc-8│ │aqc-9│  ... (8 positions)                 ││
│  │  │ 48  │ │ 32  │ │ 64  │ │ 0   │                                     ││
│  │  └─────┘ └─────┘ └─────┘ └─────┘                                     ││
│  ├─────────────────────────────────────────────────────────────────────────┤│
│  │                        ZONE C (Orange)                                  ││
│  │  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐                                     ││
│  │  │aqc-10│ │aqc-11│ │aqc-12│ │aqc-13│  ... (8 positions)             ││
│  │  └─────┘ └─────┘ └─────┘ └─────┘                                     ││
│  ├─────────────────────────────────────────────────────────────────────────┤│
│  │                        ZONE D (Purple)                                  ││
│  │  ┌─────┐ ┌─────┐ ┌─────┐                                              ││
│  │  │aqc-14│ │aqc-15│ │aqc-16│  ... (6 positions)                       ││
│  │  └─────┘ └─────┘ └─────┘                                              ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
│  LEGEND                                                                      │
│  🟥 0 slots | 🟨 32 slots | 🟩 64 slots                                  │
│                                                                              │
│  UNMAPPED MACHINES                                                           │
│  [aqc-17] [aqc-18] [aqc-19] ...                                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Widgets on this screen**:

| Widget | Position | Purpose | Refresh Rate |
|--------|----------|---------|--------------|
| Zone Sections | Center | Group machines by physical location | Static |
| Machine Boxes | Within zones | Show slot count with color coding | 5 seconds |
| Legend | Below zones | Explain color meanings | Static |
| Unmapped Machines | Bottom | Machines not assigned to positions | 5 seconds |

**Interactions**:
- **Click machine box**: Navigate to that machine's BDR Dashboard
- **Right-click machine box**: Context menu to assign/unassign machine
- **Search**: Filter machines by name

---

#### 2.6.2 Serial Browser Overlay

**Purpose**: Search and navigate to specific serial numbers

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ SERIAL BROWSER                                              [X Close]       │
├─────────────────────────────────────────────────────────────────────────────┤
│ SEARCH                                                                       │
│ [Single Mode] [Bulk Mode]                                                   │
│                                                                              │
│ Serial: [________________] [Search]                                         │
│                                                                              │
│ Category Filter: [All ▼]                                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│ RESULTS (Highlighted matches)                                                │
│ ┌─────────────────────────────────────────────────────────────────────────┐│
│ │ Serial      │ Machine │ Slot │ Status │ MAC        │ Firmware          ││
│ │ XXX-XXX-XX  │ aqc-34  │ 12   │ ✅ Pass│ AA:BB:CC   │ v1.3             ││
│ └─────────────────────────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────────────────────┤
│ DUPLICATE DETECTION (if found)                                              │
│ ⚠️ Duplicate found in: aqc-34:12, aqc-45:8                                │
│ [Go to aqc-34:12] [Go to aqc-45:8]                                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

#### 2.6.3 Cycle Analysis Overlay

**Purpose**: Workout distribution analysis across fleet

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ CYCLE ANALYSIS                                              [X Close]       │
├─────────────────────────────────────────────────────────────────────────────┤
│ WORKOUT DISTRIBUTION (Histogram)                                            │
│ ┌─────────────────────────────────────────────────────────────────────────┐│
│ │ 0 workouts: ████████████████████ (500 slots)                           ││
│ │ 1 workout:  ████████████ (300 slots)                                   ││
│ │ 2 workouts: ████████ (200 slots)                                       ││
│ │ 3 workouts: ██████ (150 slots)                                         ││
│ │ 4 workouts: ████ (100 slots)                                           ││
│ │ 5 workouts: ██ (50 slots)                                              ││
│ │ 6+ workouts: █ (20 slots)                                              ││
│ └─────────────────────────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────────────────────┤
│ PER-MACHINE BREAKDOWN                                                       │
│ ┌─────────────────────────────────────────────────────────────────────────┐│
│ │ Machine   │ Total Slots │ Occupied │ 0 WS │ 1 WS │ ... │ 6+ WS      ││
│ │ aqc-34    │ 64          │ 60       │ 5    │ 10   │ ... │ 2           ││
│ │ aqc-37    │ 64          │ 58       │ 8    │ 12   │ ... │ 1           ││
│ └─────────────────────────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────────────────────┤
│ GRAND TOTALS                                                                │
│ Total Slots: 2,048 | Occupied: 1,842 | Avg Workouts: 3.2                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

#### 2.6.4 AI Analysis Report Overlay

**Purpose**: Automated fleet analysis with recommendations

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ AI ANALYSIS REPORT                                           [X Close]      │
├─────────────────────────────────────────────────────────────────────────────┤
│ FLEET OVERVIEW                                                               │
│ Machines: 40 | Slots: 2,048 | Running: 1,200 | Passed: 800 | Failed: 48   │
├─────────────────────────────────────────────────────────────────────────────┤
│ ⚠️ ALERTS                                                                    │
│ • aqc-34: 18 problematic slots (>15 threshold)                            │
│ • aqc-45: 12 dead slots (>10 threshold)                                   │
│ • aqc-48: 14 empty slots (>10 threshold)                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│ ANOMALY BREAKDOWN (Top 30)                                                  │
│ ┌─────────────────────────────────────────────────────────────────────────┐│
│ │ Slot    │ Severity │ Type           │ Description                      ││
│ │ aqc-34:12│ 🔴 HIGH  │ Slanting Leak  │ Gradual drain after workout     ││
│ │ aqc-45:8 │ 🔴 HIGH  │ Dead           │ Battery <3% for >3hr           ││
│ └─────────────────────────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────────────────────┤
│ MACHINE STATUS (Sorted by issue weight)                                     │
│ ┌─────────────────────────────────────────────────────────────────────────┐│
│ │ Machine   │ Issues │ Failed │ Dead │ Anomalies │ Weight │ Status      ││
│ │ aqc-34    │ 18     │ 5      │ 3    │ 10        │ 85     │ ⚠️ Attention││
│ │ aqc-45    │ 15     │ 4      │ 4    │ 7         │ 72     │ ⚠️ Attention││
│ └─────────────────────────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────────────────────┤
│ MACHINES REQUIRING ATTENTION                                                 │
│ [aqc-34] [aqc-45] [aqc-48]                                                │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Widget Inventory

### 3.1 Global Widgets (Present on all screens)

| Widget | Location | Purpose | Data Source | Refresh |
|--------|----------|---------|-------------|---------|
| Machine Tabs | Header | Switch between machines | machines.json | Static |
| View Toggle | Header | Switch between 5 views | User selection | On click |
| Theme Toggle (T) | Header | Dark/light mode | localStorage | On click |
| Floorplan Button | Header | Toggle floorplan overlay | User selection | On click |
| Serial Browser Button (Q) | Header | Toggle serial browser | User selection | On click |
| Cycle Analysis Button | Header | Toggle cycle analysis | User selection | On click |
| AI Report Button | Header | Toggle AI analysis | User selection | On click |

### 3.2 BDR Dashboard Widgets

| Widget | Position | Purpose | Data Source | Refresh |
|--------|----------|---------|-------------|---------|
| KPI Card: Total Slots | Top-left | Fleet-wide slot count | BDR API | 5s |
| KPI Card: Avg Battery | Top-center-left | Average battery level | BDR API | 5s |
| KPI Card: Avg BDR | Top-center-right | Average discharge rate | BDR API | 5s |
| KPI Card: Serials | Top-right | Unique serial count | BDR API | 5s |
| Health Class Filters | Below KPIs | Filter by health status | User selection | On click |
| Firmware Filters | Below KPIs | Filter by firmware version | User selection | On click |
| Heatmap Grid | Center-left | 64-slot visual status | BDR API | 5s |
| Phase Distribution Chart | Center-right | Bar chart of phases | BDR API | 5s |
| Battery Distribution Chart | Center-right | Histogram of batteries | BDR API | 5s |
| Spotlight Anomalies | Below heatmap | Top 6 critical slots | BDR API | 5s |
| Anomaly Table | Below heatmap | Full anomaly list | BDR API | 5s |
| BDR History Chart | Bottom | Line chart over time | BDR API | 5s |
| Battery Doughnut | Bottom | Pie chart of distribution | BDR API | 5s |
| Workouts Table | Bottom | Recent workout list | BDR API | 5s |
| Diagnostics Summary | Bottom | Hardware status overview | Diagnostics API | 5s |

### 3.3 Ring Slots Widgets

| Widget | Position | Purpose | Data Source | Refresh |
|--------|----------|---------|-------------|---------|
| Stats KPI Cards (5) | Top | Ring status counts | Rings API | 5s |
| Status Filters | Below KPIs | Filter by ring status | User selection | On click |
| Search Input | Below KPIs | Search by serial/MAC | User input | On type |
| Export Button | Below KPIs | Export to CSV | User selection | On click |
| Ring Grid | Center | 64-ring visual status | Rings API | 5s |
| Detail Panel | Right | Selected ring details | Rings API | On selection |

### 3.4 Data Visualization Widgets

| Widget | Position | Purpose | Data Source | Refresh |
|--------|----------|---------|-------------|---------|
| Category Tabs | Top | Filter by serial category | User selection | On click |
| Summary Stats | Below tabs | Category counts | BDR API | On category |
| SKU Breakdown Chart | Center | Bar chart of SKUs | BDR API | On category |
| Serial Table | Bottom | Detailed serial list | BDR API | On category |

### 3.5 Diagnostics Widgets

| Widget | Position | Purpose | Data Source | Refresh |
|--------|----------|---------|-------------|---------|
| Machine Selector | Top | Choose machine | machines.json | On select |
| Status Bar | Below selector | Connection info | Diagnostics API | On connect |
| Button Grid | Center | 64-button press states | Diagnostics API | 1s (live) |
| Quick Scan Button | Below grid | Single scan | User trigger | On click |
| Live Monitor Button | Below grid | Start polling | User trigger | On click |
| LED Control Panel | Below grid | LED color control | User trigger | On click |
| Extended Diagnostics | Below LED | Hardware repair tools | User trigger | On click |
| Live Log Monitor | Bottom | Real-time logs | Diagnostics API | 2s |

### 3.6 Old Data Widgets

| Widget | Position | Purpose | Data Source | Refresh |
|--------|----------|---------|-------------|---------|
| Search Mode Toggle | Top | Single/bulk mode | User selection | On click |
| Search Input | Below toggle | Enter serial(s) | User input | On type |
| Results Table | Center | Search results | Old Data API | On search |
| Export Buttons | Bottom | Export to CSV | User trigger | On click |

---

## 4. User Workflow

### 4.1 Operator Daily Workflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ SHIFT START (08:00)                                                          │
│                                                                              │
│ 1. Open Dashboard                                                            │
│ 2. Check KPI Cards for fleet overview                                       │
│ 3. Scan Heatmap for red/orange slots (failures/warnings)                   │
│ 4. Note any CRITICAL anomalies in Spotlight section                         │
│                                                                              │
│ IF critical issues found:                                                    │
│   → Click heatmap slot to open Detail Panel                                 │
│   → Review workout table and battery chart                                  │
│   → If hardware issue: Switch to Diagnostics View                          │
│   → Connect to machine and run Quick Scan                                  │
│   → If MCP/LED issue: Run repair tools                                     │
│                                                                              │
│ IF no critical issues:                                                       │
│   → Monitor progress via BDR History Chart                                  │
│   → Check Floorplan for machine status                                      │
│   → Review Cycle Analysis for throughput                                    │
│                                                                              │
│ EVERY 5 MINUTES:                                                             │
│   → Glance at KPI Cards for changes                                         │
│   → Check heatmap for new failures                                          │
│                                                                              │
│ SHIFT END (16:00):                                                           │
│   → Generate AI Analysis Report                                             │
│   → Export anomalies for shift report                                       │
│   → Note any persistent issues for next shift                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Engineer Investigation Workflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ INVESTIGATION: Why is slot failing?                                          │
│                                                                              │
│ 1. Click failing slot in Heatmap                                             │
│ 2. Review Detail Panel:                                                      │
│    - Workout table: Check BDR values                                        │
│    - Battery chart: Look for flat lines (sensor issues)                    │
│    - Check for slanting leak badge                                          │
│                                                                              │
│ 3. IF pattern suspicious:                                                    │
│    → Switch to Data Visualization View                                      │
│    → Search serial in Old Data View                                         │
│    → Check historical performance                                           │
│                                                                              │
│ 4. IF hardware suspected:                                                    │
│    → Switch to Diagnostics View                                             │
│    → Connect to machine                                                     │
│    → Run Quick Scan to check button states                                  │
│    → Run MCP Scan if register issues suspected                             │
│    → Check Live Logs for errors                                             │
│                                                                              │
│ 5. IF systemic issue:                                                        │
│    → Check other slots on same machine                                      │
│    → Compare with other machines in Floorplan                               │
│    → Generate AI Report for fleet-wide patterns                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.3 Maintenance Technician Workflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ HARDWARE REPAIR WORKFLOW                                                     │
│                                                                              │
│ 1. Receive repair request (from operator/engineer)                          │
│                                                                              │
│ 2. Open Diagnostics View                                                    │
│ 3. Select machine from dropdown                                             │
│ 4. Click Connect                                                             │
│    → Status bar shows connection status                                     │
│                                                                              │
│ 5. Run Quick Scan                                                            │
│    → Button grid updates with press/release states                          │
│    → Red cells = pressed (stuck?)                                           │
│    → Green cells = released (normal)                                        │
│                                                                              │
│ 6. IF button issue:                                                          │
│    → Run Button Advanced Repair                                             │
│    → Re-scan to verify fix                                                  │
│                                                                              │
│ 7. IF MCP register issue:                                                    │
│    → Run MCP Scan                                                           │
│    → Check for corrupted registers                                          │
│    → Run MCP Repair                                                         │
│    → If still broken: Run Advanced Repair                                  │
│                                                                              │
│ 8. IF LED issue:                                                             │
│    → Use LED Control Panel                                                  │
│    → Set color to verify LED functionality                                  │
│    → Run LED Diagnose for full test                                         │
│                                                                              │
│ 9. IF Bluetooth issue:                                                       │
│    → Check BT Status                                                        │
│    → Run BT Connection Check                                                │
│    → If crash loop: Run BT Fix Crash Loop                                  │
│    → If pairing issue: Run BT Fix Pairing Popup                            │
│                                                                              │
│ 10. Monitor Live Logs during repair                                         │
│     → Watch for error messages                                              │
│     → Verify repair success                                                 │
│                                                                              │
│ 11. After repair:                                                            │
│     → Return to BDR Dashboard                                               │
│     → Verify slot status improves                                           │
│     → Document repair in logs                                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Widget Hierarchy

### 5.1 Visual Hierarchy (BDR Dashboard)

```
LEVEL 1 (Most Prominent)
├── Heatmap Grid (center, largest element)
├── KPI Cards (top, high contrast)
└── Spotlight Anomalies (high visibility)

LEVEL 2 (Secondary)
├── Phase Distribution Chart
├── Battery Distribution Chart
├── Anomaly Table
└── Filter Bar

LEVEL 3 (Tertiary)
├── BDR History Chart
├── Battery Doughnut
├── Workouts Table
└── Diagnostics Summary

LEVEL 4 (Supplementary)
├── Machine Tabs
├── View Toggle
├── Theme Toggle
└── Overlay Buttons
```

### 5.2 Information Density Map

```
HIGH DENSITY (Information Rich)
├── Heatmap Grid (64 data points + colors + hover details)
├── Anomaly Table (multiple columns per row)
├── Workout Table (multiple columns per row)
└── Detail Panel (multiple data fields)

MEDIUM DENSITY
├── KPI Cards (single number + label)
├── Phase Distribution Chart (categorical data)
├── Battery Distribution Chart (binned data)
└── Floorplan (spatial + color coding)

LOW DENSITY (Simple)
├── Machine Tabs (names only)
├── View Toggle (5 buttons)
├── Filter Buttons (toggle states)
└── Overlay Buttons (icons/labels)
```

---

## 6. Information Hierarchy

### 6.1 Primary Metrics (Must see at a glance)

| Metric | Why Important | Current Display |
|--------|---------------|-----------------|
| **Total Slots** | Fleet capacity utilization | KPI Card (top-left) |
| **Avg Battery** | Overall test progress | KPI Card (top-center-left) |
| **Avg BDR** | Test quality indicator | KPI Card (top-center-right) |
| **Failed Slots** | Immediate attention needed | Heatmap (red cells) |
| **Critical Anomalies** | Urgent issues | Spotlight section |

### 6.2 Secondary Metrics (Need to look for)

| Metric | Why Important | Current Display |
|--------|---------------|-----------------|
| **Phase Distribution** | Test stage breakdown | Bar chart |
| **Battery Distribution** | Charge level spread | Histogram |
| **Workout Counts** | Test completion rate | Workout table |
| **Firmware Versions** | Software consistency | Filter buttons |
| **Duplicate Serials** | Data integrity | KPI Card (serials) |

### 6.3 Tertiary Metrics (Deep dive)

| Metric | Why Important | Current Display |
|--------|---------------|-----------------|
| **Historical BDR** | Trend analysis | Line chart |
| **Cycle Analysis** | Throughput patterns | Overlay panel |
| **Machine Comparison** | Fleet benchmarking | Floorplan |
| **Repair History** | Maintenance tracking | Diagnostics view |

---

## 7. Interaction Flows

### 7.1 Slot Selection Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ USER ACTION: Click heatmap slot                                              │
│                                                                              │
│ SYSTEM RESPONSE:                                                             │
│ 1. Highlight selected slot (darker border)                                  │
│ 2. Open Detail Panel on right side                                          │
│ 3. Populate Detail Panel with:                                              │
│    - Machine name, slot ID, MAC, serial, firmware                          │
│    - Current phase and status badge                                        │
│    - Battery percentage and avg BDR                                        │
│    - Warning reason (if any)                                                │
│    - Workout table (current + historical)                                   │
│    - Battery/Current line chart                                             │
│ 4. Enable keyboard navigation (←/→ arrows)                                 │
│ 5. Enable graph freeze/unfreeze toggle                                     │
│                                                                              │
│ USER CAN:                                                                    │
│ - Click another slot to switch                                              │
│ - Click X to close panel                                                    │
│ - Use arrows to navigate slots                                              │
│ - Freeze graph to prevent auto-refresh                                     │
│ - Scroll workout table                                                      │
│ - Hover chart to highlight workout row                                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Filter Application Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ USER ACTION: Click health class filter button                               │
│                                                                              │
│ SYSTEM RESPONSE:                                                             │
│ 1. Toggle filter button state (active/inactive)                            │
│ 2. Add/remove class from active filter set                                 │
│ 3. For each heatmap cell:                                                   │
│    - Check if cell's health class matches any active filter                │
│    - If no filter active: show all cells                                   │
│    - If filters active: dim non-matching cells (slot-dimmed class)         │
│ 4. Also apply firmware filter (if active)                                  │
│ 5. Update bulk charger controls (if visible)                               │
│                                                                              │
│ MULTIPLE FILTERS:                                                            │
│ - Health class AND firmware filters are combined (AND logic)                │
│ - Multiple health classes use OR logic within category                     │
│                                                                              │
│ CLEAR FILTERS:                                                               │
│ - Click "Clear" button or press 'C' key                                    │
│ - Resets all filters to inactive                                           │
│ - All cells return to full opacity                                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 7.3 Machine Switch Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ USER ACTION: Click machine tab in header                                    │
│                                                                              │
│ SYSTEM RESPONSE:                                                             │
│ 1. Update CURRENT_MACHINE variable                                         │
│ 2. Highlight selected tab                                                   │
│ 3. Fetch new machine data from /api/bdr/{machine}                          │
│ 4. Update SESSION_DATA with new slot data                                   │
│ 5. Call init() to re-render entire dashboard                               │
│ 6. Close any open Detail Panel                                             │
│ 7. Reset scroll position to top                                            │
│                                                                              │
│ DATA FLOW:                                                                   │
│ Browser → API → PostgreSQL → Response → State Update → Re-render           │
│                                                                              │
│ KEYBOARD ALTERNATIVE:                                                        │
│ - Ctrl+←/→ to cycle machines                                               │
│ - 0-9 then Enter to jump to machine by number                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 7.4 Diagnostics Connection Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ USER ACTION: Click Connect in Diagnostics View                              │
│                                                                              │
│ SYSTEM RESPONSE:                                                             │
│ 1. POST /api/machine/{name}/diagnose/connect                               │
│ 2. Show "Connecting..." status                                              │
│ 3. Backend: SSH connect to machine IP (10s timeout)                        │
│ 4. On success:                                                              │
│    - Update status bar: "Connected"                                        │
│    - Enable Quick Scan button                                              │
│    - Enable Live Monitor button                                            │
│    - Enable LED controls                                                   │
│    - Enable extended diagnostics                                           │
│ 5. On failure:                                                              │
│    - Show error message                                                    │
│    - Keep buttons disabled                                                 │
│                                                                              │
│ SUBSEQUENT ACTIONS:                                                          │
│ - Quick Scan: Single button scan, update grid                              │
│ - Live Monitor: Start 1-second polling loop                                │
│ - LED Control: Send color commands to machine                              │
│ - Extended Diagnostics: Run hardware tests                                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 8. Navigation Map

### 8.1 Primary Navigation

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              HEADER BAR                                      │
│                                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │ Machine Tabs │  │ View Toggle  │  │ Overlay Btns │  │ Theme Toggle │   │
│  │ (aqc-34,     │  │ [BDR] [Rings]│  │ [Floorplan]  │  │ [T]          │   │
│  │  aqc-37,     │  │ [Viz] [Diag] │  │ [Serial]     │  │              │   │
│  │  aqc-48)     │  │ [Old Data]   │  │ [Cycles] [AI]│  │              │   │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘   │
│                                                                              │
│  MACHINE TABS: Switch between AQC machines                                 │
│  VIEW TOGGLE: Switch between 5 main views                                  │
│  OVERLAY BTNS: Toggle overlay panels                                       │
│  THEME TOGGLE: Dark/light mode                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 8.2 View Navigation

```
                        ┌─────────────────┐
                        │   BDR Dashboard │
                        │   (Primary)     │
                        └────────┬────────┘
                                 │
            ┌────────────────────┼────────────────────┐
            │                    │                    │
            ▼                    ▼                    ▼
    ┌───────────────┐   ┌───────────────┐   ┌───────────────┐
    │  Ring Slots   │   │  Data Viz     │   │  Diagnostics  │
    │  (Secondary)  │   │  (Secondary)  │   │  (Secondary)  │
    └───────────────┘   └───────────────┘   └───────────────┘
            │                    │                    │
            └────────────────────┼────────────────────┘
                                 │
                                 ▼
                        ┌───────────────┐
                        │   Old Data    │
                        │  (Tertiary)   │
                        └───────────────┘
```

### 8.3 Overlay Navigation

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ ANY VIEW                                                                     │
│                                                                              │
│  ┌───────────────────────┐                                                  │
│  │ Toggle Floorplan      │ ← Click Floorplan button                        │
│  └───────────┬───────────┘                                                  │
│              │                                                              │
│              ▼                                                              │
│  ┌───────────────────────┐                                                  │
│  │ Floorplan Overlay     │ ← Click machine → Navigate to BDR view         │
│  │ (covers main content) │ ← Right-click → Context menu                   │
│  └───────────┬───────────┘ ← Click X or press Escape → Close              │
│              │                                                              │
│              ▼                                                              │
│  ┌───────────────────────┐                                                  │
│  │ BDR Dashboard for     │                                                  │
│  │ selected machine      │                                                  │
│  └───────────────────────┘                                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 8.4 Drill-Down Navigation

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ DRILL-DOWN PATHS                                                             │
│                                                                              │
│ Heatmap Slot → Detail Panel (right side)                                   │
│     │                                                                       │
│     ├── Workout Table Row → Highlight corresponding chart point            │
│     │                                                                       │
│     └── Machine Name → Switch to that machine                              │
│                                                                              │
│ Anomaly Table Row → Detail Panel for that slot                              │
│                                                                              │
│ Spotlight Card → Detail Panel for that slot                                 │
│                                                                              │
│ Floorplan Machine → BDR Dashboard for that machine                         │
│                                                                              │
│ Serial Browser Result → Rings View with that ring selected                 │
│                                                                              │
│ Data Viz Serial → Old Data search for that serial                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 9. Widget Dependencies

### 9.1 Data Dependencies

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          DATA FLOW DIAGRAM                                   │
│                                                                              │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────┐                │
│  │ /api/bdr    │─────▶│ SESSION_DATA│─────▶│ init()      │                │
│  │ (5s cache)  │      │ (global)    │      │ (renderer)  │                │
│  └─────────────┘      └─────────────┘      └──────┬──────┘                │
│                                                    │                        │
│                          ┌─────────────────────────┼───────────────────┐   │
│                          │                         │                   │   │
│                          ▼                         ▼                   ▼   │
│                   ┌─────────────┐          ┌─────────────┐    ┌─────────┐│
│                   │ Heatmap     │          │ KPI Cards   │    │ Charts  ││
│                   │ Grid        │          │ (4)         │    │ (3)     ││
│                   └──────┬──────┘          └─────────────┘    └─────────┘│
│                          │                                                │
│                          ▼                                                │
│                   ┌─────────────┐                                         │
│                   │ Detail Panel│ ← Click slot                            │
│                   └──────┬──────┘                                         │
│                          │                                                │
│           ┌──────────────┼──────────────┐                                │
│           ▼              ▼              ▼                                │
│    ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                     │
│    │ Workout     │ │ Battery     │ │ Status      │                     │
│    │ Table       │ │ Chart       │ │ Info        │                     │
│    └─────────────┘ └─────────────┘ └─────────────┘                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 9.2 Filter Dependencies

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ FILTER IMPACT MAP                                                            │
│                                                                              │
│  Health Class Filter ──────────────────────────────────────────────────┐   │
│       │                                                                │   │
│       ├──▶ Heatmap Grid (dims non-matching slots)                     │   │
│       │                                                                │   │
│       └──▶ Bulk Charger Controls (updates available slots)            │   │
│                                                                              │
│  Firmware Filter ──────────────────────────────────────────────────────┐   │
│       │                                                                │   │
│       ├──▶ Heatmap Grid (dims non-matching slots)                     │   │
│       │                                                                │   │
│       └──▶ Bulk Charger Controls (updates available slots)            │   │
│                                                                              │
│  COMBINED FILTER (Health AND Firmware)                                     │
│       │                                                                    │
│       └──▶ Heatmap Grid (dims cells not matching BOTH filters)           │
│                                                                              │
│  Machine Tabs ─────────────────────────────────────────────────────────┐   │
│       │                                                                │   │
│       ├──▶ SESSION_DATA (new machine data)                            │   │
│       │                                                                │   │
│       ├──▶ Heatmap Grid (re-render with new data)                     │   │
│       │                                                                │   │
│       ├──▶ KPI Cards (recalculate for new machine)                    │   │
│       │                                                                │   │
│       ├──▶ Charts (re-render with new data)                           │   │
│       │                                                                │   │
│       └──▶ Detail Panel (close if open)                               │   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 9.3 View Dependencies

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ VIEW STATE DEPENDENCIES                                                      │
│                                                                              │
│  currentView: 'bdr' | 'rings' | 'data-viz' | 'diagnostics' | 'old-data'  │
│       │                                                                    │
│       ├──▶ 'bdr'                                                          │
│       │       ├──▶ Heatmap Grid visible                                   │
│       │       ├──▶ KPI Cards (4) visible                                  │
│       │       ├──▶ Charts visible                                         │
│       │       ├──▶ Anomaly Table visible                                  │
│       │       └──▶ Detail Panel available (on slot click)                 │
│       │                                                                    │
│       ├──▶ 'rings'                                                        │
│       │       ├──▶ Ring Grid visible                                      │
│       │       ├──▶ KPI Cards (5) visible                                  │
│       │       ├──▶ Status Filters visible                                 │
│       │       └──▶ Detail Panel available (on ring click)                 │
│       │                                                                    │
│       ├──▶ 'data-viz'                                                     │
│       │       ├──▶ Category Tabs visible                                  │
│       │       ├──▶ SKU Chart visible                                      │
│       │       └──▶ Serial Table visible                                   │
│       │                                                                    │
│       ├──▶ 'diagnostics'                                                  │
│       │       ├──▶ Machine Selector visible                               │
│       │       ├──▶ Button Grid visible                                    │
│       │       ├──▶ LED Controls visible                                   │
│       │       └──▶ Live Log Monitor visible                               │
│       │                                                                    │
│       └──▶ 'old-data'                                                     │
│               ├──▶ Search Input visible                                   │
│               ├──▶ Results Table visible                                  │
│               └──▶ Export Buttons visible                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 10. Filters and Affected Widgets

### 10.1 Filter Inventory

| Filter | Location | Type | Options | Affected Widgets |
|--------|----------|------|---------|------------------|
| **Health Class** | BDR Dashboard | Multi-select toggle | Pass, OK, Low BDR, High BDR, Sensor Issue, Warn, Danger, Dead, Empty, NA | Heatmap Grid, Bulk Charger Controls |
| **Firmware** | BDR Dashboard | Multi-select toggle | Dynamic (from data) | Heatmap Grid, Bulk Charger Controls |
| **Ring Status** | Ring Slots | Single-select radio | All, Running, Passed, Failed, Assigned | Ring Grid |
| **Search** | Ring Slots | Text input | Serial/MAC substring | Ring Grid |
| **Category** | Data Viz | Single-select tabs | All, Production, RT Conversion, Wabi Sabi | SKU Chart, Serial Table |
| **Search Mode** | Old Data | Toggle | Single, Bulk | Search Input behavior |
| **Serial Search** | Old Data | Text input | Serial number(s) | Results Table |
| **Machine** | Diagnostics | Dropdown | Machine list | Button Grid, Diagnostics |
| **Date Range** | Archive (implicit) | Date picker | Historical dates | Archive data |

### 10.2 Filter Interaction Rules

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ FILTER COMBINATION RULES                                                     │
│                                                                              │
│ HEALTH CLASS FILTERS:                                                        │
│ - Multiple selections use OR logic (show slots matching ANY selected class) │
│ - No selection = show all slots                                            │
│ - Active filter dims non-matching slots (opacity reduction)                │
│                                                                              │
│ FIRMWARE FILTERS:                                                            │
│ - Multiple selections use OR logic (show slots with ANY selected firmware) │
│ - No selection = show all slots                                            │
│ - Combined with Health Class using AND logic                               │
│                                                                              │
│ COMBINED FILTER EFFECT:                                                      │
│ - Slot shown ONLY if matches:                                              │
│   (Health Class matches ANY selected) AND (Firmware matches ANY selected)  │
│ - If no Health filters active: Firmware filter alone applies               │
│ - If no Firmware filters active: Health filter alone applies               │
│ - If no filters active: All slots shown                                    │
│                                                                              │
│ CLEAR FILTERS:                                                               │
│ - Press 'C' key or click "Clear" button                                    │
│ - Resets ALL filters (Health + Firmware)                                   │
│ - All slots return to full opacity                                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 10.3 Filter State Persistence

| Filter | Persisted? | Storage Location | Duration |
|--------|------------|------------------|----------|
| Health Class | No | In-memory (window.heatmapFilterActive) | Session only |
| Firmware | No | In-memory (window.firmwareFilterActive) | Session only |
| Ring Status | No | In-memory | Session only |
| Theme | Yes | localStorage | Permanent |
| Floorplan Names | Yes | localStorage | Permanent |
| Heatmap Colors | Yes | localStorage | Permanent |
| Selected Machine | No | In-memory (CURRENT_MACHINE) | Session only |
| Current View | No | In-memory (currentView) | Session only |

---

## 11. Drill-Down Interactions

### 11.1 Heatmap → Detail Panel

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ TRIGGER: Click heatmap slot                                                  │
│                                                                              │
│ RESULT: Detail Panel opens on right side (40% width)                        │
│                                                                              │
│ CONTENTS:                                                                    │
│ ┌─────────────────────────────────────────────────────────────────────────┐│
│ │ HEADER                                                                 ││
│ │ Machine: aqc-34 | Slot: 12 | MAC: AA:BB:CC:DD:EE:FF                   ││
│ │ Serial: WB-24-001-WB | Firmware: v1.3                                  ││
│ │ Phase: DISCHARGING | Status: ✅ Pass                                   ││
│ │ Battery: 87.3% | Avg BDR: 8.2 | Avg Current: 1.97 mA                 ││
│ │ ⚠️ Warning: Slanting leak detected                                     ││
│ ├─────────────────────────────────────────────────────────────────────────┤│
│ │ WORKOUT TABLE                                                           ││
│ │ ┌────┬───────┬──────┬──────────┬──────┬──────────┬───────┐            ││
│ │ │ #  │ Start │ End  │ Duration │ BDR  │ Readings │ Died? │            ││
│ │ ├────┼───────┼──────┼──────────┼──────┼──────────┼───────┤            ││
│ │ │ *  │ 100%  │ 87%  │ 1.2 hr   │ 10.8 │ 144      │ No    │ ← Current││
│ │ │ 1  │ 100%  │ 92%  │ 0.8 hr   │ 10.0 │ 96       │ No    │            ││
│ │ │ 2  │ 100%  │ 88%  │ 1.1 hr   │ 10.9 │ 132      │ No    │            ││
│ │ └────┴───────┴──────┴──────────┴──────┴──────────┴───────┘            ││
│ ├─────────────────────────────────────────────────────────────────────────┤│
│ │ BATTERY/CURRENT CHART                                                   ││
│ │ ┌─────────────────────────────────────────────────────────────────────┐││
│ │ │  📈 Battery % (green area)                                          │││
│ │ │  📈 Current mA (blue dashed line)                                   │││
│ │ │  [Zoom] [Pan] [Freeze]                                             │││
│ │ └─────────────────────────────────────────────────────────────────────┘││
│ └─────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
│ INTERACTIONS:                                                                │
│ - Hover chart → Highlight matching workout row                             │
│ - Click "Freeze" → Prevent auto-refresh overwriting panel                 │
│ - Arrow keys ←/→ → Navigate to previous/next slot                         │
│ - Click X → Close panel                                                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 11.2 Anomaly Table → Detail Panel

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ TRIGGER: Click anomaly table row                                            │
│                                                                              │
│ RESULT:                                                                      │
│ 1. If on different machine: Switch to that machine's tab                   │
│ 2. Open Detail Panel for that slot                                          │
│ 3. Scroll heatmap to show that slot (if needed)                            │
│                                                                              │
│ ANOMALY TABLE ROWS:                                                          │
│ ┌──────┬──────────┬────────────┬──────────┬──────┬──────────────────────┐  │
│ │ Slot │ MAC      │ Serial     │ Severity │ BDR  │ Description          │  │
│ ├──────┼──────────┼────────────┼──────────┼──────┼──────────────────────┤  │
│ │ 12   │ AA:BB:CC │ WB-24-001  │ 🔴 HIGH  │ 8.2  │ Slanting leak        │  │
│ │ 45   │ DD:EE:FF │ WB-32-002  │ 🟡 MED   │ 14.5 │ High BDR            │  │
│ └──────┴──────────┴────────────┴──────────┴──────┴──────────────────────┘  │
│                                                                              │
│ SEVERITY BADGES:                                                             │
│ 🔴 HIGH: >10 failures, CRITICAL issues, dead slots                         │
│ 🟡 MED: 3-10 failures, warnings, out-of-range metrics                     │
│ 🟢 LOW: Minor issues, informational                                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 11.3 Floorplan → Machine Navigation

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ TRIGGER: Click machine box in Floorplan                                     │
│                                                                              │
│ RESULT:                                                                      │
│ 1. Close Floorplan overlay                                                  │
│ 2. Switch to clicked machine's tab                                          │
│ 3. Load that machine's BDR data                                            │
│ 4. Re-render dashboard with new machine                                     │
│                                                                              │
│ MACHINE BOX DISPLAY:                                                         │
│ ┌─────────────────┐                                                         │
│ │ aqc-34          │  ← Machine name                                        │
│ │ 48 slots        │  ← Slot count (color-coded: red→green)                │
│ │ Zone A          │  ← Zone label                                          │
│ └─────────────────┘                                                         │
│                                                                              │
│ COLOR CODING:                                                                │
│ 🔴 0 slots (red)                                                           │
│ 🟨 32 slots (yellow-green)                                                 │
│ 🟩 64 slots (green)                                                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 11.4 Serial Browser → Ring Detail

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ TRIGGER: Click serial in Serial Browser                                     │
│                                                                              │
│ RESULT:                                                                      │
│ 1. Close Serial Browser overlay                                             │
│ 2. Switch to Ring Slots view                                                │
│ 3. Select the machine containing that serial                                │
│ 4. Open Detail Panel for that ring                                          │
│                                                                              │
│ SERIAL BROWSER RESULTS:                                                      │
│ ┌─────────────────────────────────────────────────────────────────────────┐│
│ │ Serial      │ Machine │ Slot │ Status │ MAC        │ Firmware          ││
│ │ WB-24-001-WB│ aqc-34  │ 12   │ ✅ Pass│ AA:BB:CC   │ v1.3             ││
│ └─────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
│ DUPLICATE DETECTION:                                                         │
│ If serial found in multiple locations:                                      │
│ ⚠️ Duplicate: aqc-34:12, aqc-45:8                                         │
│ [Go to aqc-34:12] [Go to aqc-45:8]                                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 12. Modal and Overlay Behavior

### 12.1 Overlay Types

| Overlay | Trigger | Content | Close Method | Z-Index |
|---------|---------|---------|--------------|---------|
| Floorplan | Header button | SVG floorplan | X button, Escape, click outside | 1000 |
| Serial Browser | Q key or button | Serial search | X button, Escape, click outside | 1000 |
| Cycle Analysis | Header button | Workout histogram | X button, Escape, click outside | 1000 |
| AI Report | Header button | Fleet analysis | X button, Escape, click outside | 1000 |
| Detail Panel | Heatmap/ring click | Slot details | X button, click another slot | 900 |
| Duplicates Modal | Duplicate detected | Duplicate locations | X button, Escape | 1100 |

### 12.2 Overlay Behavior Rules

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ OVERLAY MANAGEMENT RULES                                                     │
│                                                                              │
│ 1. SINGLE OVERLAY RULE:                                                     │
│    - Only ONE overlay can be open at a time                                │
│    - Opening new overlay closes existing one                               │
│    - Exception: Detail Panel can coexist with overlays                     │
│                                                                              │
│ 2. CLICK-OUTSIDE BEHAVIOR:                                                  │
│    - Clicking outside overlay (on backdrop) closes it                      │
│    - Backdrop has semi-transparent black overlay                           │
│    - Click propagates to backdrop, not underlying content                  │
│                                                                              │
│ 3. KEYBOARD CLOSE:                                                           │
│    - Escape key closes any open overlay                                    │
│    - Escape priority: Modal > Overlay > Detail Panel                       │
│                                                                              │
│ 4. DETAIL PANEL SPECIAL CASE:                                               │
│    - Detail Panel is NOT an overlay (it's a side panel)                    │
│    - It pushes main content to the left (60% → 60% layout)                │
│    - It can exist while overlays are open                                  │
│    - Closing overlay doesn't close Detail Panel                            │
│                                                                              │
│ 5. SCROLL LOCK:                                                              │
│    - When overlay is open, background content is NOT scrollable            │
│    - Overlay content IS scrollable if it overflows                         │
│                                                                              │
│ 6. FOCUS MANAGEMENT:                                                         │
│    - Focus moves to overlay when opened                                    │
│    - Focus returns to trigger element when closed                          │
│    - Tab key cycles through interactive elements in overlay                │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 12.3 Overlay Content Hierarchy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Z-INDEX LAYERS                                                               │
│                                                                              │
│ 1100: Duplicates Modal (highest - error states)                            │
│                                                                              │
│ 1000: Major Overlays                                                        │
│    ├── Floorplan                                                            │
│    ├── Serial Browser                                                       │
│    ├── Cycle Analysis                                                       │
│    └── AI Report                                                            │
│                                                                              │
│ 900: Side Panels                                                            │
│    └── Detail Panel                                                         │
│                                                                              │
│ 800: Tooltips                                                               │
│    └── Heatmap cell hover tooltips                                          │
│                                                                              │
│ 100: Sticky Header                                                          │
│    └── Machine tabs, view toggle, buttons                                   │
│                                                                              │
│ 1: Main Content                                                             │
│    └── Dashboard content                                                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 13. Keyboard Shortcuts

### 13.1 Global Shortcuts

| Key | Action | Context | Description |
|-----|--------|---------|-------------|
| `T` | Toggle Theme | Global | Switch between dark/light mode |
| `F` | Open Floorplan | Global | Toggle floorplan overlay |
| `C` | Clear Filters | BDR Dashboard | Reset all health/firmware filters |
| `Q` | Serial Browser | Global | Toggle serial browser overlay |
| `S` | Switch View | Global | Toggle between BDR and Rings view |
| `Escape` | Close Overlay | Global | Close any open overlay/modal |

### 13.2 Navigation Shortcuts

| Key | Action | Context | Description |
|-----|--------|---------|-------------|
| `Ctrl+←` | Previous Machine | Global | Switch to previous machine tab |
| `Ctrl+→` | Next Machine | Global | Switch to next machine tab |
| `←` | Previous Slot | Detail Panel | Navigate to previous slot |
| `→` | Next Slot | Detail Panel | Navigate to next slot |
| `0-9` then `Enter` | Jump to Machine | Global | Type machine number, press Enter |

### 13.3 Detail Panel Shortcuts

| Key | Action | Context | Description |
|-----|--------|---------|-------------|
| `←` | Previous Slot | Detail Panel | Navigate to previous slot in heatmap |
| `→` | Next Slot | Detail Panel | Navigate to next slot in heatmap |
| `Space` | Freeze Graph | Detail Panel | Toggle graph freeze/unfreeze |
| `Escape` | Close Panel | Detail Panel | Close detail panel |

### 13.4 Machine Number Input

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ MACHINE NUMBER INPUT SYSTEM                                                  │
│                                                                              │
│ User types digits (0-9):                                                    │
│   - Digits are buffered in window._machineDigitBuffer                      │
│   - Buffer is displayed in a small indicator (optional)                    │
│   - Buffer clears after 2 seconds of inactivity                           │
│                                                                              │
│ User presses Enter:                                                          │
│   - Parse buffer as integer                                                 │
│   - Find machine at that index in ALL_MACHINE_NAMES                        │
│   - If found: switch to that machine                                       │
│   - If not found: ignore                                                   │
│   - Clear buffer                                                           │
│                                                                              │
│ Example:                                                                      │
│   - User types "3" then "4" then "Enter"                                  │
│   - Buffer = "34"                                                          │
│   - Switch to ALL_MACHINE_NAMES[34] (e.g., "aqc-48")                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 14. Live Update Behavior

### 14.1 Polling Intervals

| Data Type | Interval | Source | Affected Widgets |
|-----------|----------|--------|------------------|
| BDR Data | 5 seconds | /api/bdr | Heatmap, KPI Cards, Charts, Anomalies |
| Rings Data | 5 seconds | /api/rings | Ring Grid, Ring KPI Cards |
| Button Grid (Diagnostics) | 1 second | /api/diagnostics/scan | Button Grid cells |
| Live Logs (Diagnostics) | 2 seconds | /api/diagnostics/logs | Log Monitor |
| Floorplan | 5 seconds | /api/bdr (all machines) | Floorplan machine boxes |
| Charger Status | 10 seconds | /api/machine/{name}/charger-status | Charger controls |

### 14.2 Update Mechanism

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ POLLING FLOW (BDR Data)                                                      │
│                                                                              │
│ startApiPolling()                                                            │
│     │                                                                       │
│     └──▶ setInterval(5000)                                                 │
│              │                                                              │
│              ▼                                                              │
│         fetchBdrData()                                                      │
│              │                                                              │
│              ▼                                                              │
│         GET /api/bdr                                                        │
│              │                                                              │
│              ▼                                                              │
│         Response (JSON)                                                     │
│              │                                                              │
│              ▼                                                              │
│         Fingerprint Check (JSON.stringify of sorted slots)                 │
│              │                                                              │
│         ┌────┴────┐                                                        │
│         │         │                                                        │
│     Same?      Different?                                                  │
│         │         │                                                        │
│         ▼         ▼                                                        │
│     Skip      Update ALL_MACHINE_DATA                                     │
│                  │                                                         │
│                  ▼                                                         │
│              init()                                                        │
│                  │                                                         │
│                  ▼                                                         │
│              Full Re-render                                                │
│                                                                              │
│ OPTIMIZATION:                                                                │
│ - Fingerprint check prevents unnecessary re-renders                        │
│ - JSON.stringify comparison is cheap for small payloads                    │
│ - Full re-render is acceptable for 64-slot grid                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 14.3 Real-Time Indicators

| Indicator | Location | Behavior |
|-----------|----------|----------|
| Data Freshness | KPI Cards | Animates number change with easing |
| Connection Status | Diagnostics | Green/Red dot |
| Live Monitor | Diagnostics | Pulsing indicator when active |
| Graph Freeze | Detail Panel | Toggle button state |
| Filter Active | Filter Buttons | Highlighted when active |

### 14.4 Update Batching

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ UPDATE BATCHING STRATEGY                                                     │
│                                                                              │
│ PROBLEM:                                                                      │
│ - 5-second polling could cause UI jank if updates are large                │
│ - Multiple widgets updating simultaneously                                 │
│                                                                              │
│ SOLUTION:                                                                     │
│ - All widgets update in single init() call                                 │
│ - DOM updates batched by browser's requestAnimationFrame                  │
│ - No explicit batching needed - browser handles it                         │
│                                                                              │
│ EDGE CASE:                                                                    │
│ - Detail Panel: Only updates if slot data changed                          │
│ - Graph: Only re-renders if not frozen (window.__isGraphLocked)            │
│ - Workaround: "Freeze" button to prevent auto-refresh                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 15. Business-Critical UI Elements

### 15.1 Critical Elements (Must Not Break)

| Element | Why Critical | Failure Impact |
|---------|--------------|----------------|
| **Heatmap Grid** | Primary monitoring tool | Operators can't see slot status |
| **KPI Cards** | Fleet overview | Can't assess overall health |
| **Detail Panel** | Slot investigation | Can't diagnose issues |
| **Machine Tabs** | Machine switching | Can't navigate fleet |
| **Health Class Filters** | Issue identification | Can't filter by problem type |
| **Anomaly Table** | Issue prioritization | Can't see all problems |
| **Status Badges** | Quick status识别 | Can't tell pass/fail/warn |
| **Connection Status (Diagnostics)** | Hardware repair | Can't fix machines |

### 15.2 Critical Data Flows

| Flow | Components | Failure Impact |
|------|------------|----------------|
| BDR API → Heatmap | /api/bdr → init() → Grid | Real-time monitoring broken |
| Rings API → Ring Grid | /api/rings → init() → Grid | Ring status unknown |
| Diagnostics API → Button Grid | /api/diagnostics → Grid | Hardware repair impossible |
| Machine Tabs → State | Tab click → CURRENT_MACHINE → init() | Can't switch machines |

### 15.3 Critical User Actions

| Action | Shortcut | Failure Impact |
|--------|----------|----------------|
| Switch Machine | Click tab or Ctrl+←/→ | Can't navigate fleet |
| Select Slot | Click heatmap cell | Can't investigate issues |
| Apply Filter | Click filter button | Can't identify problem types |
| Connect to Machine | Click Connect (Diagnostics) | Can't repair hardware |
| Close Overlay | Escape or X button | Can't return to main view |

---

## 16. Redesignable UI Elements

### 16.1 Freely Redesignable (No Business Impact)

| Element | Current Implementation | Redesign Freedom |
|---------|------------------------|------------------|
| **Color Scheme** | Dark/Light themes | Full redesign (except semantic colors) |
| **Typography** | System fonts | Full redesign |
| **Spacing/Layout** | Fixed widths/heights | Full redesign |
| **Icons** | Inline SVG | Full redesign |
| **Border Radius** | Mixed | Full redesign |
| **Shadows** | Minimal | Full redesign |
| **Animations** | Basic transitions | Full redesign |
| **Background** | Solid colors | Full redesign |

### 16.2 Partially Redesignable (With Constraints)

| Element | Current Implementation | Constraints |
|---------|------------------------|-------------|
| **Heatmap Layout** | 16×4 grid | Must show 64 slots, preserve slot numbering |
| **KPI Cards** | 4 across | Must show same 4 metrics |
| **Charts** | ApexCharts | Must preserve data visualization purpose |
| **Detail Panel** | Right side panel | Must show same information fields |
| **Floorplan** | SVG with 42 positions | Must preserve zone structure |
| **Filter Buttons** | Toggle buttons | Must preserve filter logic |

### 16.3 Not Redesignable (Business Logic)

| Element | Current Implementation | Why Not Redesignable |
|---------|------------------------|----------------------|
| **Health Class Colors** | Semantic color coding | Operators rely on color recognition |
| **Status Badges** | Pass/Fail/Warn/Danger | Universal status language |
| **Slot Numbering** | 01-64 standard | Physical slot mapping |
| **Severity Levels** | HIGH/MED/LOW | Issue prioritization system |
| **Keyboard Shortcuts** | T/F/C/Q/S/Escape | Operator muscle memory |

---

## 17. Semantic Colors

### 17.1 Health Class Colors (Heatmap)

| Color | Hex | Health Class | Meaning |
|-------|-----|--------------|---------|
| 🟢 Green | `#12f202` | `slot-pass` | ≥6 workouts, BDR 5-12, passing |
| 🟢 Teal | `#02f2ba` | `slot-ok` | Has data, no issues |
| 🔵 Blue | `#0EA5E9` | `slot-low-bdr` | Avg BDR >0 but <5 |
| 🩷 Pink | `#EC4899` | `slot-high-bdr` | Avg BDR >12 |
| 🩵 Cyan | `#14B8A6` | `slot-sensor-issue` | Flat battery graph |
| 🟡 Amber | `#F59E0B` | `slot-warn` | 3-10 failures, warnings |
| 🔴 Red | `#DC2626` | `slot-danger` | >10 failures, critical |
| 🟣 Purple | `#4F46E5` | `slot-dead` | Battery <3%, flat >3hr |
| ⚪ Gray | `#9CA3AF` | `slot-empty` | No serial number |
| 🟤 Brown | `#A0765F` | `slot-na` | No graph data |

### 17.2 Status Badge Colors

| Color | Status | Meaning |
|-------|--------|---------|
| 🟢 Green | `pass` | Test passed |
| 🔴 Red | `fail` | Test failed |
| 🔵 Blue | `bdr` | Test running |
| 🟠 Orange | `assigned` | Slot assigned, not started |

### 17.3 Severity Badge Colors

| Color | Severity | Meaning |
|-------|----------|---------|
| 🔴 Red | `HIGH` | >10 failures, CRITICAL issues |
| 🟡 Yellow | `MED` | 3-10 failures, warnings |
| 🟢 Green | `LOW` | Minor issues |

### 17.4 Floorplan Zone Colors

| Color | Zone | Meaning |
|-------|------|---------|
| 🔵 Blue | Zone A | Physical zone identifier |
| 🟢 Green | Zone B | Physical zone identifier |
| 🟠 Orange | Zone C | Physical zone identifier |
| 🟣 Purple | Zone D | Physical zone identifier |

### 17.5 BDR Value Colors

| Color | Range | Meaning |
|-------|-------|---------|
| 🟢 Green | 5-12 | Optimal BDR range |
| 🔴 Red | >12 | High BDR (warning) |
| 🔵 Blue | <5 | Low BDR (informational) |

### 17.6 Current Value Colors

| Color | Range | Meaning |
|-------|-------|---------|
| 🟢 Green | 1-3 mA | Optimal current range |
| 🔴 Red | <1 or >3 mA | Out of range |

---

## 18. Priority Metrics

### 18.1 Tier 1: Must-See Metrics

| Metric | Why Priority | Display Location | Update Frequency |
|--------|--------------|------------------|------------------|
| **Failed Slots** | Immediate attention needed | Heatmap (red cells), KPI Card | 5 seconds |
| **Critical Anomalies** | Urgent issues requiring action | Spotlight section, Anomaly Table | 5 seconds |
| **Avg BDR** | Test quality indicator | KPI Card | 5 seconds |
| **Avg Battery** | Test progress indicator | KPI Card | 5 seconds |

### 18.2 Tier 2: Important Metrics

| Metric | Why Important | Display Location | Update Frequency |
|--------|---------------|------------------|------------------|
| **Total Slots** | Fleet capacity utilization | KPI Card | 5 seconds |
| **Phase Distribution** | Test stage breakdown | Bar Chart | 5 seconds |
| **Battery Distribution** | Charge level spread | Histogram | 5 seconds |
| **Workout Count** | Test completion rate | Workout Table | 5 seconds |

### 18.3 Tier 3: Contextual Metrics

| Metric | Why Useful | Display Location | Update Frequency |
|--------|------------|------------------|------------------|
| **Firmware Versions** | Software consistency | Filter Buttons | On load |
| **Duplicate Serials** | Data integrity | KPI Card | On load |
| **Historical BDR** | Trend analysis | Line Chart | 5 seconds |
| **Machine Comparison** | Fleet benchmarking | Floorplan | 5 seconds |

### 18.4 Metric Relationships

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ METRIC DEPENDENCY GRAPH                                                      │
│                                                                              │
│ Failed Slots (Tier 1)                                                       │
│     │                                                                       │
│     ├──▶ Anomaly Count (derived)                                           │
│     │                                                                       │
│     └──▶ Machine Health Score (derived)                                    │
│                                                                              │
│ Avg BDR (Tier 1)                                                            │
│     │                                                                       │
│     ├──▶ BDR Range Distribution (derived)                                  │
│     │                                                                       │
│     └──▶ Test Quality Score (derived)                                      │
│                                                                              │
│ Avg Battery (Tier 1)                                                        │
│     │                                                                       │
│     ├──▶ Battery Distribution (derived)                                    │
│     │                                                                       │
│     └──▶ Test Progress Score (derived)                                     │
│                                                                              │
│ Workout Count (Tier 2)                                                      │
│     │                                                                       │
│     ├──▶ Throughput Rate (derived)                                          │
│     │                                                                       │
│     └──▶ Completion Rate (derived)                                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 19. Current UX Pain Points

### 19.1 Identified Issues

| Issue | Location | Impact | Severity |
|-------|----------|--------|----------|
| **No Dark Mode Persistence** | Theme toggle | User must toggle every session | Low |
| **Filter State Lost on Machine Switch** | Health/Firmware filters | Operators re-apply filters | Medium |
| **Detail Panel Blocks Content** | Right side panel | Main content compressed | Medium |
| **No Loading Indicators** | API calls | Users see stale data during fetch | Low |
| **No Error Messages** | API failures | Silent failures | High |
| **Complex Filter Logic** | Health + Firmware AND | Confusing filter behavior | Medium |
| **No Responsive Design** | Mobile/tablet | Unusable on small screens | High |
| **No Batch Operations** | Charger controls | One-at-a-time slot control | Low |
| **No Undo for Actions** | All interactions | Accidental clicks permanent | Medium |
| **No Keyboard Focus Indicators** | All interactive elements | Accessibility issue | High |
| **No Tooltips** | Heatmap cells | Hover required for details | Low |
| **No Print/Export** | Dashboard view | Can't save snapshots | Medium |
| **No Multi-Machine Comparison** | Single machine view | Can't compare side-by-side | High |
| **No Historical Trend View** | Current snapshot only | Can't see patterns over time | High |
| **No Alert System** | Passive monitoring | Must actively watch dashboard | High |

### 19.2 Accessibility Issues

| Issue | Location | WCAG | Impact |
|-------|----------|------|--------|
| **No ARIA Labels** | All interactive elements | 1.1.1 | Screen readers can't interpret |
| **No Keyboard Navigation** | Heatmap grid | 2.1.1 | Can't navigate without mouse |
| **No Focus Indicators** | All buttons/links | 2.4.7 | Can't see where focus is |
| **Low Contrast Ratios** | Some text on dark theme | 1.4.3 | Hard to read |
| **No Color-Blind Support** | Health class colors | 1.4.1 | Relies solely on color |
| **No Reduced Motion** | Animations | 2.3.3 | No preference respect |

### 19.3 Performance Issues

| Issue | Location | Impact | Severity |
|-------|----------|--------|----------|
| **Full Re-render on Update** | init() | Unnecessary DOM manipulation | Medium |
| **No Virtual Scrolling** | Anomaly Table | Slow with many anomalies | Low |
| **No Image Lazy Loading** | Floorplan SVG | Initial load delay | Low |
| **Large Bundle Size** | app.js (6800 LOC) | Slow initial load | High |
| **No Code Splitting** | Single file | Loads everything upfront | Medium |

---

## 20. Designer's Mental Model

### 20.1 How Operators Actually Use the Dashboard

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         OPERATOR'S MENTAL MODEL                              │
│                                                                              │
│ "I'm responsible for 40 machines with 64 slots each. That's 2,560 slots.  │
│  I can't watch them all. I need to know:                                    │
│                                                                              │
│  1. WHAT'S BROKEN RIGHT NOW?                                                │
│     → Look for RED cells in heatmap                                        │
│     → Check Spotlight anomalies                                            │
│                                                                              │
│  2. WHAT'S ABOUT TO BREAK?                                                  │
│     → Look for ORANGE/YELLOW cells (warnings)                              │
│     → Check BDR trend in line chart                                        │
│                                                                              │
│  3. WHAT'S WORKING WELL?                                                    │
│     → Look for GREEN cells (passing)                                       │
│     → KPI cards show overall health                                        │
│                                                                              │
│  4. HOW DO I FIX IT?                                                        │
│     → Click failing slot to see details                                    │
│     → If hardware: Go to Diagnostics, connect, scan, repair               │
│     → If software: Note it, report to engineering                          │
│                                                                              │
│  5. HOW DO I PROVE IT'S FIXED?                                              │
│     → Watch slot turn from red → orange → green                            │
│     → Check BDR history chart for improvement                              │
│                                                                              │
│  TIME PRESSURE:                                                              │
│     → Shift is 8 hours                                                     │
│     → Must process X batteries per shift                                   │
│     → Every minute a slot is down = lost productivity                      │
│     → Need to triage: fix the easy stuff first, escalate the hard stuff   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 20.2 Operator's Information Needs by Time

| Time of Day | Primary Need | Dashboard Focus |
|-------------|--------------|-----------------|
| **Shift Start (08:00)** | Fleet status overview | KPI Cards, Heatmap scan |
| **First Hour (08:00-09:00)** | Identify overnight failures | Anomaly Table, Spotlight |
| **Mid-Morning (09:00-11:00)** | Monitor progress, handle issues | Detail Panel, Diagnostics |
| **Lunch (11:00-12:00)** | Quick status check | KPI Cards only |
| **Afternoon (12:00-15:00)** | Deep investigation, repairs | Full Diagnostics workflow |
| **End of Shift (15:00-16:00)** | Prepare handoff, document | AI Report, Export data |

### 20.3 Operator's Decision Tree

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ OPERATOR'S DECISION TREE                                                    │
│                                                                              │
│ START: Open Dashboard                                                       │
│     │                                                                       │
│     ▼                                                                       │
│ Check KPI Cards                                                              │
│     │                                                                       │
│     ├──▶ High failure count? → Scan heatmap for red cells                  │
│     │                                                                       │
│     ├──▶ Low battery avg? → Check battery distribution chart               │
│     │                                                                       │
│     └──▶ High BDR avg? → Check BDR history chart                          │
│                                                                              │
│ Found Issue?                                                                 │
│     │                                                                       │
│     ├──▶ YES → Click failing slot                                           │
│     │           │                                                           │
│     │           ├──▶ Hardware issue? → Diagnostics View                    │
│     │           │                                                           │
│     │           ├──▶ Software issue? → Document, escalate                 │
│     │           │                                                           │
│     │           └──▶ Unknown? → Deep investigation workflow               │
│     │                                                                       │
│     └──▶ NO → Monitor progress                                              │
│                 │                                                           │
│                 ├──▶ Check Floorplan for machine status                     │
│                 │                                                           │
│                 ├──▶ Review Cycle Analysis for throughput                  │
│                 │                                                           │
│                 └──▶ Wait for next alert                                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 20.4 Operator's Mental Shortcuts

| Shortcut | Meaning | Dashboard Equivalent |
|----------|---------|----------------------|
| "Red = Bad" | Failing slot | `slot-danger` class |
| "Green = Good" | Passing slot | `slot-pass` class |
| "Yellow = Watch" | Warning slot | `slot-warn` class |
| "Purple = Dead" | Non-functional | `slot-dead` class |
| "Empty = Available" | No battery | `slot-empty` class |
| "Big number = Good" | High throughput | KPI Card: Total Slots |
| "Small number = Bad" | Low progress | KPI Card: Avg Battery |
| "Flat line = Broken" | Sensor issue | `slot-sensor-issue` class |
| "Slanted = Leaking" | Battery leak | Slanting leak badge |

### 20.5 Operator's Workflow Patterns

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ COMMON WORKFLOW PATTERNS                                                     │
│                                                                              │
│ PATTERN 1: "Quick Scan" (30 seconds)                                        │
│   - Open dashboard                                                         │
│   - Glance at KPI cards                                                   │
│   - Scan heatmap for red cells                                             │
│   - If red: click to investigate                                           │
│   - If green: move on                                                     │
│                                                                              │
│ PATTERN 2: "Deep Dive" (5-10 minutes)                                      │
│   - Identify problem slot                                                  │
│   - Open detail panel                                                      │
│   - Review workout table                                                   │
│   - Check battery chart                                                    │
│   - Check historical data                                                  │
│   - Decide: fix now or escalate?                                           │
│                                                                              │
│ PATTERN 3: "Hardware Repair" (15-30 minutes)                               │
│   - Switch to Diagnostics View                                            │
│   - Connect to machine                                                    │
│   - Run Quick Scan                                                         │
│   - Identify faulty component                                             │
│   - Run repair tool                                                        │
│   - Verify fix worked                                                      │
│   - Return to BDR Dashboard                                               │
│                                                                              │
│ PATTERN 4: "Shift Handoff" (10 minutes)                                    │
│   - Generate AI Report                                                     │
│   - Export anomalies                                                       │
│   - Note ongoing issues                                                    │
│   - Brief incoming operator                                                │
│                                                                              │
│ PATTERN 5: "Fleet Monitoring" (continuous)                                 │
│   - Dashboard open on second monitor                                       │
│   - Periodic glance every 5-10 minutes                                    │
│   - React to alerts (sound/notification)                                   │
│   - Address issues as they arise                                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 20.6 Operator's Pain Points

| Pain Point | Current Workaround | Desired Solution |
|------------|-------------------|------------------|
| "I can't see all machines at once" | Switch tabs manually | Multi-machine comparison view |
| "I don't know when something fails" | Watch dashboard constantly | Push notifications/alerts |
| "Filters reset when I switch machines" | Re-apply filters each time | Persistent filter state |
| "I can't compare historical data" | Take screenshots | Historical trend view |
| "I can't export my findings" | Manual copy-paste | One-click export with formatting |
| "I can't see patterns across shifts" | Paper notes | Shift comparison view |
| "I can't prioritize which machine to fix first" | Guesswork | Priority ranking system |
| "I can't see if my fix worked" | Wait and watch | Before/after comparison |

---

## Appendix A: Widget Specifications

### A.1 Heatmap Cell Specification

| Property | Value | Notes |
|----------|-------|-------|
| Size | ~40×40px | Responsive to container |
| Border radius | 6px | Rounded corners |
| Border | 2px solid | Color based on health class |
| Background | Based on health class | Semantic colors |
| Text | Slot number (01-64) | White, centered |
| Hover | Slight scale increase | 1.05× transform |
| Click | Opens Detail Panel | Adds selection border |
| Dimmed | 30% opacity | When filtered out |
| Duplicate | Pulsing border animation | `slot-dup` class |

### A.2 KPI Card Specification

| Property | Value | Notes |
|----------|-------|-------|
| Size | ~150×80px | Fixed width, flexible height |
| Background | White/Dark (theme) | Subtle shadow |
| Border | None | Rounded corners: 8px |
| Label | Small text, gray | Top of card |
| Value | Large text, bold | Animated counter |
| Animation | 820ms ease-out | `requestAnimationFrame` |

### A.3 Detail Panel Specification

| Property | Value | Notes |
|----------|-------|-------|
| Width | 40% of viewport | Pushes main content left |
| Position | Right side | Fixed when scrolling |
| Header | Machine, slot, serial info | Sticky |
| Workout Table | Scrollable | Max height: 200px |
| Chart | Full width, 400px height | Zoom/pan enabled |
| Close Button | Top-right corner | X icon |

### A.4 Floorplan Box Specification

| Property | Value | Notes |
|----------|-------|-------|
| Size | ~80×60px | Fixed per zone |
| Border radius | 8px | Rounded corners |
| Background | Color based on slot count | Red→Yellow→Green gradient |
| Border | 2px solid | Thicker if active machine |
| Text | Machine name + slot count | White, centered |
| Badge | Slot count pill | Top-right corner |

---

## Appendix B: Data Field Reference

### B.1 Slot Data Fields

| Field | Type | Description | Used In |
|-------|------|-------------|---------|
| `serial_number` | string | Unique identifier | All views |
| `machine` | string | Machine name | All views |
| `slot` | integer | Slot number (1-64) | All views |
| `mac` | string | MAC address | Detail Panel |
| `firmware_version` | string | Firmware version | Filters, Detail |
| `battery_percent` | float | Current battery % | KPI, Charts |
| `bdr` | float | Current BDR value | KPI, Charts |
| `avg_bdr` | float | Average BDR | KPI, Anomalies |
| `battery_current` | float | Current draw (mA) | Charts |
| `phase` | string | Test phase | Charts, Filters |
| `status` | string | Pass/Fail/Warn | Status Badges |
| `workouts` | integer | Completed workouts | KPI, Charts |
| `last_update` | timestamp | Last data update | Freshness |
| `health_class` | string | Health classification | Heatmap colors |
| `anomalies` | array | List of issues | Anomaly Table |
| `bdr_data` | object | BDR test data | Detail Panel |
| `bdr_state` | object | BDR state info | Detail Panel |

### B.2 Machine Data Fields

| Field | Type | Description | Used In |
|-------|------|-------------|---------|
| `name` | string | Machine identifier | Tabs, Floorplan |
| `ip` | string | IP address | Diagnostics |
| `user` | string | SSH username | Diagnostics |
| `removed_slots` | array | Unavailable slots | Filtering |
| `slot_count` | integer | Available slots | Floorplan color |
| `firmware_versions` | array | Unique firmware | Filters |

---

## Appendix C: API Endpoint Reference

### C.1 Data Endpoints

| Endpoint | Method | Purpose | Response |
|----------|--------|---------|----------|
| `/api/bdr` | GET | All machines BDR data | JSON object |
| `/api/bdr/{machine}` | GET | Single machine BDR | JSON object |
| `/api/rings` | GET | All machines rings | JSON object |
| `/api/rings/{machine}` | GET | Single machine rings | JSON object |
| `/api/machines` | GET | Machine list | JSON array |
| `/api/health` | GET | Health check | JSON status |

### C.2 Search Endpoints

| Endpoint | Method | Purpose | Response |
|----------|--------|---------|----------|
| `/api/old-data/search/{serial}` | GET | Single serial search | JSON array |
| `/api/old-data/search` | POST | Batch serial search | JSON array |
| `/api/search` | GET | Search serials | JSON array |
| `/api/search/{serial}` | GET | Search specific serial | JSON array |

### C.3 Diagnostics Endpoints

| Endpoint | Method | Purpose | Response |
|----------|--------|---------|----------|
| `.../diagnose/connect` | POST | Connect to machine | Status |
| `.../diagnose/scan` | POST | Quick scan | Button states |
| `.../diagnose/led/{action}` | POST | LED control | Status |
| `.../diagnose/mcp/scan` | POST | MCP register scan | Register states |
| `.../diagnose/mcp/repair` | POST | MCP repair | Status |
| `.../diagnose/full` | POST | Full diagnostics | Report |
| `.../diagnose/bt/status` | GET | Bluetooth status | Status |
| `.../diagnose/logs` | GET | Fetch logs | Log entries |

---

## Appendix D: Error States

### D.1 API Error States

| Error | Display | Recovery |
|-------|---------|----------|
| API unreachable | "API Offline" banner | Retry in 5s |
| Data stale | "Data outdated" warning | Auto-refresh |
| Machine offline | Red indicator on tab | Manual reconnect |
| SSH connection failed | Error message in Diagnostics | Retry connection |
| No data available | Empty state message | Wait for data |

### D.2 UI Error States

| Error | Display | Recovery |
|-------|---------|----------|
| No slots selected | Empty heatmap | Data loads automatically |
| No search results | "No results found" | Clear search |
| Filter mismatch | All cells dimmed | Adjust filters |
| Detail panel error | Error message in panel | Click another slot |
| Overlay error | Error toast | Close and reopen |

---

**End of Document**

*This document should enable a product designer to understand the complete UX of the BDR Dashboard without reading any code.*
