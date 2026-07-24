import { useEffect, useMemo, useState } from "react";
import type {
  PositionState,
  RollingDemoResponse,
  StrategyKey,
  StrategyPointSeries,
} from "./types";

type ReplayMode = "day" | "hour" | "point";

const POINTS_PER_DAY = 96;
const POINTS_PER_HOUR = 4;
const strategyOrder: StrategyKey[] = ["td3", "ppo", "sac", "trend"];
const strategyLabels: Record<StrategyKey, string> = {
  td3: "TD3",
  ppo: "PPO",
  sac: "SAC",
  trend: "趋势 / Trend",
};
const modeLabels: Record<ReplayMode, string> = {
  day: "逐日 / Daily",
  hour: "逐小时 / Hourly",
  point: "逐点 / 15-minute",
};

function finite(values: (number | null | undefined)[]): number[] {
  return values.filter((value): value is number => value != null && Number.isFinite(value));
}

function average(values: (number | null | undefined)[]): number | null {
  const valid = finite(values);
  return valid.length ? valid.reduce((sum, value) => sum + value, 0) / valid.length : null;
}

function valueRange(values: (number | null | undefined)[]): { min: number | null; max: number | null } {
  const valid = finite(values);
  return valid.length ? { min: Math.min(...valid), max: Math.max(...valid) } : { min: null, max: null };
}

