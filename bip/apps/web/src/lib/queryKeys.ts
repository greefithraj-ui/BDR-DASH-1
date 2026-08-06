export const queryKeys = {
  machines: {
    all: ["machines"] as const,
    detail: (id: string) => ["machines", "detail", id] as const
  },
  rings: {
    all: ["rings"] as const,
    detail: (id: string) => ["rings", "detail", id] as const
  },
  timeline: {
    list: ["timeline", "list"] as const
  },
  reports: {
    list: ["reports", "list"] as const
  },
  metrics: {
    all: ["metrics"] as const
  },
  analyticsSummary: {
    all: ["analytics-summary"] as const
  },
  qualitySummary: {
    all: ["quality-summary"] as const
  },
  performanceSummary: {
    all: ["performance-summary"] as const
  },
  health: {
    all: ["health"] as const
  }
};
