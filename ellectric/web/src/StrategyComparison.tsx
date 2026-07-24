import type { RollingDemoStrategy, StrategySummaryRow } from "./types";
import { simulatedValueParts, strategyPresentation } from "./strategyPresentation";

const factLabels: Record<string, string> = {
  highest_30_day_value: "30 天累计值最高",
  most_profitable_days: "盈利日最多",
  highest_active_positive_rate: "持仓时段正贡献率最高",
  smallest_max_drawdown: "最大回撤最小",
  highest_profit_factor: "盈利因子最高",
  above_trend_baseline: "累计值高于趋势基线",
  simple_rule_reference: "简单规则参照",
};

function MetricValue({ value, signed = true }: { value: number; signed?: boolean }) {
  const formatted = simulatedValueParts(value, signed);
  return (
    <span className="strategy-number">
      {formatted.number}
      <small>{formatted.unit}</small>
    </span>
  );
}

function StrategyTable({ rows }: { rows: StrategySummaryRow[] }) {
  return (
    <div className="strategy-table-scroll" role="region" tabIndex={0} aria-label="策略比较表，可横向滚动">
      <table className="strategy-table">
        <caption>四种策略在同一 30 天历史窗口中的固定比较</caption>
        <thead>
          <tr>
            <th scope="col">策略</th>
            <th scope="col"><abbr title="30 天模拟价差值 / 30-day Simulated Spread Value">30 天模拟价差值</abbr></th>
            <th scope="col"><abbr title="当日模拟价差值为正的天数">盈利日</abbr></th>
            <th scope="col"><abbr title="持仓时段正贡献率 / Active-Period Positive Contribution Rate">持仓时段正贡献率</abbr></th>
            <th scope="col"><abbr title="最大回撤，按正的损失幅度显示">最大回撤</abbr></th>
            <th scope="col"><abbr title="盈利因子 / Profit Factor">盈利因子</abbr></th>
            <th scope="col"><abbr title="相对趋势基线倍数">趋势倍数</abbr></th>
            <th scope="col"><abbr title="Oracle 理论价差捕获率">Oracle 捕获率</abbr></th>
            <th scope="col">事实标签</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.strategy} data-strategy={row.strategy}>
              <th scope="row">
                <span className="strategy-identity-mark" aria-hidden="true" />
                {strategyPresentation[row.strategy].label}
              </th>
              <td><MetricValue value={row.simulated_spread_value} /></td>
              <td><strong>{row.profitable_days}</strong><span className="strategy-denominator"> / 30 天</span></td>
              <td>{(row.active_positive_contribution_rate * 100).toFixed(1)}%</td>
              <td><MetricValue value={row.max_drawdown} signed={false} /></td>
              <td>{row.profit_factor.toFixed(2)}</td>
              <td>{row.trend_multiple.toFixed(2)}×</td>
              <td>{(row.oracle_capture_rate * 100).toFixed(1)}%</td>
              <td>
                <span className="strategy-facts">
                  {row.facts.map((fact) => (
                    <span key={fact}>{factLabels[fact] ?? fact}</span>
                  ))}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function StrategyComparison({ strategy }: { strategy: RollingDemoStrategy }) {
  if (strategy.status !== "ok") {
    return (
      <section className="strategy-section strategy-section-degraded" aria-labelledby="strategy-title">
        <div className="strategy-heading">
          <div>
            <p className="strategy-kicker">MARKET-ONLY MODE</p>
            <h2 id="strategy-title">30 天策略表现 / 30-day Strategy Performance</h2>
          </div>
          <span className="badge badge-degraded">策略证据不可用 / unavailable</span>
        </div>
        <p role="status" className="strategy-degradation-message">
          策略证据与市场回放窗口无法作为一个完整快照通过校验，当前仅展示市场数据。未使用 106 天结果替代 30 天指标。
          <span>Strategy evidence failed whole-snapshot validation. Market data remains available; no 106-day values are substituted.</span>
        </p>
      </section>
    );
  }

  const { window, methodology, long_term_evidence: longTerm, provenance } = strategy;

  return (
    <section className="strategy-section" aria-labelledby="strategy-title">
      <div className="strategy-heading">
        <div>
          <p className="strategy-kicker">OCTOBER EVIDENCE SNAPSHOT</p>
          <h2 id="strategy-title">30 天策略表现 / 30-day Strategy Performance</h2>
          <p>固定完整窗口结论，不随播放指针变化。四种策略使用同一市场、容量尺度和结算口径。</p>
        </div>
        <span className="badge badge-ok">证据快照已校验 / validated</span>
      </div>

      <div className="strategy-boundary-grid" aria-label="测试边界">
        <div>
          <span>历史回放窗口</span>
          <strong>2025-10-01 → 2025-10-30</strong>
          <small>北京时间 UTC+8 · {window.points.toLocaleString()} 个 15 分钟点</small>
        </div>
        <div>
          <span>标准化回测日</span>
          <strong>{window.standardized_day}</strong>
          <small>{window.points_per_day} 点 / 日，不宣称官方交易日定义</small>
        </div>
        <div>
          <span>模型训练窗口</span>
          <strong>{longTerm.training_window.start} → {longTerm.training_window.end}</strong>
          <small>30 天回放位于训练窗口之后</small>
        </div>
        <div>
          <span>固定容量尺度</span>
          <strong>{methodology.capacity_scale_mw.toLocaleString("zh-CN", { minimumFractionDigits: 2 })} MW</strong>
          <small>省级回测缩放参数，不是交易主体容量或成交电量</small>
        </div>
      </div>

      <div className="strategy-methodology">
        <div>
          <span>模拟价差值 / Simulated Spread Value</span>
          <code>还原持仓 × 固定容量尺度 ×（历史实时结算价 − 当日回测基准价）÷ 1000</code>
        </div>
        <p>
          前 {methodology.baseline_initialization_days} 天为<strong>基准初始化期</strong>，使用完整当日实时价格均值；第 8 天起使用此前 7 天、672 点均价。
          结果适合同口径策略比较，不是严格可交易回测，也不是人民币利润、收入或投资收益率。
        </p>
      </div>

      <div className="strategy-interpretation" aria-label="如何理解策略水平">
        <div>
          <span>模拟相对表现</span>
          <strong>较强 / Relatively strong</strong>
          <p>TD3 的 30 天累计模拟价差值为趋势基线的 5.59×，捕获 Oracle 理论价差的 14.9%。</p>
        </div>
        <div>
          <span>现实盈利水平</span>
          <strong>未评定 / Unassessed</strong>
          <p>缺少真实交易容量、资金占用、手续费、滑点、保证金和偏差考核，不能据此评价现实收益高低。</p>
        </div>
      </div>

      <StrategyTable rows={strategy.summary} />
      <p className="strategy-table-hint">手机端可左右滑动查看全部指标 / Swipe horizontally for all metrics.</p>

      <div className="strategy-definitions">
        <p><strong>持仓时段正贡献率</strong>：仅统计绝对还原持仓 ≥ 1% 的时段；近似空仓不进入分母。</p>
        <p><strong>盈利因子 / Profit Factor</strong>：正模拟价差值总和 ÷ 负模拟价差值绝对值总和，不是收益率或平均单笔盈亏比。</p>
        <p><strong>最大回撤</strong>：从历史累计峰值到后续低点的最大损失幅度，按正数展示，越小表示路径回撤越小。</p>
      </div>

      <article className="strategy-long-term" aria-labelledby="long-term-title">
        <div>
          <p className="strategy-kicker">INDEPENDENT LONG-WINDOW EVIDENCE</p>
          <h3 id="long-term-title">106 天样本外稳定性评估</h3>
          <p>北京时间 2025-10-01 至 2026-01-14 · {longTerm.points.toLocaleString()} 个 15 分钟点</p>
        </div>
        <p>
          <strong>PPO 在 106 天累计窗口领先；TD3 在当前 30 天累计窗口领先。</strong>
          领先策略会随评估窗口变化，因此不宣布固定冠军，也不把长期指标混入上方 30 天表格。
        </p>
      </article>

      <details className="strategy-settings">
        <summary>测试设置与证据来源 / Test settings &amp; provenance</summary>
        <dl>
          <div><dt>训练步数</dt><dd>{provenance.training_steps_per_algorithm.toLocaleString()} / 算法</dd></div>
          <div><dt>随机种子</dt><dd>{provenance.seed}</dd></div>
          <div><dt>特征层级</dt><dd>{provenance.feature_tier.toUpperCase()}</dd></div>
          <div><dt>报告生成时间</dt><dd>{provenance.source_generated_at}</dd></div>
          <div><dt>来源 Git SHA</dt><dd><code>{provenance.source_git_sha}</code></dd></div>
          <div><dt>快照身份 SHA-256</dt><dd><code>{provenance.content_hash}</code></dd></div>
        </dl>
      </details>
    </section>
  );
}
