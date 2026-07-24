import { useState, useEffect, useRef, useMemo } from "react";
import type { RollingDemoResponse, RollingDemoSeries } from "./types";
import { fetchRollingDemo, streamChat } from "./api";
import { StrategyComparison } from "./StrategyComparison";
import "./styles.css";

/* ── SVG chart helpers ── */
function svgPoints(data: (number | null)[], w: number, h: number): string {
  const len = data.length;
  if (len < 2) return "";
  const vals = data.filter((v): v is number => v != null);
  if (vals.length === 0) return "";
  const min = Math.min(...vals);
  const max = Math.max(...vals);
  const rng = max - min || 1;
  const pad = 3;
  const uh = h - pad * 2;
  return data.map((v, i) => {
    const x = (i / (len - 1)) * w;
    const y = pad + uh - (((v ?? min) - min) / rng) * uh;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");
}

function svgArea(data: (number | null)[], w: number, h: number): string {
  const pts = svgPoints(data, w, h);
  if (!pts) return "";
  const coords = pts.split(" ");
  const fx = coords[0].split(",")[0];
  const lx = coords[coords.length - 1].split(",")[0];
  return `M${pts} L${lx},${h} L${fx},${h} Z`;
}

function LoadChartSVG({ series, tick }: { series: RollingDemoSeries; tick: number }) {
  const w = 600, h = 170;
  const actual = svgPoints(series.load_actual, w, h);
  const forecast = svgPoints(series.load_forecast, w, h);
  const tx = series.timestamps.length > 1 ? (tick / (series.timestamps.length - 1)) * w : 0;
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="chart-svg" aria-label="负荷与预测折线图 / Load and forecast line chart">
      {actual && <polyline fill="none" stroke="#2dd4bf" strokeWidth="2.5" points={actual} />}
      {forecast && <polyline fill="none" stroke="#f59e0b" strokeWidth="1.5" strokeDasharray="6 4" points={forecast} />}
      <line x1={tx} y1="0" x2={tx} y2={h} stroke="#2dd4bf" strokeWidth="1.5" opacity="0.7" />
    </svg>
  );
}

function RenewableChartSVG({ series }: { series: RollingDemoSeries }) {
  const w = 400, h = 150;
  const wPath = svgArea(series.wind_actual, w, h);
  const sPath = svgArea(series.solar_actual, w, h);
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="chart-svg" aria-label="风光堆叠面积图 / Renewable stacked area chart">
      {wPath && <path d={wPath} fill="rgba(45,212,191,0.34)" />}
      {sPath && <path d={sPath} fill="rgba(245,158,11,0.34)" />}
    </svg>
  );
}

function PriceHeatmapGrid({ data }: { data: RollingDemoResponse }) {
  const ppd = data.meta.points_per_day;
  const hpDay = 24;
  const tpH = ppd / hpDay;
  const maxDays = Math.min(Math.floor(data.series.price_rt.length / ppd), 30);

  const cells = useMemo(() => {
    const values: number[] = [];
    let minV = Infinity, maxV = -Infinity;
    for (let d = 0; d < maxDays; d++) {
      for (let h = 0; h < hpDay; h++) {
        let sum = 0, cnt = 0;
        for (let t = 0; t < tpH; t++) {
          const idx = d * ppd + h * tpH + t;
          const val = data.series.price_rt[idx];
          if (val != null) { sum += val; cnt++; }
        }
        const avg = cnt > 0 ? sum / cnt : 0;
        values.push(avg);
        if (avg < minV) minV = avg;
        if (avg > maxV) maxV = avg;
      }
    }
    const range = maxV - minV || 1;
    return values.map(v => {
      const norm = (v - minV) / range;
      const hue = 200 - norm * 130;
      return { v, c: `hsl(${hue},55%,${18 + norm * 28}%)` };
    });
  }, [data, maxDays, ppd, tpH]);

  return (
    <div className="heatmap-scroll" style={{ marginTop: "8px" }}>
      <div className="heatmap-grid" style={{ gridTemplateColumns: `repeat(${maxDays},1fr)` }}>
        {cells.map((c, i) => (
          <div key={i} className="heatmap-cell" style={{ backgroundColor: c.c }} title={`电价 / Price ¥${c.v.toFixed(1)}`} />
        ))}
      </div>
    </div>
  );
}

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

