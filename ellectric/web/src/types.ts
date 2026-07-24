export type SourceStatus = "api" | "offline_report" | "fallback" | "missing" | "error";

export interface CapabilityItem {
  id: string;
  title: string;
  category: string;
  description: string;
  example_questions: string[];
  endpoint?: string | null;
  tool_name?: string | null;
  supports_offline_fallback?: boolean;
  available?: boolean;
}

export interface DatasetInfo {
  id: string;
  title: string;
  description: string;
  source: string;
  frequency?: string | null;
  rows?: number | null;
  start?: string | null;
  end?: string | null;
  columns?: string[];
  available?: boolean;
}

export interface ReportSummary {
  id: string;
  title: string;
  report_type: string;
  status: "ok" | "missing" | "error" | "degraded";
  generated_at?: string | null;
  summary: string;
  metrics?: Record<string, number | string | boolean | null>;
  paths?: Record<string, string>;
}

export interface ReportDetail {
  id: string;
  status: "ok" | "missing" | "error" | "degraded";
  report_type?: string;
  title?: string;
  summary?: string;
  content?: string;
  metrics?: Record<string, number | string | boolean | null>;
  metrics_meta?: Record<string, { label: string; unit?: string }>;
}

export interface RollingDemoMeta {
  source: string;
  start: string;
  end: string;
  frequency: string;
  points_per_day: number;
  rows: number;
}

export interface RollingDemoSeries {
  timestamps: string[];
  load_actual: (number | null)[];
  load_forecast: (number | null)[];
  price_rt: (number | null)[];
  price_da: (number | null)[];
  wind_actual: (number | null)[];
  solar_actual: (number | null)[];
  tie_line: (number | null)[];
  pumped_storage: (number | null)[];
}

export interface RollingDemoPanel {
  id: string;
  title: string;
  chart_type: string;
  summary: string;
  metrics: Record<string, number | string>;
  warning_ids: string[];
}

export interface StrategySummaryRow {
  strategy: StrategyKey;
  simulated_spread_value: number;
  profitable_days: number;
  active_positive_contribution_rate: number;
  approximately_flat_period_rate: number;
  max_drawdown: number;
  profit_factor: number;
  trend_multiple: number;
  oracle_capture_rate: number;
  facts: string[];
}

export type StrategyKey = "td3" | "ppo" | "sac" | "trend";
export type PositionState = "long" | "short" | "approximately_flat" | "indeterminate";

export interface StrategyPointSeries {
  simulated_spread_value: number[];
  cumulative_simulated_spread_value: number[];
  reconstructed_position: (number | null)[];
  position_state: PositionState[];
}

export interface StrategyTimeseries {
  timestamps: string[];
  daily_baseline_price: number[];
  strategies: Record<StrategyKey, StrategyPointSeries>;
}

export interface StrategyDailySeries {
  simulated_spread_value: number[];
  cumulative_simulated_spread_value: number[];
  long_periods: number[];
  short_periods: number[];
  approximately_flat_periods: number[];
  indeterminate_periods: number[];
  mean_absolute_position: (number | null)[];
}

export interface StrategyDailyEvidence {
  dates: string[];
  baseline_initialization: boolean[];
  strategies: Record<StrategyKey, StrategyDailySeries>;
}

export interface StrategyEvidenceWindow {
  start: string;
  end: string;
  timezone: string;
  points: number;
  points_per_day: number;
  standardized_day: string;
}

export interface StrategyMethodology {
  value_name: string;
  unit: string;
  settlement_price: string;
  formula: string;
  capacity_scale_mw: number;
  capacity_scale_source: string;
  baseline_initialization_days: number;
  baseline_after_initialization: string;
  approximate_flat_position_threshold: number;
  indeterminate_spread_threshold_cny_per_mwh: number;
  reconstructed_position_bound: number;
  zero_reference: string;
}

export interface LongTermStrategyEvidence {
  title: string;
  window: { start: string; end: string; timezone: string };
  training_window: { start: string; end: string };
  points: number;
  cumulative_leader: string;
  terminal_simulated_spread_value: Record<string, number>;
  source_report: string;
  purpose: string;
}

export interface StrategyProvenance {
  source_generated_at: string;
  source_git_sha: string;
  training_steps_per_algorithm: number;
  seed: number;
  feature_tier: string;
  source_evaluation_window: {
    start: string;
    end_exclusive: string;
    points: number;
  };
  source_artifacts: Record<string, string>;
  source_hashes: Record<string, string>;
  content_hash: string;
}

interface StrategyCommon {
  degradation_reason?: string | null;
  snapshot_version?: number | null;
}

export interface RollingDemoStrategyOk extends StrategyCommon {
  status: "ok";
  window: StrategyEvidenceWindow;
  methodology: StrategyMethodology;
  summary: StrategySummaryRow[];
  timeseries: StrategyTimeseries;
  daily: StrategyDailyEvidence;
  oracle: Record<string, unknown>;
  long_term_evidence: LongTermStrategyEvidence;
  provenance: StrategyProvenance;
}

export interface RollingDemoStrategyDegraded extends StrategyCommon {
  status: "degraded";
  window?: StrategyEvidenceWindow;
  methodology?: StrategyMethodology;
  summary?: StrategySummaryRow[];
  timeseries?: StrategyTimeseries;
  daily?: StrategyDailyEvidence;
  oracle?: Record<string, unknown>;
  long_term_evidence?: LongTermStrategyEvidence;
  provenance?: StrategyProvenance;
}

export type RollingDemoStrategy = RollingDemoStrategyOk | RollingDemoStrategyDegraded;

export interface RollingDemoReportEvidence {
  id: string;
  title: string;
  status: string;
  summary: string;
  metrics: Record<string, number | string>;
}

export interface RollingDemoResponse {
  meta: RollingDemoMeta;
  series: RollingDemoSeries;
  panels: RollingDemoPanel[];
  strategy: RollingDemoStrategy;
  reports: RollingDemoReportEvidence[];
  warnings: string[];
}

export type ChatEvent =
  | { type: "token"; content: string }
  | { type: "tool_call"; name?: string; args?: unknown }
  | { type: "tool_result"; name?: string; content?: string; payload?: unknown }
  | { type: "error"; message?: string; content?: string }
  | { type: "done" };
