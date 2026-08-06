import type {
  AiCitation,
  AiContextOption,
  AiConversation,
  AiMessage,
  AiScope,
  AiToolActivity,
  AiToolStatus
} from "./ai.types";

const TOOL_STATUS_TONES: Record<AiToolStatus, "success" | "danger" | "info"> = {
  Success: "success",
  Failed: "danger",
  Running: "info"
};

function cite(id: string, label: string, source: string, detail: string): AiCitation {
  return { id, label, source, detail };
}

function tool(
  id: string,
  toolName: string,
  description: string,
  status: AiToolStatus,
  startedAt: string,
  endedAt: string
): AiToolActivity {
  return { id, tool: toolName, description, status, startedAt, endedAt };
}

function message(id: string, role: "user" | "assistant", content: string, timestamp: string, extras?: Partial<AiMessage>): AiMessage {
  return { id, role, content, timestamp, ...extras };
}

function conversation(
  id: string,
  title: string,
  scope: AiScope,
  description: string,
  createdDate: string,
  updatedDate: string,
  suggestedPrompts: string[],
  messages: AiMessage[]
): AiConversation {
  return { id, title, scope, description, createdDate, updatedDate, suggestedPrompts, messages };
}

export function getContextOptions(): AiContextOption[] {
  return [
    { value: "All", label: "All contexts", description: "All conversations across the platform." },
    { value: "Fleet", label: "Fleet", description: "Fleet-wide health, KPIs, and risk summaries." },
    { value: "Battery", label: "Battery", description: "Battery-level health, aging, and lifecycle data." },
    { value: "Machine", label: "Machine", description: "Machine throughput, utilization, and status." },
    { value: "Quality", label: "Quality", description: "Pass rates, defects, and failure analysis." },
    { value: "Production", label: "Production", description: "Production output, yield, and shift performance." },
    { value: "Ring Lifecycle", label: "Ring Lifecycle", description: "Ring lifecycle stage distribution and transitions." }
  ];
}