function CopilotPanel() {
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
    <>
      <div className={"copilot-backdrop" + (open ? " open" : "")} onClick={() => setOpen(false)} />
      <aside className={"copilot-panel" + (open ? " open" : "")}>
        <div className="copilot-header">Copilot 助手 / Copilot</div>
      {configError && <div className="copilot-config-error">⚠️ {configError}</div>}
      <div className="copilot-messages" ref={msgsContainerRef}>
        {messages.map((msg, i) => {
          switch (msg.role) {
            case "user":
              return <div key={i} className="message message-user">{msg.content}</div>;
            case "assistant":
              return <div key={i} className="message message-assistant">{msg.content}</div>;
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
            {streamingText}<span className="streaming-cursor" />
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
  const [degraded, setDegraded] = useState(false);

  const [currentTick, setCurrentTick] = useState(0);
  const [playing, setPlaying] = useState(true);
  const [speed, setSpeed] = useState<1 | 4 | 16>(4);

  useEffect(() => {
    const ac = new AbortController();
    fetchRollingDemo(ac.signal)
      .then((d) => {
        setData(d);
        setLoading(false);
        if (d.warnings.length > 0) setDegraded(true);
      })
      .catch((e) => {
        if (e.name !== "AbortError") {
          setError(e.message);
          setLoading(false);
        }
      });
    return () => ac.abort();
  }, []);

  const totalPoints = data?.series.timestamps.length ?? 0;

  useEffect(() => {
    if (!playing || totalPoints === 0) return;
    const id = setInterval(() => {
      setCurrentTick((prev) => {
        const next = prev + speed;
        return next >= totalPoints ? 0 : next;
      });
    }, 1000);
    return () => clearInterval(id);
  }, [playing, speed, totalPoints]);

  const progressPct = totalPoints > 0 ? (currentTick / totalPoints) * 100 : 0;
  const currentTs = data?.series.timestamps[currentTick] ?? "";
  const fmt = (v: number | null | undefined) => v != null ? v.toFixed(1) : "—";

  if (loading) return <div className="app"><p className="loading">加载数据剧场... / Loading data theater...</p></div>;
  if (error) return <div className="app"><p className="error">数据不可用 / Data unavailable: {error}</p></div>;

  const s = {
    tl: { border: "1px solid rgba(45,212,191,0.22)", background: "rgba(2,6,23,0.4)", borderRadius: "16px", padding: "14px", minHeight: "215px", position: "relative" as const },
    ms: { display: "grid", gap: "10px" },
    mc: { background: "rgba(15,23,42,0.7)", border: "1px solid rgba(148,163,184,0.18)", borderRadius: "14px", padding: "12px" },
    mv: { display: "block", fontSize: "20px", marginTop: "4px" },
    ml: { color: "#8aa4c2", fontSize: "12px" },
    pn: { border: "1px solid rgba(148,163,184,0.2)", background: "linear-gradient(145deg,rgba(15,23,42,0.92),rgba(13,26,46,0.9))", borderRadius: "20px", overflow: "hidden" },
    ph: { display: "flex", justifyContent: "space-between", gap: "14px", alignItems: "center", padding: "16px 18px", borderBottom: "1px solid rgba(148,163,184,0.16)" },
    pb: { padding: "16px 18px 18px" },
    mono: { fontFamily: "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace", color: "#bfdbfe", whiteSpace: "pre-wrap" as const, fontSize: "12px", lineHeight: "1.45" },

  };

  return (
    <div className="app">
      <header className="app-header">
        <div>
          <h1>山东 15min 数据剧场 / Shandong 15min Data Theater</h1>
          <p style={{ color: "#8aa4c2", fontSize: "13px", marginTop: "4px" }}>
            {data?.meta.start} → {data?.meta.end} · {data?.meta.rows.toLocaleString()} 点 / points · 只读滚动演示端点 / rolling demo readonly endpoint
          </p>
        </div>
        <span className="badge badge-shandong" style={{ marginTop: 0 }}>学习原型 / Learning prototype · 非真实交易 / no real trading</span>
      </header>

      <div className="app-layout">
        <main className="dashboard-main">
          <section className="section" style={{ marginTop: 0, border: "1px solid rgba(148,163,184,0.2)", background: "linear-gradient(145deg,rgba(15,23,42,0.92),rgba(13,26,46,0.9))", borderRadius: "20px", overflow: "hidden" }}>
            <div style={{ display: "flex", justifyContent: "space-between", gap: "14px", alignItems: "center", padding: "16px 18px", borderBottom: "1px solid rgba(148,163,184,0.16)" }}>
              <div>
                <h2 style={{ margin: 0, fontSize: "1.125rem", fontWeight: 600 }}>滚动回放舞台 / Rolling Playback Stage</h2>
                <p style={{ color: "#8aa4c2", fontSize: "13px", marginTop: "4px" }}>播放指针驱动全部面板：负荷、电价、风光、策略、证据 / Playhead drives every panel: load, price, renewable, strategy, evidence</p>
              </div>
              <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                <button
                  onClick={() => setPlaying((p) => !p)}
                  style={{ border: `1px solid rgba(148,163,184,${playing ? "0.55" : "0.26"})`, background: playing ? "rgba(45,212,191,0.15)" : "rgba(15,23,42,0.92)", color: "#e5f1ff", borderRadius: "12px", padding: "8px 10px", cursor: "pointer" }}
                >
                  {playing ? "暂停 / Pause" : "播放 / Play"}
                </button>
                {([1, 4, 16] as const).map((sp) => (
                  <button key={sp}
                    onClick={() => setSpeed(sp)}
                    style={{ border: `1px solid rgba(148,163,184,${speed === sp ? "0.55" : "0.26"})`, background: speed === sp ? "rgba(45,212,191,0.15)" : "rgba(15,23,42,0.92)", color: speed === sp ? "#99f6e4" : "#e5f1ff", borderRadius: "12px", padding: "8px 10px", cursor: "pointer" }}
                  >{sp}x</button>
                ))}
              </div>
            </div>
            <div className="stage-grid">
              <div style={s.tl}>
                <div style={{ position: "absolute", top: "14px", bottom: "14px", width: "2px", background: "#2dd4bf", boxShadow: "0 0 18px #2dd4bf", left: `${progressPct}%`, transition: "left 0.3s ease" }} />
                <LoadChartSVG series={data!.series} tick={currentTick} />
                <div style={{display:"flex",gap:"14px",fontSize:"11px",color:"#94a3b8",marginTop:"6px",flexWrap:"wrap",padding:"0 2px"}}>
                  <span><span style={{display:"inline-block",width:"16px",height:"2.5px",background:"#2dd4bf",verticalAlign:"middle",marginRight:"5px",borderRadius:"1px"}} /> 实际负荷 / actual</span>
                  <span><span style={{display:"inline-block",width:"16px",borderTop:"1.5px dashed #f59e0b",verticalAlign:"middle",marginRight:"5px"}} /> 预测负荷 / forecast</span>
                  <span><span style={{display:"inline-block",width:"2px",height:"12px",background:"#2dd4bf",verticalAlign:"middle",marginRight:"5px",borderRadius:"1px"}} /> 播放指针 / playhead</span>
                </div>
                <div style={s.mono}>
                  {`当前点 / current_tick = ${String(currentTick).padStart(4, "0")} / ${totalPoints}\n时间戳 / timestamp    = ${currentTs}\n粒度 / granularity    = ${data?.meta.frequency}\n来源 / source         = ${data?.meta.source}`}
                </div>
              </div>
              <div style={s.ms}>
                <div style={s.mc}><span style={s.ml}>已加载点数 / Loaded points</span><strong style={s.mv}>{data?.meta.rows.toLocaleString()}</strong></div>
                <div style={s.mc}><span style={s.ml}>窗口 / Window</span><strong style={s.mv}>{Math.round((data?.meta.rows ?? 0) / (data?.meta.points_per_day ?? 96))} 天 / days</strong></div>
                <div style={s.mc}><span style={s.ml}>降级状态 / Fallback state</span><strong style={{ ...s.mv, color: degraded ? "#fb7185" : "#34d399" }}>{degraded ? "降级 / degraded" : "安全 / safe"}</strong></div>
              </div>
            </div>
          </section>

          <section className="section panel-grid" style={{ marginTop: "18px" }}>
            <article style={s.pn}>
              <div style={s.ph}><h3 style={{ margin: 0, fontSize: "14px" }}>负荷预测 / Load Forecast</h3><span className="badge badge-shandong" style={{ margin: 0 }}>折线 / line</span></div>
              <div style={s.pb}><div style={s.mono}>实际负荷 / actual load ━━━━━{'\n'}预测 / forecast      - - - -{'\n'}当前 / current: {fmt(data?.series.load_actual[currentTick])} MW · 预测 / forecast {fmt(data?.series.load_forecast[currentTick])} MW</div></div>
            </article>
            <article style={s.pn}>
              <div style={s.ph}><h3 style={{ margin: 0, fontSize: "14px" }}>电价热力图 / Price Heatmap</h3><span className="badge badge-shandong" style={{ margin: 0 }}>30×96</span></div>
                <div style={s.pb}>
                  <div className="mono-text">日前 / DA {fmt(data!.series.price_da[currentTick])} ¥ · 实时 / RT {fmt(data!.series.price_rt[currentTick])} ¥</div>
                  <PriceHeatmapGrid data={data!} />
                </div>
            </article>
            <article style={s.pn}>
              <div style={s.ph}><h3 style={{ margin: 0, fontSize: "14px" }}>风电 + 光伏 / Wind + Solar</h3><span className="badge badge-shandong" style={{ margin: 0 }}>面积 / area</span></div>
                <div style={s.pb}>
                  <RenewableChartSVG series={data!.series} />
                  <div style={{display:"flex",gap:"14px",fontSize:"11px",color:"#94a3b8",marginTop:"6px"}}>
                    <span><span style={{display:"inline-block",width:"16px",height:"12px",background:"rgba(45,212,191,0.34)",verticalAlign:"middle",marginRight:"5px",borderRadius:"2px"}} /> 风电 / wind</span>
                    <span><span style={{display:"inline-block",width:"16px",height:"12px",background:"rgba(245,158,11,0.34)",verticalAlign:"middle",marginRight:"5px",borderRadius:"2px"}} /> 光伏 / solar</span>
                  </div>
                </div>
            </article>
            <StrategyComparison strategy={data!.strategy} />
            <article style={{ ...s.pn, gridColumn: "1 / -1" }}>
              <div style={s.ph}><h3 style={{ margin: 0, fontSize: "14px" }}>证据报告 / Evidence</h3><span className="badge badge-shandong" style={{ margin: 0 }}>报告 / reports</span></div>
                <div style={{ padding: "12px 18px 18px" }}>
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
          </section>
        </main>
        <CopilotPanel />
      </div>
    </div>
  );
}
