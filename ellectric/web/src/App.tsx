import { useState, useEffect, useRef } from "react";
import type { ReplayContext, RollingDemoResponse } from "./types";
import { fetchRollingDemo, streamChat } from "./api";
import { ReplayStage } from "./ReplayStage";
import { StrategyComparison } from "./StrategyComparison";
import { renderMarkdown } from "./MarkdownRenderer";
import "./styles.css";

type CopilotMessage =
  | { role: "user"; content: string }
  | { role: "assistant"; content: string }
  | { role: "tool_call"; name?: string; args?: unknown }
  | { role: "tool_result"; name?: string; content?: string; payload?: unknown }
  | { role: "error"; content: string };

const statusLabels: Record<string, string> = {
  ok: "正常 / OK",
  missing: "缺失 / Missing",
  error: "错误 / Error",
  degraded: "降级 / Degraded",
};

const metricLabels: Record<string, string> = {
  baseline_mae: "基线 MAE / Baseline MAE",
  wind_mae: "风电 MAE / Wind MAE",
  wind_nrmse: "风电 NRMSE / Wind NRMSE",
  solar_mae: "光伏 MAE / Solar MAE",
  solar_nrmse: "光伏 NRMSE / Solar NRMSE",
  validate_weather_tier4_status: "Weather Tier4 状态 / Weather Tier4 status",
  validate_renewable_forecaster_status: "风光预测状态 / Renewable forecast status",
  compare_price_models_status: "电价模型对比状态 / Price model comparison status",
  pytest_status: "测试状态 / Test status",
  verify_time_resolution_status: "时间分辨率验证状态 / Time resolution status",
  rl_ppo_status: "PPO 状态 / PPO status",
  rl_sac_status: "SAC 状态 / SAC status",
  rl_td3_status: "TD3 状态 / TD3 status",
};

function bilingualStatus(status: string): string {
  return statusLabels[status] ?? `未知状态 / Unknown status: ${status}`;
}

function bilingualMetric(key: string): string {
  return metricLabels[key] ?? `${key} / ${key.replace(/_/g, " ")}`;
}

function bilingualValue(value: unknown): string {
  return typeof value === "string" && statusLabels[value] ? bilingualStatus(value) : String(value);
}

function bilingualReportTitle(title: string): string {
  if (title === "Weather Tier4 负荷预测验证") return "Weather Tier4 负荷预测验证 / Weather Tier4 Load Forecast Validation";
  if (title === "风光出力预测验证") return "风光出力预测验证 / Renewable Output Forecast Validation";
  if (title.startsWith("全量运行")) return `${title} / Full Run`;
  return `${title} / Report`;
}

function bilingualReportSummary(summary: string): string {
  if (summary.includes("Ablation: degraded")) {
    return `消融实验：降级（天气特征不可用或训练失败） / ${summary}`;
  }
  if (summary === "风光出力预测验证 验证结果。") {
    return "风光出力预测验证结果。 / Renewable output forecast validation result.";
  }
  if (summary === "Weather + 风光 + 电价 + RL 全量运行汇总。") {
    return "Weather + 风光 + 电价 + RL 全量运行汇总。 / Full-run summary: weather + renewable + price + RL.";
  }
  return `${summary} / Source report summary`;
}

