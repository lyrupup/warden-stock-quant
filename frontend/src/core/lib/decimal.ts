/**
 * 后端金额/比率/指标为 decimal 字符串，展示/计算前统一经此转换。
 * 禁止对 decimal 字符串直接做算术（见 AGENTS / FRONTEND §6）。
 */

/** decimal 字符串/数值 → number（null/空 → NaN） */
export const toNum = (v: string | number | null | undefined): number =>
  v == null || v === "" ? NaN : typeof v === "number" ? v : Number(v);

/** 比率 → 百分比展示，如 0.1234 → "12.34%" */
export const fmtPct = (v: string | number | null | undefined, digits = 2): string => {
  const n = toNum(v);
  return Number.isNaN(n) ? "-" : `${(n * 100).toFixed(digits)}%`;
};

/** 金额本地化展示，固定两位小数 */
export const fmtMoney = (v: string | number | null | undefined): string => {
  const n = toNum(v);
  return Number.isNaN(n)
    ? "-"
    : n.toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
};

/** 普通数值展示（缺省回退 "-"） */
export const fmtNum = (v: string | number | null | undefined, digits = 2): string => {
  const n = toNum(v);
  return Number.isNaN(n) ? "-" : n.toFixed(digits);
};
