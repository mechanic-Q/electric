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

export type ChatEvent =
  | { type: "token"; content: string }
  | { type: "tool_call"; name?: string; args?: unknown }
  | { type: "tool_result"; name?: string; content?: string; payload?: unknown }
  | { type: "error"; message?: string; content?: string }
  | { type: "done" };
