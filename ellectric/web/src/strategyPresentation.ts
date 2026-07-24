import type { StrategyKey } from "./types";

export const strategyOrder: StrategyKey[] = ["td3", "ppo", "sac", "trend"];

export const strategyPresentation: Record<StrategyKey, {
  label: string;
  color: string;
  dashed: boolean;
}> = {
  td3: { label: "TD3", color: "#60a5fa", dashed: false },
  ppo: { label: "PPO", color: "#2dd4bf", dashed: false },
  sac: { label: "SAC", color: "#fb923c", dashed: false },
  trend: { label: "趋势基线 / Trend", color: "#94a3b8", dashed: true },
};

export function simulatedValueParts(value: number, signed = true): { number: string; unit: string } {
  const sign = value < 0 ? "−" : signed && value > 0 ? "+" : "";
  const absolute = Math.abs(value);
  return absolute >= 10_000
    ? { number: `${sign}${(absolute / 10_000).toFixed(2)} 万`, unit: "模拟单位" }
    : { number: `${sign}${Math.round(absolute).toLocaleString("zh-CN")}`, unit: "模拟单位" };
}

export function formatSimulatedValue(value: number, signed = true): string {
  const formatted = simulatedValueParts(value, signed);
  return `${formatted.number} ${formatted.unit}`;
}