function buildConversations(): AiConversation[] {
  return [
    conversation(
      "conv-executive-summary",
      "Executive Summary",
      "Fleet",
      "Fleet health and top risks summarized for leadership review.",
      "2026-07-15",
      "2026-08-02",
      [
        "What are the top 3 fleet risks this week?",
        "How did fleet health trend over the last 30 days?",
        "Which products need executive attention?"
      ],
      [
        message(
          "exec-msg-1",
          "user",
          "Summarize fleet health and the top risks for the leadership review.",
          "2026-08-02 07:40",
          {}
        ),
        message(
          "exec-msg-2",
          "assistant",
          "Fleet health is stable at 91/100, up 2 points month-over-month. 12,480 batteries are tracked across 8 machines and 5 products.\n\nTop risks this week:\n- Machine AQC-04 utilization dropped to 74.2% (fleet average 84.4%), driven by line-changeover delays.\n- Contact anomalies on AQC-02 rose 18% week-over-week and are under investigation.\n- Ring lifecycle 'Pending Removal' pool grew to 312 units (+9% MoM), increasing scrappage exposure.\n\nPass rate held at 95.4% and yield at 94.8%, so output quality remains the bright spot for the board pack.",
          "2026-08-02 07:41",
          {
            toolActivity: [
              tool("exec-tool-1", "Query fleet store", "Loaded 12,480 tracked batteries across 8 machines and 5 products", "Success", "2026-08-02 07:40:12", "2026-08-02 07:40:20"),
              tool("exec-tool-2", "Aggregate health", "Computed fleet health score, MoM delta, and risk ranking", "Success", "2026-08-02 07:40:21", "2026-08-02 07:40:33"),
              tool("exec-tool-3", "Verify citations", "Matched insights against Executive Dashboard and Reports sources", "Success", "2026-08-02 07:40:34", "2026-08-02 07:40:41")
            ],
            citations: [
              cite("exec-cite-1", "Fleet Health", "Executive Dashboard", "Fleet health 91/100, +2 pts MoM."),
              cite("exec-cite-2", "AQC-04 Utilization", "Machine Explorer", "AQC-04 at 74.2% utilization, below fleet 84.4%."),
              cite("exec-cite-3", "Contact Anomalies", "Quality Analytics", "AQC-02 contact anomalies +18% WoW.")
            ]
          }
        )
      ]
    ),
    conversation(
      "conv-battery-health",
      "Battery Health",
      "Battery",
      "Battery health score distribution across the tracked fleet.",
      "2026-07-18",
      "2026-08-02",
      [
        "How many batteries are in critical health?",
        "Show the health distribution by product.",
        "Which batteries need reconditioning next?"
      ],
      [
        message("batt-msg-1", "user", "Show me the overall battery health score distribution.", "2026-08-02 09:12", {}),
        message(
          "batt-msg-2",
          "assistant",
          "Across 12,480 tracked batteries, the health score distribution is:\n\n- Excellent (90+): 7,116 batteries (57%)\n- Good (80-89): 3,744 batteries (30%)\n- Fair (70-79): 1,123 batteries (9%)\n- Critical (<70): 497 batteries (4%)\n\nLFP-280 holds the strongest profile (63% Excellent). The 497 critical units are concentrated in LTO-45 (210 units) and NMC-121 (163 units), and should be prioritized for reconditioning.",
          "2026-08-02 09:13",
          {
            toolActivity: [
              tool("batt-tool-1", "Query battery store", "Loaded health scores for 12,480 batteries grouped by product", "Success", "2026-08-02 09:12:03", "2026-08-02 09:12:11"),
              tool("batt-tool-2", "Bucket health", "Binned scores into Excellent/Good/Fair/Critical buckets", "Success", "2026-08-02 09:12:12", "2026-08-02 09:12:19"),
              tool("batt-tool-3", "Rank critical units", "Ranked critical fleet by product for reconditioning priority", "Success", "2026-08-02 09:12:20", "2026-08-02 09:12:27")
            ],
            citations: [
              cite("batt-cite-1", "Battery Explorer", "Battery Explorer", "Health score distribution across 12,480 tracked batteries."),
              cite("batt-cite-2", "LTO-45 Health", "Battery Explorer", "LTO-45 holds 210 critical-health units."),
              cite("batt-cite-3", "NMC-121 Health", "Battery Explorer", "NMC-121 holds 163 critical-health units.")
            ]
          }
        )
      ]
    ),
    conversation(
      "conv-machine-status",
      "Machine Status",
      "Machine",
      "Machine utilization and throughput compared against the fleet.",
      "2026-07-20",
      "2026-08-02",
      [
        "Which machines are underperforming vs fleet average?",
        "What is AQC-06 utilization today?",
        "Show maintenance backlog by machine."
      ],
      [
        message("mach-msg-1", "user", "Which machines are underperforming versus the fleet average?", "2026-08-02 10:05", {}),
        message(
          "mach-msg-2",
          "assistant",
          "Compared against fleet averages (utilization 84.4%, efficiency 92%), two machines stand out:\n\n- AQC-04: utilization 74.2%, throughput 137.6/hr (-6.0% vs fleet). Line changeover and conveyor delays are the primary driver.\n- AQC-07: efficiency 88%, throughput 141.2/hr. Calibration drift contributed to 3% more rejected cells this week.\n\nAll other machines are within 2% of the fleet average. AQC-04 is the priority for the maintenance team's next shift.",
          "2026-08-02 10:06",
          {
            toolActivity: [
              tool("mach-tool-1", "Query machine store", "Loaded utilization and throughput for 8 machines over 14 days", "Success", "2026-08-02 10:05:08", "2026-08-02 10:05:17"),
              tool("mach-tool-2", "Compare vs fleet", "Computed per-machine delta against fleet averages", "Success", "2026-08-02 10:05:18", "2026-08-02 10:05:26"),
              tool("mach-tool-3", "Rank outliers", "Flagged AQC-04 and AQC-07 as outside tolerance", "Success", "2026-08-02 10:05:27", "2026-08-02 10:05:33")
            ],
            citations: [
              cite("mach-cite-1", "AQC-04 Throughput", "Machine Explorer", "AQC-04 at 137.6/hr vs fleet 146.3/hr."),
              cite("mach-cite-2", "AQC-07 Efficiency", "Machine Explorer", "AQC-07 efficiency 88%, below fleet 92%."),
              cite("mach-cite-3", "Utilization Distribution", "Performance Analytics", "Machine utilization distribution across the fleet.")
            ]
          }
        )
      ]
    ),
    conversation(
      "conv-quality-summary",
      "Quality Summary",
      "Quality",
      "Pass rates, yield, and defect trends for the current month.",
      "2026-07-22",
      "2026-08-01",
      [
        "What is the current pass rate?",
        "Show defect share by failure cause.",
        "Are retest rates improving?"
      ],
      [
        message("qual-msg-1", "user", "Summarize pass rates and defect trends this month.", "2026-08-01 08:20", {}),
        message(
          "qual-msg-2",
          "assistant",
          "Month-to-date quality summary:\n\n- Pass rate: 95.4% (+0.6 pts vs prior month)\n- Yield: 94.8% (+0.4 pts)\n- Retest rate: 2.1% (-0.2 pts)\n\nTop defect causes: calibration drift (31% share), contact anomaly (22%), cell imbalance (18%). Contact anomalies increased 18% week-over-week on AQC-02, while thermal excursions remain flat. The improvement in retest rate aligns with the recalibration push in week 3.",
          "2026-08-01 08:21",
          {
            toolActivity: [
              tool("qual-tool-1", "Query quality store", "Loaded pass/fail and defect records for July 2026", "Success", "2026-08-01 08:20:04", "2026-08-01 08:20:12"),
              tool("qual-tool-2", "Aggregate defects", "Computed defect share by cause and WoW deltas", "Success", "2026-08-01 08:20:13", "2026-08-01 08:20:24"),
              tool("qual-tool-3", "Verify citations", "Cross-checked figures against Quality Analytics panels", "Success", "2026-08-01 08:20:25", "2026-08-01 08:20:31")
            ],
            citations: [
              cite("qual-cite-1", "Pass Rate", "Quality Analytics", "Pass rate 95.4%, +0.6 pts MoM."),
              cite("qual-cite-2", "Failure Causes", "Quality Analytics", "Calibration drift 31%, contact anomaly 22%, cell imbalance 18%."),
              cite("qual-cite-3", "Retest Rate", "Quality Analytics", "Retest rate 2.1%, -0.2 pts MoM.")
            ]
          }
        )
      ]
    ),
    conversation(
      "conv-performance-review",
      "Performance Review",
      "Production",
      "Throughput, utilization, and cycle time performance review.",
      "2026-07-24",
      "2026-08-02",
      [
        "What was fleet throughput this week?",
        "Compare cycle time across machines.",
        "Is utilization improving or declining?"
      ],
      [
        message("perf-msg-1", "user", "Review throughput, utilization, and cycle time performance.", "2026-08-02 11:30", {}),
        message(
          "perf-msg-2",
          "assistant",
          "Performance review for the last 14 days:\n\n- Throughput: 146.3/hr fleet average (+6/hr vs prior period)\n- Machine utilization: 84.4% (+1.2 pts)\n- Cycle time: 13.6s (-0.3s)\n- Processing rate: 2.4 batteries/min\n- Efficiency: 92% (+0.8 pts)\n- Performance score: 90/100 (+3 pts)\n\nCycle distribution clusters in the 12-14s band (331 of 560 records), and utilization gains are driven by AQC-01, AQC-03, and AQC-05. AQC-04 remains the laggard as noted in the machine review.",
          "2026-08-02 11:31",
          {
            toolActivity: [
              tool("perf-tool-1", "Query performance store", "Loaded 560 performance records across 8 machines and 5 products", "Success", "2026-08-02 11:30:05", "2026-08-02 11:30:16"),
              tool("perf-tool-2", "Aggregate KPIs", "Computed throughput, cycle time, utilization, efficiency, and score", "Success", "2026-08-02 11:30:17", "2026-08-02 11:30:28"),
              tool("perf-tool-3", "Verify citations", "Cross-checked figures against Performance Analytics", "Success", "2026-08-02 11:30:29", "2026-08-02 11:30:35")
            ],
            citations: [
              cite("perf-cite-1", "Throughput", "Performance Analytics", "Fleet throughput 146.3/hr, +6/hr."),
              cite("perf-cite-2", "Cycle Time", "Performance Analytics", "Cycle time 13.6s, -0.3s."),
              cite("perf-cite-3", "Utilization", "Performance Analytics", "Machine utilization 84.4%, +1.2 pts.")
            ]
          }
        )
      ]
    ),
    conversation(
      "conv-failure-investigation",
      "Failure Investigation",
      "Quality",
      "Root-cause investigation of the AQC-02 contact anomaly spike.",
      "2026-07-26",
      "2026-08-02",
      [
        "What caused the contact anomaly spike on AQC-02?",
        "Show failure trend for the last 14 days.",
        "Which batches are most affected?"
      ],
      [
        message("fail-msg-1", "user", "Investigate the recent spike in contact anomalies on AQC-02.", "2026-08-02 14:15", {}),
        message(
          "fail-msg-2",
          "assistant",
          "Investigation summary for the AQC-02 contact anomaly spike:\n\n- Contact anomalies rose 18% week-over-week (31 to 43 recorded failures).\n- Breakdown by cause: contact anomaly 22%, cell imbalance 18%, thermal excursion 12%.\n- Most affected ring batch: B-2209 (14 anomalies), concentrated on the evening shift.\n\nPattern analysis suggests the anomaly correlates with the batch changeover on 2026-07-28, consistent with a seating/fixture adjustment. The ring batch B-2210 referenced in the work order was not found in the fleet store, so the analysis fell back to B-2209.",
          "2026-08-02 14:16",
          {
            toolActivity: [
              tool("fail-tool-1", "Query failure store", "Loaded failure records for AQC-02 over 14 days", "Success", "2026-08-02 14:15:06", "2026-08-02 14:15:18"),
              tool("fail-tool-2", "Correlate with shifts", "Matched anomaly timestamps to shifts and batch changeovers", "Success", "2026-08-02 14:15:19", "2026-08-02 14:15:31"),
              tool("fail-tool-3", "Resolve ring batch", "Ring batch B-2210 not found in fleet store; fell back to B-2209", "Failed", "2026-08-02 14:15:32", "2026-08-02 14:15:36")
            ],
            citations: [
              cite("fail-cite-1", "Failure Trend", "Quality Analytics", "Contact anomalies +18% WoW on AQC-02."),
              cite("fail-cite-2", "Ring Batch B-2209", "Battery Explorer", "Ring batch B-2209: 14 anomalies, evening shift."),
              cite("fail-cite-3", "Failure Causes", "Quality Analytics", "Contact anomaly 22%, cell imbalance 18%, thermal excursion 12%.")
            ]
          }
        )
      ]
    ),
    conversation(
      "conv-ring-lifecycle",
      "Ring Lifecycle",
      "Ring Lifecycle",
      "Ring lifecycle stage distribution and transition overview.",
      "2026-07-28",
      "2026-08-01",
      [
        "How many rings are in each lifecycle stage?",
        "What is the Pending Removal trend?",
        "Which stage has the highest transition rate?"
      ],
      [
        message("ring-msg-1", "user", "Explain the ring lifecycle stage distribution.", "2026-08-01 16:45", {}),
        message(
          "ring-msg-2",
          "assistant",
          "The ring lifecycle currently distributes 12,480 rings across five stages:\n\n- Registered: 6,237 (50%)\n- Tracking: 4,244 (34%)\n- Review: 1,012 (8%)\n- Pending Removal: 312 (3%)\n- Finalized: 675 (5%)\n\nThe Pending Removal pool grew 9% month-over-month, driven by NMC-280 rings flagged for end-of-life review. Tracking-to-Review is the highest transition rate (87% of review-stage rings originated from Tracking last month). Finalized volume is up 12% MoM, reflecting faster dispositioning.",
          "2026-08-01 16:46",
          {
            toolActivity: [
              tool("ring-tool-1", "Query lifecycle store", "Loaded ring lifecycle stages for 12,480 rings", "Success", "2026-08-01 16:45:07", "2026-08-01 16:45:15"),
              tool("ring-tool-2", "Compute transitions", "Computed stage-to-stage transition rates for the last 30 days", "Success", "2026-08-01 16:45:16", "2026-08-01 16:45:27"),
              tool("ring-tool-3", "Flag growth", "Flagged Pending Removal +9% MoM for review", "Success", "2026-08-01 16:45:28", "2026-08-01 16:45:34")
            ],
            citations: [
              cite("ring-cite-1", "Stage Distribution", "Battery Explorer", "Ring stage distribution across 12,480 rings."),
              cite("ring-cite-2", "Pending Removal", "Battery Explorer", "Pending Removal pool 312 rings, +9% MoM."),
              cite("ring-cite-3", "Transition Rate", "Timeline", "Tracking→Review transition rate 87%.")
            ]
          }
        )
      ]
    ),
    conversation(
      "conv-trend-analysis",
      "Trend Analysis",
      "Fleet",
      "30-day trends for tracked batteries, open alerts, and fleet health.",
      "2026-07-29",
      "2026-08-02",
      [
        "Show the 30-day alert trend.",
        "How has fleet health changed over 30 days?",
        "Which KPI is declining fastest?"
      ],
      [
        message("trend-msg-1", "user", "Analyze 30-day trends for tracked batteries and open alerts.", "2026-08-02 13:05", {}),
        message(
          "trend-msg-2",
          "assistant",
          "30-day trend summary:\n\n- Tracked batteries: 12,268 → 12,480 (+1.7%)\n- Open alerts: 186 → 214 (+15%), concentrated in the last 7 days\n- Fleet health: 89 → 91/100 (+2 pts)\n- Pass rate: 94.7% → 95.4% (+0.7 pts)\n\nThe alert uptick is driven by AQC-02 contact anomalies and calibration-drift flags on AQC-07. Despite more alerts, fleet health improved, indicating alerts are being triaged faster. Open alerts remain the fastest-moving metric and are flagged for the daily operations review.",
          "2026-08-02 13:06",
          {
            toolActivity: [
              tool("trend-tool-1", "Query fleet store", "Loaded 30 days of tracking, alert, and health snapshots", "Success", "2026-08-02 13:05:04", "2026-08-02 13:05:13"),
              tool("trend-tool-2", "Compute deltas", "Computed 30-day deltas for track, alerts, health, and pass rate", "Success", "2026-08-02 13:05:14", "2026-08-02 13:05:25"),
              tool("trend-tool-3", "Verify citations", "Cross-checked trends against Timeline and dashboards", "Success", "2026-08-02 13:05:26", "2026-08-02 13:05:32")
            ],
            citations: [
              cite("trend-cite-1", "Tracked Fleet", "Battery Explorer", "Tracked batteries 12,268 → 12,480 over 30 days."),
              cite("trend-cite-2", "Open Alerts", "Battery Intelligence Dashboard", "Open alerts 186 → 214 over 30 days."),
              cite("trend-cite-3", "Fleet Health", "Executive Dashboard", "Fleet health 89 → 91/100 over 30 days.")
            ]
          }
        ),
        message("trend-msg-3", "user", "Which KPI is declining fastest?", "2026-08-02 13:07", {}),
        message(
          "trend-msg-4",
          "assistant",
          "Open alerts is the fastest-declining metric: 186 → 214 (+15%) over 30 days, with the steepest rise in the last 7 days. Utilization on AQC-04 is the next most concerning trend, down 3.4 pts across the window. No other tracked KPI declined by more than 1 point.",
          "2026-08-02 13:08",
          {
            toolActivity: [
              tool("trend-tool-4", "Rank KPIs", "Ranked all tracked KPIs by 30-day delta", "Success", "2026-08-02 13:07:02", "2026-08-02 13:07:09")
            ],
            citations: [
              cite("trend-cite-4", "Open Alerts", "Battery Intelligence Dashboard", "Open alerts +15% over 30 days, steepest in last 7 days."),
              cite("trend-cite-5", "AQC-04 Utilization", "Machine Explorer", "AQC-04 utilization -3.4 pts over 30 days.")
            ]
          }
        )
      ]
    ),
    conversation(
      "conv-production-summary",
      "Production Summary",
      "Production",
      "Today's production output across all lines and shifts.",
      "2026-07-30",
      "2026-08-02",
      [
        "Give me today's production summary.",
        "Which line produced the most today?",
        "Show today's output by shift."
      ],
      [
        message("prod-msg-1", "user", "Give me today's production summary across all lines.", "2026-08-02 06:50", {}),
        message(
          "prod-msg-2",
          "assistant",
          "Today's production summary (through 06:50):\n\n- Total produced: 1,284 batteries (running at 98% of plan)\n- Passed: 1,225 · Failed: 59 (pass rate 95.4%)\n- Yield: 94.8% · Throughput: 146.3/hr fleet average\n\nBy shift: Shift A produced 512 units, Shift B 449, Shift C 323 (partial). AQC-03 leads output at 178 units; AQC-04 trails at 132 units, consistent with its utilization lag. Shift C is expected to catch up by end of day.",
          "2026-08-02 06:51",
          {
            toolActivity: [
              tool("prod-tool-1", "Query production store", "Loaded today's output by line and shift", "Success", "2026-08-02 06:50:09", "2026-08-02 06:50:17"),
              tool("prod-tool-2", "Compute summary", "Computed totals, pass rate, yield, and plan attainment", "Success", "2026-08-02 06:50:18", "2026-08-02 06:50:28"),
              tool("prod-tool-3", "Rank lines", "Ranked production lines by output", "Success", "2026-08-02 06:50:29", "2026-08-02 06:50:34")
            ],
            citations: [
              cite("prod-cite-1", "Daily Production Report", "Reports", "Today's production totals and pass rate."),
              cite("prod-cite-2", "Shift Output", "Reports", "Shift A 512, Shift B 449, Shift C 323."),
              cite("prod-cite-3", "Line Ranking", "Production", "AQC-03 leads at 178 units today.")
            ]
          }
        )
      ]
    ),
    conversation(
      "conv-general-questions",
      "General Questions",
      "Fleet",
      "Onboarding and capability questions about the AI Intelligence Center.",
      "2026-08-01",
      "2026-08-02",
      [
        "What can this assistant do?",
        "How do I cite a report in my question?",
        "What data sources are available?"
      ],
      [
        message("gen-msg-1", "user", "How do I use the AI Intelligence Center?", "2026-08-02 12:00", {}),
        message(
          "gen-msg-2",
          "assistant",
          "The AI Intelligence Center answers questions over the platform's mock data using structured conversations.\n\n- Pick a conversation from the sidebar or use the context selector to scope answers to Fleet, Battery, Machine, Quality, Production, or Ring Lifecycle.\n- Each assistant answer shows the mock tool activity it ran and the citation cards it used.\n- Ask follow-ups in the same conversation, or click a suggested prompt to get started.\n\nStart with the Executive Summary conversation for a fleet-wide overview, or ask a specific question such as \"Which machines are underperforming?\".",
          "2026-08-02 12:01",
          {
            toolActivity: [
              tool("gen-tool-1", "Load capabilities", "Loaded available conversation scopes and prompt templates", "Success", "2026-08-02 12:00:05", "2026-08-02 12:00:10")
            ],
            citations: [
              cite("gen-cite-1", "AI Intelligence Center", "Platform Help", "Guide to conversations, context scopes, and citations."),
              cite("gen-cite-2", "Mock Data", "Platform", "All assistant answers are generated from deterministic mock data.")
            ]
          }
        )
      ]
    )
  ];
}

