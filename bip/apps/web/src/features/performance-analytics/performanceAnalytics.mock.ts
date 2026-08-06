import type {
  PerformanceChartPlaceholder,
  PerformanceComparisonItem,
  PerformanceDistributionItem,
  PerformanceKpi,
  PerformanceMetric,
  PerformanceRecord,
  PerformanceTone,
  PerformanceTrendPoint
} from "./performanceAnalytics.types";

type ProductSeed = {
  product: string;
  category: string;
};

const PRODUCT_SEEDS: ProductSeed[] = [
  { product: "LFP-280", category: "LFP" },
  { product: "LFP-135", category: "LFP" },
  { product: "NMC-121", category: "NMC" },
  { product: "NMC-280", category: "NMC" },
  { product: "LTO-45", category: "LTO" }
];

const MACHINES = ["AQC-01", "AQC-02", "AQC-03", "AQC-04", "AQC-05", "AQC-06", "AQC-07", "AQC-08"];
const FIRMWARES = ["v3.0.2", "v2.4.1", "v2.3.8", "v1.9.0"];
const TARGET_THROUGHPUT = 150;

const DATES = buildDates(14);

const CYCLE_BUCKETS = ["<10s", "10-12s", "12-14s", "14-16s", ">16s"];
const UTILIZATION_BUCKETS = ["<70%", "70-80%", "80-90%", ">=90%"];

function buildDates(count: number): string[] {
  const dates: string[] = [];
  const start = new Date(2026, 6, 1);
  for (let n = 0; n < count; n += 1) {
    const date = new Date(start.getTime() + n * 86_400_000);
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    dates.push(`2026-${month}-${day}`);
  }
  return dates;
}