function CopilotPanel({ replayContext }: { replayContext: ReplayContext | null }) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<CopilotMessage[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [streamingText, setStreamingText] = useState("");
  const [configError, setConfigError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const streamingTextRef = useRef("");
  const msgsEndRef = useRef<HTMLDivElement>(null);
  const msgsContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = msgsContainerRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, streamingText]);

  useEffect(() => {
    if (messages.length === 0) {
      setMessages([{
        role: "assistant",
        content: "你好！我是 Ellectric Copilot，可以用通俗语言解释这个展示页面、XGBoost/LEAR/RL 等术语，以及离线报告里的结果。\nHello! I am Ellectric Copilot. I can explain this showcase dashboard, core terms like XGBoost/LEAR/RL, and the offline report results in plain language.",
      }]);
    }
  }, []);

  useEffect(() => {
    return () => abortRef.current?.abort();
  }, []);

  const sendMessage = async () => {
    const text = input.trim();
    if (!text || streaming) return;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setStreaming(true);
    setStreamingText("");
    streamingTextRef.current = "";

    const ac = new AbortController();
    abortRef.current = ac;

    const history = messages
      .filter((m): m is { role: "user" | "assistant"; content: string } =>
        m.role === "user" || m.role === "assistant")
      .map((m) => ({ role: m.role, content: m.content }));

    await streamChat(text, history, {
      onToken: (t) => {
        streamingTextRef.current += t;
        setStreamingText(streamingTextRef.current);
      },
      onToolCall: (name, args) => {
        setMessages((prev) => [...prev, { role: "tool_call", name, args }]);
      },
      onToolResult: (name, content, payload) => {
        setMessages((prev) => [...prev, { role: "tool_result", name, content, payload }]);
      },
      onError: (msg) => {
        if (msg?.includes("401") || msg?.toLowerCase().includes("key") || msg?.toLowerCase().includes("api_key")) {
          setConfigError("DEEPSEEK_API_KEY 未配置，请在 .env 中设置。/ DEEPSEEK_API_KEY is missing. Set it in .env.");
        }
        setMessages((prev) => [...prev, { role: "error", content: msg || "未知错误 / Unknown error" }]);
      },
      onDone: () => {
        const finalText = streamingTextRef.current;
        if (finalText.trim()) {
          setMessages((prev) => [...prev, { role: "assistant", content: finalText }]);
        }
        streamingTextRef.current = "";
        setStreamingText("");
        setStreaming(false);
        abortRef.current = null;
      },
    }, replayContext, ac.signal);
  };

  const cancel = () => {
    abortRef.current?.abort();
    setStreaming(false);
    setStreamingText("");
    streamingTextRef.current = "";
    abortRef.current = null;
  };

  return (
    <>
      <div className={"copilot-backdrop" + (open ? " open" : "")} onClick={() => setOpen(false)} />
      <aside className={"copilot-panel" + (open ? " open" : "")}>
        <div className="copilot-header">AI智能体专职讲解</div>
      {configError && <div className="copilot-config-error">⚠️ {configError}</div>}
      <div className="copilot-messages" ref={msgsContainerRef}>
          {messages.map((msg, i) => {
          switch (msg.role) {
            case "user":
              return <div key={i} className="message message-user">{msg.content}</div>;
            case "assistant":
              return <div key={i} className="message message-assistant">{renderMarkdown(msg.content)}</div>;
            case "tool_call":
              return (
                <div key={i} className="message message-tool-call">
                  🔧 查询 {msg.name}…
                </div>
              );
            case "tool_result":
              const resultText = typeof msg.content === "string" ? msg.content : JSON.stringify(msg.content, null, 2);
              return (
                <details key={i} className="message-tool-result-details">
                  <summary>{msg.name || "工具结果 / Tool result"}</summary>
                  <pre className="tool-result-body">{resultText}</pre>
                </details>
              );
            case "error":
              return <div key={i} className="message message-error">⚠️ {msg.content}</div>;
          }
        })}
        {streaming && streamingText && (
          <div className="message message-assistant">
            {renderMarkdown(streamingText)}<span className="streaming-cursor" />
          </div>
        )}
        <div ref={msgsEndRef} />
      </div>
      <div className="copilot-input-area">
        <textarea
          className="copilot-input"
          placeholder="问关于 Dashboard 的问题... / Ask about this Dashboard..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); } }}
          rows={2}
          disabled={streaming}
        />
        {streaming ? (
          <button className="copilot-btn copilot-btn-cancel" onClick={cancel}>停止 / Stop</button>
        ) : (
          <button className="copilot-btn copilot-btn-send" onClick={sendMessage} disabled={!input.trim()}>发送 / Send</button>
        )}
      </div>
    </aside>
    <div className="copilot-toggle-bar" onClick={() => setOpen(o => !o)}>
      💬 Copilot {open ? "关闭 / Close" : "打开 / Open"}
    </div>
  </>
  );
}