function formatNumber(value: number | null | undefined, digits = 1): string {
  return value == null ? "—" : value.toLocaleString("zh-CN", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

function formatContribution(value: number): string {
  const sign = value > 0 ? "+" : value < 0 ? "−" : "";
  const absolute = Math.abs(value);
  return absolute >= 10_000
    ? `${sign}${(absolute / 10_000).toFixed(2)} 万模拟单位`
    : `${sign}${Math.round(absolute).toLocaleString("zh-CN")} 模拟单位`;
}

function dateLabel(timestamp: string): string {
  const [, month, day] = timestamp.slice(0, 10).split("-");
  return `${Number(month)} 月 ${Number(day)} 日`;
}

function periodLabel(timestamp: string, mode: ReplayMode): string {
  const date = dateLabel(timestamp);
  const time = timestamp.slice(11, 16);
  if (mode === "day") return `${date}当日`;
  if (mode === "hour") return `${date} ${time.slice(0, 2)}:00–${time.slice(0, 2)}:45`;
  return `${date} ${time}`;
}

function summaryRange(mode: ReplayMode, tick: number, total: number): [number, number] {
  const size = mode === "day" ? POINTS_PER_DAY : mode === "hour" ? POINTS_PER_HOUR : 1;
  const start = Math.floor(tick / size) * size;
  return [start, Math.min(start + size, total)];
}

function chartRange(mode: ReplayMode, tick: number, total: number): [number, number] {
  if (mode !== "point") return summaryRange(mode, tick, total);
  return [Math.max(0, tick - POINTS_PER_HOUR), Math.min(total, tick + POINTS_PER_HOUR + 1)];
}

function linePath(values: (number | null)[], width: number, height: number, min: number, max: number): string {
  const range = max - min || 1;
  let drawing = false;
  return values.map((value, index) => {
    if (value == null) {
      drawing = false;
      return "";
    }
    const x = values.length > 1 ? (index / (values.length - 1)) * width : width / 2;
    const y = height - 6 - ((value - min) / range) * (height - 12);
    const command = drawing ? "L" : "M";
    drawing = true;
    return `${command}${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");
}

interface ChartSeries {
  label: string;
  values: (number | null)[];
  color: string;
  dashed?: boolean;
  pointsOnly?: boolean;
}

function DetailChart({ title, unit, series }: { title: string; unit: string; series: ChartSeries[] }) {
  const width = 520;
  const height = 150;
  const allValues = finite(series.flatMap((item) => item.values));
  const min = allValues.length ? Math.min(...allValues) : 0;
  const max = allValues.length ? Math.max(...allValues) : 1;

  return (
    <figure className="replay-detail-chart">
      <figcaption>{title}<small>{unit}</small></figcaption>
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={title}>
        {series.map((item) => item.pointsOnly ? (
          <g key={item.label} aria-label={item.label}>
            {item.values.map((value, index) => {
              if (value == null) return null;
              const x = item.values.length > 1 ? (index / (item.values.length - 1)) * width : width / 2;
              const y = height - 6 - ((value - min) / (max - min || 1)) * (height - 12);
              return <circle key={index} cx={x} cy={y} r="3" fill={item.color} />;
            })}
          </g>
        ) : (
          <path
            key={item.label}
            d={linePath(item.values, width, height, min, max)}
            fill="none"
            stroke={item.color}
            strokeWidth="2.2"
            strokeDasharray={item.dashed ? "7 5" : undefined}
          />
        ))}
      </svg>
      <div className="replay-chart-legend">
        {series.map((item) => <span key={item.label}><i style={{ background: item.color }} />{item.label}</span>)}
      </div>
    </figure>
  );
}

function PriceMonthMatrix({ data, tick, mode }: { data: RollingDemoResponse; tick: number; mode: ReplayMode }) {
  const selectedDay = Math.floor(tick / POINTS_PER_DAY);
  const selectedHour = Math.floor((tick % POINTS_PER_DAY) / POINTS_PER_HOUR);
  const cells = useMemo(() => {
    const values: number[] = [];
    for (let day = 0; day < 30; day += 1) {
      for (let hour = 0; hour < 24; hour += 1) {
        const start = day * POINTS_PER_DAY + hour * POINTS_PER_HOUR;
        values.push(average(data.series.price_rt.slice(start, start + POINTS_PER_HOUR)) ?? 0);
      }
    }
    const min = Math.min(...values);
    const max = Math.max(...values);
    return values.map((value) => {
      const normalized = (value - min) / (max - min || 1);
      const hue = 215 - normalized * 170;
      return { value, color: `hsl(${hue},62%,${18 + normalized * 30}%)` };
    });
  }, [data.series.price_rt]);

  return (
    <div className="price-matrix-scroll" role="region" tabIndex={0} aria-label="30 天乘 24 小时实时价格均价矩阵">
      <div className="price-month-matrix" role="grid" aria-label="实时价格月度定位图">
        <span className="price-matrix-corner">日\时</span>
        {Array.from({ length: 24 }, (_, hour) => <span key={hour} className="price-matrix-hour">{hour}</span>)}
        {Array.from({ length: 30 }, (_, day) => (
          <div key={day} className="price-matrix-row" role="row">
            <span className="price-matrix-day">10/{String(day + 1).padStart(2, "0")}</span>
            {Array.from({ length: 24 }, (_, hour) => {
              const cell = cells[day * 24 + hour];
              const selected = day === selectedDay && (mode === "day" || hour === selectedHour);
              const current = day === selectedDay && hour === selectedHour;
              return (
                <span
                  key={hour}
                  role="gridcell"
                  className={`price-matrix-cell${selected ? " selected" : ""}${current ? " current" : ""}`}
                  style={{ backgroundColor: cell.color }}
                  title={`10 月 ${day + 1} 日 ${hour}:00，实时价小时均值 ${cell.value.toFixed(1)} 元/MWh`}
                  aria-label={`10 月 ${day + 1} 日 ${hour} 时，${cell.value.toFixed(1)} 元每兆瓦时`}
                />
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
}

interface StrategyPeriodSummary {
  contribution: number;
  long: number;
  short: number;
  flat: number;
  indeterminate: number;
  meanAbsolutePosition: number | null;
  pointPosition: number | null;
  pointState: PositionState;
}

function aggregateStrategy(series: StrategyPointSeries, start: number, end: number): StrategyPeriodSummary {
  const contributions = series.simulated_spread_value.slice(start, end);
  const states = series.position_state.slice(start, end);
  const positions = series.reconstructed_position.slice(start, end);
  const determinate = finite(positions);
  return {
    contribution: contributions.reduce((sum, value) => sum + value, 0),
    long: states.filter((state) => state === "long").length,
    short: states.filter((state) => state === "short").length,
    flat: states.filter((state) => state === "approximately_flat").length,
    indeterminate: states.filter((state) => state === "indeterminate").length,
    meanAbsolutePosition: determinate.length
      ? determinate.reduce((sum, value) => sum + Math.abs(value), 0) / determinate.length
      : null,
    pointPosition: positions[0] ?? null,
    pointState: states[0] ?? "indeterminate",
  };
}

function contributionClass(value: number): string {
  if (value > 0.005) return "正贡献";
  if (value < -0.005) return "负贡献";
  return "无贡献";
}

function periodContributionClass(summary: StrategyPeriodSummary, mode: ReplayMode): string {
  if (mode === "point" && (
    summary.pointState === "approximately_flat" || summary.pointState === "indeterminate"
  )) return "无贡献";
  return contributionClass(summary.contribution);
}

function pointPositionLabel(position: number | null, state: PositionState): string {
  if (state === "indeterminate" || position == null) return "不可判定";
  if (state === "approximately_flat") return "近似空仓";
  return `${position > 0 ? "做多" : "做空"} ${Math.round(Math.abs(position) * 100)}%`;
}

function distributionLabel(summary: StrategyPeriodSummary, periods: number, mode: ReplayMode): string {
  if (mode === "hour") {
    return `做多 ${summary.long} / 做空 ${summary.short} / 近空 ${summary.flat}${summary.indeterminate ? ` / 不可判 ${summary.indeterminate}` : ""}`;
  }
  const percentage = (value: number) => `${((value / periods) * 100).toFixed(0)}%`;
  return `做多 ${percentage(summary.long)} / 做空 ${percentage(summary.short)} / 近空 ${percentage(summary.flat)}${summary.indeterminate ? ` / 不可判 ${percentage(summary.indeterminate)}` : ""}`;
}

function deterministicSummary(
  label: string,
  mode: ReplayMode,
  spread: number | null,
  summaries: Record<StrategyKey, StrategyPeriodSummary>,
): string {
  const priceKind = mode === "point" ? "实时结算价" : "实时结算价均值";
  const relation = spread == null || Math.abs(spread) < 0.01 ? "接近" : spread > 0 ? "高于" : "低于";
  const positive = strategyOrder.filter((key) => periodContributionClass(summaries[key], mode) === "正贡献").map((key) => strategyLabels[key]);
  const negative = strategyOrder.filter((key) => periodContributionClass(summaries[key], mode) === "负贡献").map((key) => strategyLabels[key]);
  const neutral = strategyOrder.filter((key) => periodContributionClass(summaries[key], mode) === "无贡献").map((key) => strategyLabels[key]);
  const parts = [`${label}：${priceKind}${relation}当日回测基准价${spread == null ? "" : `，价差 ${spread >= 0 ? "+" : ""}${spread.toFixed(1)} 元/MWh`}`];
  if (positive.length) parts.push(`${positive.join("、")}为正贡献`);
  if (negative.length) parts.push(`${negative.join("、")}为负贡献`);
  if (neutral.length) parts.push(`${neutral.join("、")}无显著贡献`);
  return `${parts.join("；")}。`;
}

export function ReplayStage({ data }: { data: RollingDemoResponse }) {
  const total = data.series.timestamps.length;
  const strategy = data.strategy.status === "ok" ? data.strategy : null;
  const [mode, setMode] = useState<ReplayMode>("day");
  const [tick, setTick] = useState(0);
  const [playing, setPlaying] = useState(
    () => !window.matchMedia("(prefers-reduced-motion: reduce)").matches,
  );

  useEffect(() => {
    const pauseWhenHidden = () => {
      if (document.hidden) setPlaying(false);
    };
    document.addEventListener("visibilitychange", pauseWhenHidden);
    return () => document.removeEventListener("visibilitychange", pauseWhenHidden);
  }, []);

  useEffect(() => {
    if (!playing || total === 0) return;
    const step = mode === "day" ? POINTS_PER_DAY : mode === "hour" ? POINTS_PER_HOUR : 1;
    const atMonthEnd = mode === "day" && tick >= total - POINTS_PER_DAY;
    const timer = window.setTimeout(() => {
      setTick((current) => current + step >= total ? 0 : current + step);
    }, atMonthEnd ? 2000 : 1000);
    return () => window.clearTimeout(timer);
  }, [mode, playing, tick, total]);

  const selectMode = (nextMode: ReplayMode) => {
    const size = nextMode === "day" ? POINTS_PER_DAY : nextMode === "hour" ? POINTS_PER_HOUR : 1;
    if (nextMode === "point") setPlaying(false);
    setMode(nextMode);
    setTick((current) => Math.floor(current / size) * size);
  };

  const selectExactPoint = (nextTick: number) => {
    setPlaying(false);
    setMode("point");
    setTick(Math.max(0, Math.min(total - 1, nextTick)));
  };

  const [start, end] = summaryRange(mode, tick, total);
  const [chartStart, chartEnd] = chartRange(mode, tick, total);
  const timestamp = data.series.timestamps[tick];
  const label = periodLabel(timestamp, mode);
  const currentDay = Math.floor(tick / POINTS_PER_DAY);
  const initializationPeriod = strategy?.daily.baseline_initialization[currentDay] ?? currentDay < 7;
  const rtValues = data.series.price_rt.slice(start, end);
  const loadValues = data.series.load_actual.slice(start, end);
  const windValues = data.series.wind_actual.slice(start, end);
  const solarValues = data.series.solar_actual.slice(start, end);
  const priceStats = valueRange(rtValues);
  const rtMean = average(rtValues);
  const loadStats = valueRange(loadValues);
  const baseline = strategy ? strategy.timeseries.daily_baseline_price[tick] : null;
  const settlementReference = mode === "point" ? data.series.price_rt[tick] : rtMean;
  const spread = settlementReference != null && baseline != null ? settlementReference - baseline : null;
  const hourlyStart = Math.floor(tick / POINTS_PER_HOUR) * POINTS_PER_HOUR;
  const dayAhead = data.series.price_da[hourlyStart];
  const dayAheadChartValues = data.series.price_da
    .slice(chartStart, chartEnd)
    .map((value, offset) => (chartStart + offset) % POINTS_PER_HOUR === 0 ? value : null);
  const periodLength = end - start;
  const strategySummaries = strategy
    ? Object.fromEntries(strategyOrder.map((key) => [
      key,
      aggregateStrategy(strategy.timeseries.strategies[key], start, end),
    ])) as Record<StrategyKey, StrategyPeriodSummary>
    : null;

  const marketCards = mode === "day" ? [
    ["实时价范围 / RT range", `${formatNumber(priceStats.min)}–${formatNumber(priceStats.max)} 元/MWh`],
    ["实时价均值 / RT mean", `${formatNumber(rtMean)} 元/MWh`],
    ["实际负荷峰值 / Load peak", `${formatNumber(loadStats.max)} MW`],
    ["风电 / 光伏均值", `${formatNumber(average(windValues))} / ${formatNumber(average(solarValues))} MW`],
  ] : mode === "hour" ? [
    ["小时实时价范围", `${formatNumber(priceStats.min)}–${formatNumber(priceStats.max)} 元/MWh`],
    ["小时实时价均值", `${formatNumber(rtMean)} 元/MWh`],
    ["小时平均实际负荷", `${formatNumber(average(loadValues))} MW`],
    ["小时风电 / 光伏均值", `${formatNumber(average(windValues))} / ${formatNumber(average(solarValues))} MW`],
  ] : [
    ["历史实时结算价", `${formatNumber(data.series.price_rt[tick])} 元/MWh`],
    ["本小时日前价（对照）", dayAhead == null ? "原始点缺失" : `${formatNumber(dayAhead)} 元/MWh`],
    ["实际 / 历史发布预测负荷", `${formatNumber(data.series.load_actual[tick])} / ${formatNumber(data.series.load_forecast[tick])} MW`],
    ["风电 / 光伏", `${formatNumber(data.series.wind_actual[tick])} / ${formatNumber(data.series.solar_actual[tick])} MW`],
  ];

  return (
    <section className="replay-stage" aria-labelledby="replay-stage-title">
      <header className="replay-stage-header">
        <div>
          <p className="replay-kicker">SYNCHRONIZED HISTORICAL REPLAY</p>
          <h2 id="replay-stage-title">滚动回放舞台 / Rolling Playback Stage</h2>
          <p>市场与策略始终使用同一选区 · 山东市场时间（北京时间，UTC+8）</p>
        </div>
        <div className="replay-controls" role="group" aria-label="回放控制">
          <button type="button" onClick={() => setPlaying((value) => !value)} aria-pressed={playing}>
            {playing ? "暂停 / Pause" : "播放 / Play"}
          </button>
          {(["day", "hour", "point"] as ReplayMode[]).map((item) => (
            <button key={item} type="button" onClick={() => selectMode(item)} aria-pressed={mode === item}>
              {modeLabels[item]}
            </button>
          ))}
        </div>
      </header>

      <div className="replay-timeline">
        <button type="button" onClick={() => selectExactPoint(tick - 1)} disabled={tick === 0} aria-label="前一个 15 分钟点">−15 分钟</button>
        <label>
          <span>{label} · {modeLabels[mode]}</span>
          <input
            type="range"
            min="0"
            max={total - 1}
            step="1"
            value={tick}
            onChange={(event) => selectExactPoint(Number(event.target.value))}
            aria-label="选择 2025 年 10 月任意 15 分钟点"
          />
          <small><span>10 月 1 日 00:00</span><span>10 月 30 日 23:45</span></small>
        </label>
        <button type="button" onClick={() => selectExactPoint(tick + 1)} disabled={tick === total - 1} aria-label="后一个 15 分钟点">+15 分钟</button>
      </div>

      <div className="replay-period-heading">
        <div>
          <span>当前选区 / Selected period</span>
          <strong>{label}</strong>
        </div>
        {initializationPeriod ? <span className="initialization-badge">基准初始化期 / Baseline initialization</span> : null}
      </div>

      <div className="replay-basis-strip">
        <div><span>{mode === "point" ? "实时结算价" : "选区实时价均值"}</span><strong>{formatNumber(settlementReference)} 元/MWh</strong></div>
        <div><span>当日回测基准价</span><strong>{formatNumber(baseline)} 元/MWh</strong></div>
        <div><span>价差 / Spread</span><strong className={spread != null && spread < 0 ? "negative" : "positive"}>{spread == null ? "—" : `${spread >= 0 ? "+" : ""}${spread.toFixed(1)} 元/MWh`}</strong></div>
        <div><span>日前价口径</span><strong>小时级 · 仅对照</strong></div>
      </div>

      {strategySummaries ? (
        <p className="replay-narrative" role="status">{deterministicSummary(label, mode, spread, strategySummaries)}</p>
      ) : (
        <p className="replay-narrative replay-narrative-degraded">策略快照不可用，当前仅同步展示历史市场状态。</p>
      )}

      <div className="replay-summary-grid">
        <article>
          <h3>{label}市场状态 / Market state</h3>
          <dl className="market-summary-list">
            {marketCards.map(([name, value]) => <div key={name}><dt>{name}</dt><dd>{value}</dd></div>)}
          </dl>
        </article>
        <article>
          <h3>{label}四策略贡献 / Strategy contribution</h3>
          {strategySummaries ? (
            <div className="period-strategy-table" role="table" aria-label={`${label}四策略贡献`}>
              {strategyOrder.map((key) => {
                const summary = strategySummaries[key];
                const classification = periodContributionClass(summary, mode);
                return (
                  <div key={key} role="row" data-contribution={classification}>
                    <strong role="rowheader">{strategyLabels[key]}</strong>
                    <span role="cell">{formatContribution(summary.contribution)}</span>
                    <span role="cell">{classification}</span>
                    <small role="cell">
                      {mode === "point"
                        ? `还原持仓：${pointPositionLabel(summary.pointPosition, summary.pointState)}`
                        : `${distributionLabel(summary, periodLength, mode)} · 平均绝对持仓 ${formatNumber(summary.meanAbsolutePosition == null ? null : summary.meanAbsolutePosition * 100, 0)}%`}
                    </small>
                  </div>
                );
              })}
            </div>
          ) : <p className="replay-empty">策略证据整体降级，不显示部分指标。</p>}
        </article>
      </div>

      <div className="replay-detail-grid">
        <DetailChart
          title="实际负荷 vs 历史发布负荷预测"
          unit="MW · Historical Published Load Forecast"
          series={[
            { label: "实际负荷", values: data.series.load_actual.slice(chartStart, chartEnd), color: "#2dd4bf" },
            { label: "历史发布负荷预测", values: data.series.load_forecast.slice(chartStart, chartEnd), color: "#f59e0b", dashed: true },
          ]}
        />
        <DetailChart
          title="实时结算价 vs 小时级日前价"
          unit="元/MWh · 日前价仅作对照"
          series={[
            { label: "实时价（15 分钟）", values: data.series.price_rt.slice(chartStart, chartEnd), color: "#60a5fa" },
            { label: "日前价（原始小时点）", values: dayAheadChartValues, color: "#fbbf24", pointsOnly: true },
          ]}
        />
        <DetailChart
          title="风电 + 光伏历史出力"
          unit="MW"
          series={[
            { label: "风电", values: data.series.wind_actual.slice(chartStart, chartEnd), color: "#2dd4bf" },
            { label: "光伏", values: data.series.solar_actual.slice(chartStart, chartEnd), color: "#fb923c" },
          ]}
        />
      </div>

      <article className="price-month-overview">
        <header><h3>30 天 × 24 小时实时价格均价 / Monthly RT Price Overview</h3><span>当前日期与小时高亮</span></header>
        <PriceMonthMatrix data={data} tick={tick} mode={mode} />
      </article>
    </section>
  );
}