function buildReply(scope: AiScope): AiMessage {
  const replies: Record<AiScope, string> = {
    Fleet:
      "Here is the fleet-level view (mock): fleet health holds at 91/100 with 12,480 tracked batteries. Open alerts ticked up 15% over 30 days, concentrated on AQC-02 contact anomalies and AQC-07 calibration drift. No urgent action is required, but AQC-04 utilization remains the main watch item.",
    Battery:
      "Here is the battery-level view (mock): 57% of the fleet is in Excellent health, 30% Good, 9% Fair, and 4% Critical. The 497 critical units are concentrated in LTO-45 (210) and NMC-121 (163) and are candidates for reconditioning.",
    Machine:
      "Here is the machine-level view (mock): fleet utilization is 84.4%. AQC-04 is underperforming at 74.2% utilization (137.6/hr), and AQC-07 shows efficiency at 88% due to calibration drift. The rest of the fleet is within 2% of average.",
    Quality:
      "Here is the quality view (mock): pass rate is 95.4% (+0.6 pts MoM), yield 94.8%, retest rate 2.1%. Calibration drift (31%) and contact anomaly (22%) lead the defect causes; contact anomalies rose 18% WoW on AQC-02.",
    Production:
      "Here is the production view (mock): today totals 1,284 batteries at 98% of plan with a 95.4% pass rate. Shift A leads at 512 units; AQC-03 tops the lines at 178 units.",
    "Ring Lifecycle":
      "Here is the ring lifecycle view (mock): 12,480 rings split into Registered 50%, Tracking 34%, Review 8%, Pending Removal 3%, and Finalized 5%. The Pending Removal pool grew 9% MoM and Tracking-to-Review is the highest transition rate at 87%."
  };

  return {
    id: `live-assistant-${Date.now()}`,
    role: "assistant",
    content: replies[scope],
    timestamp: formatNow(),
    toolActivity: [
      tool(`live-tool-1-${Date.now()}`, "Query context store", `Scoped retrieval for "${scope}" context`, "Success", formatNow(), formatNow()),
      tool(`live-tool-2-${Date.now()}`, "Synthesize answer", "Generated a deterministic mock response from scope templates", "Success", formatNow(), formatNow())
    ],
    citations: [
      cite(`live-cite-1-${Date.now()}`, scope, "AI Intelligence Center", "Mock citation for the selected scope.")
    ]
  };
}

export function formatNow(): string {
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, "0");
  const d = String(now.getDate()).padStart(2, "0");
  const hh = String(now.getHours()).padStart(2, "0");
  const mm = String(now.getMinutes()).padStart(2, "0");
  return `${y}-${m}-${d} ${hh}:${mm}`;
}

const mockConversations = buildConversations();

export function getMockConversations(): AiConversation[] {
  return mockConversations;
}

export function createMockReply(scope: AiScope, _prompt: string): AiMessage {
  void _prompt;
  return buildReply(scope);
}

export { TOOL_STATUS_TONES };