function round1(value: number): number {
  return Math.round(value * 10) / 10;
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

function buildRecord(machine: string, machineIndex: number, product: string, category: string, productIndex: number, date: string, dateIndex: number): PerformanceRecord {
  const baseUtilization = 81 + (machineIndex % 3) * 4;
  const utilization = round1(clamp(baseUtilization + ((machineIndex * 5 + dateIndex) % 9) - 4, 75, 98));
  const baseThroughput = 130 + (machineIndex % 3) * 10;
  const throughput = baseThroughput + ((machineIndex * 11 + productIndex * 7 + dateIndex * 5) % 40) - 12;
  const cycleTime = round1(Math.max(10, 15 - machineIndex * 0.35 - ((productIndex + dateIndex) % 4) * 0.25 + ((machineIndex * 3) % 5) * 0.1));
  const processingRate = round1(throughput / 60);
  const efficiency = 86 + ((machineIndex * 3 + productIndex * 2 + dateIndex) % 13);
  const throughputRatio = clamp((throughput / TARGET_THROUGHPUT) * 100, 0, 100);
  const performanceScore = Math.round(clamp(utilization * 0.35 + efficiency * 0.35 + throughputRatio * 0.3, 0, 100));
  const status = performanceScore >= 85 ? "On Target" : performanceScore >= 70 ? "Watch" : "Off Target";
  const statusTone: PerformanceTone = performanceScore >= 85 ? "success" : performanceScore >= 70 ? "warning" : "danger";
  const produced = 55 + ((machineIndex * 9 + productIndex * 13 + dateIndex * 5) % 50);

  return {
    id: `performance-${date}-${machine}-${product}`,
    machine,
    product,
    category,
    firmware: FIRMWARES[(machineIndex + productIndex + dateIndex) % FIRMWARES.length],
    date,
    produced,
    throughput,
    cycleTime,
    utilization,
    processingRate,
    efficiency,
    performanceScore,
    targetThroughput: TARGET_THROUGHPUT,
    status,
    statusTone
  };
}

function buildRecords(): PerformanceRecord[] {
  const records: PerformanceRecord[] = [];
  let seedIndex = 0;

  DATES.forEach((date, dateIndex) => {
    MACHINES.forEach((machine, machineIndex) => {
      PRODUCT_SEEDS.forEach((product, productIndex) => {
        const record = buildRecord(machine, machineIndex, product.product, product.category, productIndex, date, dateIndex);
        record.id = `performance-${seedIndex}`;
        seedIndex += 1;
        records.push(record);
      });
    });
  });

  return records;
}

function average(values: number[]): number {
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function buildKpis(records: PerformanceRecord[]): PerformanceKpi[] {
  const avgThroughput = average(records.map((record) => record.throughput));
  const avgCycleTime = average(records.map((record) => record.cycleTime));
  const avgUtilization = average(records.map((record) => record.utilization));
  const avgProcessingRate = average(records.map((record) => record.processingRate));
  const avgEfficiency = average(records.map((record) => record.efficiency));
  const avgScore = average(records.map((record) => record.performanceScore));

  return [
    { id: "performance-kpi-throughput", label: "Throughput", value: `${round1(avgThroughput)}/hr`, delta: "+6/hr", deltaTone: "success" },
    { id: "performance-kpi-cycle-time", label: "Cycle Time", value: `${round1(avgCycleTime)}s`, delta: "-0.3s", deltaTone: "success" },
    { id: "performance-kpi-utilization", label: "Machine Utilization", value: `${round1(avgUtilization)}%`, delta: "+1.2 pts", deltaTone: "success" },
    { id: "performance-kpi-processing-rate", label: "Battery Processing Rate", value: `${round1(avgProcessingRate)}/min`, delta: "+0.1/min", deltaTone: "success" },
    { id: "performance-kpi-efficiency", label: "Machine Efficiency", value: `${round1(avgEfficiency)}%`, delta: "+0.8 pts", deltaTone: "success" },
    { id: "performance-kpi-score", label: "Performance Score", value: `${Math.round(avgScore)}/100`, delta: "+3 pts", deltaTone: "success" }
  ];
}

function bucketForCycleTime(cycleTime: number): string {
  if (cycleTime < 10) return "<10s";
  if (cycleTime < 12) return "10-12s";
  if (cycleTime < 14) return "12-14s";
  if (cycleTime < 16) return "14-16s";
  return ">16s";
}

function bucketForUtilization(utilization: number): string {
  if (utilization < 70) return "<70%";
  if (utilization < 80) return "70-80%";
  if (utilization < 90) return "80-90%";
  return ">=90%";
}

const CYCLE_BUCKET_TONES: PerformanceTone[] = ["success", "success", "info", "warning", "danger"];
const UTILIZATION_BUCKET_TONES: PerformanceTone[] = ["danger", "warning", "info", "success"];

function buildDistribution(records: PerformanceRecord[], kind: "cycle" | "utilization"): PerformanceDistributionItem[] {
  const buckets = kind === "cycle" ? CYCLE_BUCKETS : UTILIZATION_BUCKETS;
  const tones = kind === "cycle" ? CYCLE_BUCKET_TONES : UTILIZATION_BUCKET_TONES;
  const counts = new Array(buckets.length).fill(0);

  for (const record of records) {
    const bucket = kind === "cycle" ? bucketForCycleTime(record.cycleTime) : bucketForUtilization(record.utilization);
    const index = buckets.indexOf(bucket);
    if (index >= 0) {
      counts[index] += 1;
    }
  }

  return buckets
    .map((bucket, index) => ({ bucket, count: counts[index], tone: tones[index] }))
    .filter((item) => item.count > 0);
}

function buildTrend(records: PerformanceRecord[]): PerformanceTrendPoint[] {
  return DATES.map((date) => {
    const daily = records.filter((record) => record.date === date);
    return {
      date,
      throughput: round1(average(daily.map((record) => record.throughput))),
      utilization: round1(average(daily.map((record) => record.utilization))),
      cycleTime: round1(average(daily.map((record) => record.cycleTime))),
      efficiency: round1(average(daily.map((record) => record.efficiency)))
    };
  });
}

function buildComparisons(records: PerformanceRecord[], kind: "Machine" | "Product"): PerformanceComparisonItem[] {
  const names = [...new Set(records.map((record) => (kind === "Machine" ? record.machine : record.product)))];
  const fleetThroughput = average(records.map((record) => record.throughput));
  const fleetCycleTime = average(records.map((record) => record.cycleTime));
  const fleetUtilization = average(records.map((record) => record.utilization));
  const fleetEfficiency = average(records.map((record) => record.efficiency));
  const fleetScore = average(records.map((record) => record.performanceScore));

  return names.map((name, index) => {
    const subset = records.filter((record) => (kind === "Machine" ? record.machine : record.product) === name);
    const throughput = average(subset.map((record) => record.throughput));
    const cycleTime = average(subset.map((record) => record.cycleTime));
    const utilization = average(subset.map((record) => record.utilization));
    const efficiency = average(subset.map((record) => record.efficiency));
    const score = average(subset.map((record) => record.performanceScore));
    const metrics: PerformanceMetric[] = [
      { label: "Throughput", value: `${round1(throughput)}/hr`, tone: throughput >= fleetThroughput ? "success" : "warning" },
      { label: "Cycle Time", value: `${round1(cycleTime)}s`, tone: cycleTime <= fleetCycleTime ? "success" : "warning" },
      { label: "Utilization", value: `${round1(utilization)}%`, tone: utilization >= fleetUtilization ? "success" : "warning" },
      { label: "Efficiency", value: `${round1(efficiency)}%`, tone: efficiency >= fleetEfficiency ? "success" : "warning" },
      { label: "Performance Score", value: `${Math.round(score)}/100`, tone: score >= fleetScore ? "success" : "warning" }
    ];

    return {
      id: `${kind.toLowerCase()}-comparison-${index + 1}`,
      name,
      kind,
      metrics,
      statusTone: score >= 85 ? "success" : score >= 70 ? "warning" : "danger"
    };
  });
}

function buildCharts(): PerformanceChartPlaceholder[] {
  return [
    { id: "performance-chart-throughput-trend", title: "Throughput Trend", description: "Placeholder chart container for throughput over time." },
    { id: "performance-chart-utilization-trend", title: "Utilization Trend", description: "Placeholder chart container for machine utilization over time." },
    { id: "performance-chart-cycle-time-trend", title: "Cycle Time Trend", description: "Placeholder chart container for cycle time over time." }
  ];
}

const mockRecords = buildRecords();

export function getMockPerformanceAnalytics() {
  const records = mockRecords;

  return {
    records,
    kpis: buildKpis(records),
    cycleDistribution: buildDistribution(records, "cycle"),
    utilizationDistribution: buildDistribution(records, "utilization"),
    trend: buildTrend(records),
    machineComparisons: buildComparisons(records, "Machine"),
    productComparisons: buildComparisons(records, "Product"),
    charts: buildCharts()
  };
}