export default function App() {
  const [data, setData] = useState<RollingDemoResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [replayContext, setReplayContext] = useState<ReplayContext | null>(null);

  useEffect(() => {
    const ac = new AbortController();
    fetchRollingDemo(ac.signal)
      .then((d) => {
        setData(d);
        setLoading(false);
      })
      .catch((e) => {
        if (e.name !== "AbortError") {
          setError(e.message);
          setLoading(false);
        }
      });
    return () => ac.abort();
  }, []);

  if (loading) return <div className="app"><p className="loading">加载数据剧场... / Loading data theater...</p></div>;
  if (error) return <div className="app"><p className="error">数据不可用 / Data unavailable: {error}</p></div>;

  return (
    <div className="app">
      <header className="app-header">
        <div>
          <h1>Ellectric — AI + 电力交易技术学习平台</h1>
          <h2 className="header-subtitle">山东 15min 数据剧场 / Shandong 15min Data Theater</h2>
          <p className="header-sub-info">
            {data?.meta.start} → {data?.meta.end} · {data?.meta.rows.toLocaleString()} 点 / points · 只读滚动演示端点 / rolling demo readonly endpoint
          </p>
        </div>
        <span className="badge badge-shandong" style={{ marginTop: 0 }}>学习原型 / Learning prototype · 非真实交易 / no real trading</span>
      </header>

      <div className="app-layout">
        <main className="dashboard-main">
          <ReplayStage data={data!} onContextChange={setReplayContext} />

          <section className="section panel-grid panel-grid-section">
            <StrategyComparison strategy={data!.strategy} />
            <article className="evidence-report-panel">
              <div className="evidence-report-header"><h3 className="evidence-report-title">证据报告 / Evidence</h3><span className="badge badge-shandong" style={{ margin: 0 }}>报告 / reports</span></div>
                <div className="evidence-report-body">
                  {data!.reports.filter((r) => r.id !== "rl_full_dataset/evaluation").map((r) => (
                    <div key={r.id} className="evidence-card">
                      <div className="evidence-header">
                        <span className="evidence-title">{bilingualReportTitle(r.title)}</span>
                        <span className={`badge badge-${r.status}`}>{bilingualStatus(r.status)}</span>
                      </div>
                      <p className="evidence-summary">{bilingualReportSummary(r.summary)}</p>
                      {Object.keys(r.metrics).length > 0 && (
                        <div className="evidence-metrics">
                          {Object.entries(r.metrics).map(([k, v]) => (
                            <span key={k} className="metric-item">
                              <span className="metric-label">{bilingualMetric(k)}</span>
                              <span className="metric-value">{bilingualValue(v)}</span>
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
            </article>
            <details className="technical-interface">
              <summary>技术接口 / Technical interface</summary>
              <div>
                <code>GET /rolling-demo.json</code>
                <span>只读静态数据 · 返回 meta, series, panels, strategy, reports, warnings</span>
              </div>
            </details>
            <details open className="tools-pipeline">
              <summary>技术工具与流程 / Tools & Pipeline</summary>
              <ol className="tools-flow">
                <li><span className="tf-stage">① 数据接入 / Data</span><span className="tf-tool">ShandongDataLoader · WeatherFetcher</span></li>
                <li><span className="tf-stage">② 负荷预测 / Load</span><span className="tf-tool">XGBoost + TimeSeriesSplit</span></li>
                <li><span className="tf-stage">③ 电价预测 / Price</span><span className="tf-tool">LEAR (Lasso L1)</span></li>
                <li><span className="tf-stage">④ 风光出力 / Renewable</span><span className="tf-tool">WindPowerForecaster · SolarPowerForecaster</span></li>
                <li><span className="tf-stage">⑤ RL交易+回测 / RL Trading</span><span className="tf-tool">ElectricityMarketEnv · BacktestRunner (PPO/SAC/TD3)</span></li>
                <li><span className="tf-stage">⑥ 可解释性 / Explainability</span><span className="tf-tool">SHAP (Tree + Linear)</span></li>
                <li><span className="tf-stage">⑦ 展示+对话 / Showcase</span><span className="tf-tool">FastAPI · React WebUI · DeepSeek Copilot</span></li>
              </ol>
              <p className="tools-footnote">* ASSUME 仅为独立学习实验，未接入集成管道。 / ASSUME is a standalone learning experiment, not part of the integrated pipeline.</p>
            </details>
          </section>
        </main>
        <CopilotPanel replayContext={replayContext} />
      </div>
    </div>
  );
}
