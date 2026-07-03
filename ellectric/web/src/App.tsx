import { useState, useEffect, useRef } from "react";
import type { CapabilityItem, DatasetInfo, ReportSummary } from "./types";
import { fetchCapabilities, fetchDatasets, fetchReports, streamChat } from "./api";
import "./styles.css";

const FORECAST_CATEGORIES = ["load", "price", "wind", "solar"];
const CATEGORY_LABEL: Record<string, string> = {
  load: "负荷预测", price: "电价预测", wind: "风电预测", solar: "光伏预测",
};

function statusBadge(status: string) {
  return <span className={`badge badge-${status}`}>{status}</span>;
}

function sourceTag(source: string) {
  return <span className={`source-tag badge-${source}`}>{source}</span>;
}

function chainArrow() {
  return <div className="chain-arrow">→</div>;
}

type CopilotMessage =
  | { role: "user"; content: string }
  | { role: "assistant"; content: string }
  | { role: "tool_call"; name?: string; args?: unknown }
  | { role: "tool_result"; name?: string; content?: string; payload?: unknown }
  | { role: "error"; content: string };

function CopilotPanel() {
  const [messages, setMessages] = useState<CopilotMessage[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [streamingText, setStreamingText] = useState("");
  const [configError, setConfigError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const streamingTextRef = useRef("");
  const msgsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    msgsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingText]);

  useEffect(() => {
    if (messages.length === 0) {
      setMessages([{
        role: "assistant",
        content: "你好！我是 Ellectric Copilot，可以帮助你解读 Dashboard 上的学习指标和报告。请注意：所有策略评估和预测结果仅供学习参考。",
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
          setConfigError("DEEPSEEK_API_KEY 未配置，请在 .env 中设置。");
        }
        setMessages((prev) => [...prev, { role: "error", content: msg || "未知错误" }]);
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
    }, ac.signal);
  };

  const cancel = () => {
    abortRef.current?.abort();
    setStreaming(false);
    setStreamingText("");
    streamingTextRef.current = "";
    abortRef.current = null;
  };

  return (
    <aside className="copilot-panel">
      <div className="copilot-header">Copilot</div>
      {configError && <div className="copilot-config-error">⚠️ {configError}</div>}
      <div className="copilot-messages">
        {messages.map((msg, i) => {
          switch (msg.role) {
            case "user":
              return <div key={i} className="message message-user">{msg.content}</div>;
            case "assistant":
              return <div key={i} className="message message-assistant">{msg.content}</div>;
            case "tool_call":
              return (
                <div key={i} className="message message-tool-call">
                  🔧 {msg.name}({JSON.stringify(msg.args)})
                </div>
              );
            case "tool_result":
              return (
                <div key={i} className="message message-tool-result">
                  <div className="tool-result-card">
                    <div className="tool-result-header">{msg.name || "工具结果"}</div>
                    <pre className="tool-result-body">{JSON.stringify(msg.payload ?? msg.content, null, 2)}</pre>
                  </div>
                </div>
              );
            case "error":
              return <div key={i} className="message message-error">⚠️ {msg.content}</div>;
          }
        })}
        {streaming && streamingText && (
          <div className="message message-assistant">
            {streamingText}<span className="streaming-cursor" />
          </div>
        )}
        <div ref={msgsEndRef} />
      </div>
      <div className="copilot-input-area">
        <textarea
          className="copilot-input"
          placeholder="问关于 Dashboard 的问题..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); } }}
          rows={2}
          disabled={streaming}
        />
        {streaming ? (
          <button className="copilot-btn copilot-btn-cancel" onClick={cancel}>停止</button>
        ) : (
          <button className="copilot-btn copilot-btn-send" onClick={sendMessage} disabled={!input.trim()}>发送</button>
        )}
      </div>
    </aside>
  );
}

export default function App() {
  const [caps, setCaps] = useState<CapabilityItem[]>([]);
  const [capsLoading, setCapsLoading] = useState(true);
  const [capsError, setCapsError] = useState<string | null>(null);

  const [datasets, setDatasets] = useState<DatasetInfo[]>([]);
  const [dsLoading, setDsLoading] = useState(true);
  const [dsError, setDsError] = useState<string | null>(null);

  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [repLoading, setRepLoading] = useState(true);
  const [repError, setRepError] = useState<string | null>(null);

  useEffect(() => {
    const ac = new AbortController();
    fetchCapabilities(ac.signal)
      .then((d) => { setCaps(d.filter((c) => FORECAST_CATEGORIES.includes(c.category))); setCapsLoading(false); })
      .catch((e) => { if (e.name !== "AbortError") { setCapsError(e.message); setCapsLoading(false); } });
    fetchDatasets(ac.signal)
      .then((d) => { setDatasets(d); setDsLoading(false); })
      .catch((e) => { if (e.name !== "AbortError") { setDsError(e.message); setDsLoading(false); } });
    fetchReports(undefined, ac.signal)
      .then((d) => { setReports(d); setRepLoading(false); })
      .catch((e) => { if (e.name !== "AbortError") { setRepError(e.message); setRepLoading(false); } });
    return () => ac.abort();
  }, []);

  const rlReports = reports.filter((r) => r.report_type?.toLowerCase().includes("rl"));
  const otherReports = reports.filter((r) => !r.report_type?.toLowerCase().includes("rl"));

  return (
    <div className="app">
      <header className="header">
        <h1 className="header-title">Ellectric — AI + 电力交易技术学习平台</h1>
        <p className="header-subtitle">⚠ 学习原型 · 非交易建议 · 历史回测不预示未来表现</p>
        <span className="badge badge-shandong">山东 15min 数据 · 71,520 行 · 2023-2025</span>
      </header>

      <div className="app-layout">
        <main className="dashboard-main">

      {/* Value Chain */}
      <section className="section">
        <h2 className="section-title">端到端价值链</h2>
        <div className="value-chain">
          {[
            ["公开数据", "山东出清数据"],
            ["负荷/电价/风光预测", "XGBoost / LEAR"],
            ["回测/RL评估", "PPO / SAC / TD3"],
            ["SHAP/Weather解释", "模型可解释性"],
            ["报告溯源", "状态与指标"],
          ].map(([label, desc], i) => (
            <div key={i} className="chain-step">
              <div className="chain-label">{label}</div>
              <div className="chain-desc">{desc}</div>
              {i < 4 && chainArrow()}
            </div>
          ))}
        </div>
      </section>

      {/* Forecast Lab */}
      <section className="section">
        <h2 className="section-title">预测实验室</h2>
        {capsLoading && <p className="loading">加载预测能力数据...</p>}
        {capsError && <p className="error">预测能力数据不可用: {capsError}</p>}
        {!capsLoading && !capsError && (
          caps.length === 0
            ? <p className="unavailable">暂无预测能力数据</p>
            : <div className="card-grid">
                {caps.map((c) => (
                  <div key={c.id} className="card">
                    <div className="card-header">
                      <span className="card-title">{c.title}</span>
                      {sourceTag(c.available !== false ? "api" : "offline_report")}
                    </div>
                    <span className="card-category">{CATEGORY_LABEL[c.category] || c.category}</span>
                    <p className="card-desc">{c.description}</p>
                  </div>
                ))}
              </div>
        )}
      </section>

      {/* Strategy Evaluation */}
      <section className="section">
        <h2 className="section-title">策略评估</h2>
        {repLoading && <p className="loading">加载策略报告...</p>}
        {repError && <p className="error">策略报告不可用: {repError}</p>}
        {!repLoading && !repError && (
          rlReports.length === 0
            ? <p className="unavailable">暂无 RL 策略评估报告</p>
            : <>
                <div className="card-grid">
                {rlReports.map((r) => (
                  <div key={r.id} className="card">
                    <div className="card-header">
                      <span className="card-title">{r.title}</span>
                      {statusBadge(r.status)}
                    </div>
                    <p className="card-desc">{r.summary}</p>
                    {r.metrics && Object.keys(r.metrics).length > 0 && (
                      <div className="card-metrics">
                        {Object.entries(r.metrics).map(([k, v]) => (
                          <div key={k} className="metric">
                            <span className="metric-label">{k}</span>
                            <span className="metric-value">{String(v ?? "—")}</span>
                          </div>
                        ))}
                      </div>
                    )}
                    {r.paths && Object.keys(r.paths).length > 0 && (
                      <div className="card-footer">
                        {Object.entries(r.paths).slice(0, 2).map(([k, v]) => (
                          <span key={k} className="report-path">
                            {k === "report" ? "📄 " : "📁 "}{v}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
                <p className="disclaimer">以上为历史回测结果，仅用于策略评估学习，不构成投资建议。</p>
              </>
        )}
      </section>

      {/* Explainability + Reports / Data */}
      <section className="section">
        <h2 className="section-title">可解释性 & 报告溯源</h2>
        <div className="card-grid">
          {/* SHAP card */}
          <div className="card">
            <div className="card-header">
              <span className="card-title">SHAP 模型解释</span>
              {sourceTag("offline_report")}
            </div>
            <p className="card-desc">XGBoost / LEAR 特征贡献度分析（SHAP 瀑布图）</p>
            <div className="card-footer">
              <span className="status-indicator">
                <span className="status-dot" style={{background: "var(--green)"}} />
                可用
              </span>
            </div>
          </div>

          {/* Weather Tier4 card */}
          <div className="card">
            <div className="card-header">
              <span className="card-title">Weather Tier4 特征</span>
              {sourceTag("offline_report")}
            </div>
            <p className="card-desc">气象特征集成与精度影响验证报告</p>
            <div className="card-footer">
              <span className="status-indicator">
                <span className="status-dot" style={{background: "var(--green)"}} />
                可用
              </span>
            </div>
          </div>

          {/* Dataset info cards */}
          {dsLoading && <p className="loading">加载数据集信息...</p>}
          {dsError && <p className="error">数据集信息不可用: {dsError}</p>}
          {!dsLoading && !dsError && datasets.map((d) => (
            <div key={d.id} className="card">
              <div className="card-header">
                <span className="card-title">{d.title}</span>
                {d.available !== false ? sourceTag("api") : sourceTag("offline_report")}
              </div>
              <p className="card-desc">{d.description}</p>
              <div className="dataset-rows">
                {d.rows != null && <span>{d.rows.toLocaleString()} 行</span>}
                {d.source && <span> · 来源: {d.source}</span>}
                {d.frequency && <span> · {d.frequency}</span>}
              </div>
            </div>
          ))}

          {/* Report list with status */}
          {repLoading && <p className="loading">加载报告列表...</p>}
          {repError && <p className="error">报告列表不可用: {repError}</p>}
          {!repLoading && !repError && otherReports.map((r) => (
            <div key={r.id} className="card">
              <div className="card-header">
                <span className="card-title">{r.title}</span>
                {statusBadge(r.status)}
              </div>
              <p className="card-desc">{r.summary}</p>
              {r.metrics && Object.keys(r.metrics).length > 0 && (
                <div className="card-metrics">
                  {Object.entries(r.metrics).slice(0, 3).map(([k, v]) => (
                    <div key={k} className="metric">
                      <span className="metric-label">{k}</span>
                      <span className="metric-value">{String(v ?? "—")}</span>
                    </div>
                  ))}
                </div>
              )}
              {r.generated_at && <span style={{fontSize: "0.7rem", color: "var(--text-muted)"}}>{r.generated_at}</span>}
            </div>
          ))}
        </div>
      </section>
        </main>
        <CopilotPanel />
      </div>
    </div>
  );
}
