import type { RollingDemoStrategyOk, StrategyKey } from "./types";
import { formatSimulatedValue, simulatedValueParts, strategyOrder, strategyPresentation } from "./strategyPresentation";

const HEAT_LIMIT = 300_000;
const CHART_WIDTH = 920;
const CHART_HEIGHT = 260;
const CHART_PADDING = { top: 18, right: 18, bottom: 34, left: 74 };

function chartPath(values: number[], selectedEnd: number, min: number, max: number): string {
  const width = CHART_WIDTH - CHART_PADDING.left - CHART_PADDING.right;
  const height = CHART_HEIGHT - CHART_PADDING.top - CHART_PADDING.bottom;
  const range = max - min || 1;
  return values.slice(0, selectedEnd + 1).map((value, index) => {
    const x = CHART_PADDING.left + (index / (values.length - 1)) * width;
    const y = CHART_PADDING.top + height - ((value - min) / range) * height;
    return `${index === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");
}

function heatColor(value: number): string {
  const normalized = Math.max(-1, Math.min(1, value / HEAT_LIMIT));
  if (normalized > 0) return `hsl(153, ${38 + normalized * 30}%, ${15 + normalized * 25}%)`;
  if (normalized < 0) return `hsl(354, ${38 + Math.abs(normalized) * 30}%, ${15 + Math.abs(normalized) * 25}%)`;
  return "hsl(215, 18%, 24%)";
}

function signMarker(value: number): string {
  if (value > 0.005) return "+";
  if (value < -0.005) return "−";
  return "0";
}

function chartBounds(strategy: RollingDemoStrategyOk): { min: number; max: number } {
  const values = strategyOrder.flatMap((key) => (
    strategy.timeseries.strategies[key].cumulative_simulated_spread_value
  ));
  return { min: Math.min(0, ...values), max: Math.max(0, ...values) };
}

function CumulativePath({ strategy, selectedTick }: {
  strategy: RollingDemoStrategyOk;
  selectedTick: number;
}) {
  const { min, max } = chartBounds(strategy);
  const boundedTick = Math.min(selectedTick, strategy.window.points - 1);
  const plotWidth = CHART_WIDTH - CHART_PADDING.left - CHART_PADDING.right;
  const plotHeight = CHART_HEIGHT - CHART_PADDING.top - CHART_PADDING.bottom;
  const zeroY = CHART_PADDING.top + plotHeight - ((0 - min) / (max - min || 1)) * plotHeight;
  const markerX = CHART_PADDING.left + (boundedTick / (strategy.window.points - 1)) * plotWidth;
  const yLabels = [max, (max + min) / 2, min];

  return (
    <article className="strategy-path-card">
      <header>
        <div>
          <p className="strategy-path-kicker">CUMULATIVE PATH</p>
          <h3>30 天累计模拟价差路径 / Cumulative Simulated Spread Value</h3>
        </div>
        <span>固定纵轴 · 完整路径常驻</span>
      </header>
      <div className="strategy-path-svg-scroll">
        <svg
          viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`}
          className="strategy-path-svg"
          role="img"
          aria-labelledby="strategy-path-title strategy-path-description"
        >
          <title id="strategy-path-title">四种可执行策略的30天累计模拟价差路径</title>
          <desc id="strategy-path-description">完整路径低对比显示，已播放区间高亮；灰色虚线为趋势基线，水平虚线为零参考。</desc>
          {yLabels.map((value, index) => {
            const y = CHART_PADDING.top + (index / (yLabels.length - 1)) * plotHeight;
            return (
              <g key={index}>
                <line x1={CHART_PADDING.left} y1={y} x2={CHART_WIDTH - CHART_PADDING.right} y2={y} className="strategy-path-gridline" />
                <text x={CHART_PADDING.left - 9} y={y + 3} textAnchor="end" className="strategy-path-axis-label">{simulatedValueParts(value, false).number}</text>
              </g>
            );
          })}
          <line x1={CHART_PADDING.left} y1={zeroY} x2={CHART_WIDTH - CHART_PADDING.right} y2={zeroY} className="strategy-zero-line" />
          {strategyOrder.map((key) => {
            const values = strategy.timeseries.strategies[key].cumulative_simulated_spread_value;
            const presentation = strategyPresentation[key];
            return (
              <g key={key}>
                <path
                  d={chartPath(values, values.length - 1, min, max)}
                  className="strategy-path-unplayed"
                  stroke={presentation.color}
                  strokeDasharray={presentation.dashed ? "8 6" : undefined}
                />
                <path
                  d={chartPath(values, boundedTick, min, max)}
                  className="strategy-path-played"
                  stroke={presentation.color}
                  strokeDasharray={presentation.dashed ? "8 6" : undefined}
                />
              </g>
            );
          })}
          <line x1={markerX} y1={CHART_PADDING.top} x2={markerX} y2={CHART_HEIGHT - CHART_PADDING.bottom} className="strategy-playhead-marker" />
          {strategyOrder.map((key) => {
            const value = strategy.timeseries.strategies[key].cumulative_simulated_spread_value[boundedTick];
            const y = CHART_PADDING.top + plotHeight - ((value - min) / (max - min || 1)) * plotHeight;
            return <circle key={key} cx={markerX} cy={y} r="4" fill={strategyPresentation[key].color} stroke="#07101d" strokeWidth="2" />;
          })}
          <text x={CHART_PADDING.left} y={CHART_HEIGHT - 10} className="strategy-path-axis-label">10/01</text>
          <text x={CHART_WIDTH - CHART_PADDING.right} y={CHART_HEIGHT - 10} textAnchor="end" className="strategy-path-axis-label">10/30</text>
          <text x="10" y="14" className="strategy-path-axis-unit">模拟单位</text>
        </svg>
      </div>
      <div className="strategy-path-legend" aria-label="策略线型图例">
        {strategyOrder.map((key) => (
          <span key={key}>
            <i style={{ borderColor: strategyPresentation[key].color }} className={strategyPresentation[key].dashed ? "dashed" : ""} />
            {strategyPresentation[key].label}
          </span>
        ))}
        <span><i className="zero" />零参考线 / Zero reference</span>
      </div>
    </article>
  );
}

