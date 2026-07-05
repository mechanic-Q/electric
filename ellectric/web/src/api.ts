import type { CapabilityItem, DatasetInfo, ReportDetail, ReportSummary, RollingDemoResponse } from "./types";

async function fetchJson<T>(url: string, signal?: AbortSignal): Promise<T> {
  const res = await fetch(url, { signal });
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
  return res.json();
}

export function fetchCapabilities(signal?: AbortSignal): Promise<CapabilityItem[]> {
  return fetchJson("/capabilities", signal);
}

export function fetchDatasets(signal?: AbortSignal): Promise<DatasetInfo[]> {
  return fetchJson("/datasets", signal);
}

export function fetchReports(
  reportType?: string,
  signal?: AbortSignal,
): Promise<ReportSummary[]> {
  const url = reportType
    ? `/reports?report_type=${encodeURIComponent(reportType)}`
    : "/reports";
  return fetchJson(url, signal);
}

export function fetchReportDetail(
  reportId: string,
  signal?: AbortSignal,
): Promise<ReportDetail> {
  const encoded = reportId.split("/").map(encodeURIComponent).join("/");
  return fetchJson(`/reports/${encoded}`, signal);
}

export function fetchRollingDemo(signal?: AbortSignal): Promise<RollingDemoResponse> {
  return fetchJson("/dashboard/rolling-demo", signal);
}

async function* readSSE(
  body: ReadableStream<Uint8Array>,
): AsyncGenerator<Record<string, unknown>> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      const parts = buffer.split("\n\n");
      buffer = parts.pop() || "";

      for (const part of parts) {
        for (const line of part.split("\n")) {
          if (line.startsWith("data: ")) {
            const raw = line.slice(6).trim();
            if (raw && raw !== "[DONE]") {
              yield JSON.parse(raw);
            }
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

export interface ChatCallbacks {
  onToken?: (text: string) => void;
  onToolCall?: (name?: string, args?: unknown) => void;
  onToolResult?: (name?: string, content?: string, payload?: unknown) => void;
  onError?: (message?: string) => void;
  onDone?: () => void;
}

export async function streamChat(
  query: string,
  history: Array<{ role: string; content: string }>,
  callbacks: ChatCallbacks,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch("/chat/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, history }),
    signal,
  });

  if (!res.ok) {
    callbacks.onError?.(`HTTP ${res.status}`);
    return;
  }

  if (!res.body) {
    callbacks.onError?.("No response body");
    return;
  }

  try {
    for await (const event of readSSE(res.body)) {
      const { type, ...rest } = event as { type: string; [k: string]: unknown };
      switch (type) {
        case "token":
          callbacks.onToken?.(rest.content as string);
          break;
        case "tool_call":
          callbacks.onToolCall?.(rest.name as string | undefined, rest.args);
          break;
        case "tool_result":
          callbacks.onToolResult?.(
            rest.name as string | undefined,
            rest.content as string | undefined,
            rest.payload,
          );
          break;
        case "error":
          callbacks.onError?.(rest.message as string | undefined);
          break;
        case "done":
          callbacks.onDone?.();
          break;
      }
    }
  } catch (err) {
    if (signal?.aborted) return;
    callbacks.onError?.((err as Error).message);
  }
}