function OracleReference({ strategy, selectedTick }: {
  strategy: RollingDemoStrategyOk;
  selectedTick: number;
}) {
  const boundedTick = Math.min(selectedTick, strategy.window.points - 1);
  const currentOracle = strategy.oracle.cumulative_simulated_spread_value[boundedTick];

  return (
    <aside className="oracle-reference" aria-label="Oracle 理论上界">
      <div>
        <p className="strategy-path-kicker">THEORETICAL UPPER BOUND</p>
        <h3>Oracle 理论价差上界</h3>
        <p>使用未来真实价格，只作不可执行上界；不进入可执行策略同轴曲线。</p>
      </div>
      <dl>
        <div><dt>当前累计上界</dt><dd>{formatSimulatedValue(currentOracle)}</dd></div>
        <div><dt>30 天最终上界</dt><dd>{formatSimulatedValue(strategy.oracle.terminal_simulated_spread_value)}</dd></div>
        {strategyOrder.map((key) => {
          const strategyValue = strategy.timeseries.strategies[key].cumulative_simulated_spread_value[boundedTick];
          const capture = currentOracle > 0 ? strategyValue / currentOracle : 0;
          return <div key={key}><dt>{strategyPresentation[key].label} 当前捕获率</dt><dd>{(capture * 100).toFixed(1)}%</dd></div>;
        })}
      </dl>
    </aside>
  );
}

function DailyContributionMatrix({ strategy, selectedDay, onSelectDay }: {
  strategy: RollingDemoStrategyOk;
  selectedDay: number;
  onSelectDay: (dayIndex: number) => void;
}) {
  return (
    <article className="daily-contribution-card">
      <header>
        <div>
          <p className="strategy-path-kicker">DAILY CONTRIBUTION NAVIGATION</p>
          <h3>策略 × 标准化回测日贡献矩阵</h3>
        </div>
        <span>共享色阶：−30 万 ↔ 0 ↔ +30 万模拟单位/日</span>
      </header>
      <div className="daily-matrix-scroll" role="region" tabIndex={0} aria-label="每日模拟价差贡献矩阵，可横向滚动">
        <div className="daily-contribution-matrix" role="grid" aria-label="四策略30天贡献导航">
          <span className="daily-matrix-corner" role="columnheader">策略\日期</span>
          {strategy.daily.dates.map((date, day) => (
            <span
              key={date}
              role="columnheader"
              className={`daily-matrix-date${selectedDay === day ? " selected" : ""}${strategy.daily.baseline_initialization[day] ? " initialization" : ""}`}
              title={strategy.daily.baseline_initialization[day] ? "基准初始化期" : undefined}
            >{date.slice(8)}</span>
          ))}
          {strategyOrder.map((key) => (
            <div key={key} className="daily-matrix-row" role="row">
              <span className="daily-matrix-strategy" role="rowheader">
                <i style={{ background: strategyPresentation[key].color }} />{strategyPresentation[key].label}
              </span>
              {strategy.daily.strategies[key].simulated_spread_value.map((value, day) => {
                const date = strategy.daily.dates[day];
                const exact = formatSimulatedValue(value);
                const initialization = strategy.daily.baseline_initialization[day];
                return (
                  <button
                    key={date}
                    type="button"
                    role="gridcell"
                    className={`daily-matrix-cell${selectedDay === day ? " selected" : ""}${initialization ? " initialization" : ""}`}
                    style={{ backgroundColor: heatColor(value) }}
                    onClick={() => onSelectDay(day)}
                    aria-label={`${strategyPresentation[key].label}，${date}，${exact}${initialization ? "，基准初始化期" : ""}`}
                    title={`${strategyPresentation[key].label} · ${date} · ${exact}${initialization ? " · 基准初始化期" : ""}`}
                  >{signMarker(value)}</button>
                );
              })}
            </div>
          ))}
        </div>
      </div>
      <footer className="daily-matrix-legend">
        <span><i className="loss" />≤ −30 万</span><span><i className="neutral" />0</span><span><i className="gain" />≥ +30 万</span>
        <span className="initialization-key">斜纹：10 月 1–7 日基准初始化期</span>
      </footer>
    </article>
  );
}

export function StrategyPathEvidence({ strategy, selectedTick, selectedDay, onSelectDay }: {
  strategy: RollingDemoStrategyOk;
  selectedTick: number;
  selectedDay: number;
  onSelectDay: (dayIndex: number) => void;
}) {
  return (
    <section className="strategy-path-evidence" aria-labelledby="strategy-path-evidence-title">
      <header className="strategy-path-evidence-heading">
        <div>
          <p className="strategy-path-kicker">PATH + DAILY EVIDENCE</p>
          <h2 id="strategy-path-evidence-title">模拟价差怎样形成 / How the Simulated Spread Value Developed</h2>
        </div>
        <span>与上方回放使用同一选区</span>
      </header>
      <CumulativePath strategy={strategy} selectedTick={selectedTick} />
      <OracleReference strategy={strategy} selectedTick={selectedTick} />
      <DailyContributionMatrix strategy={strategy} selectedDay={selectedDay} onSelectDay={onSelectDay} />
    </section>
  );
}
