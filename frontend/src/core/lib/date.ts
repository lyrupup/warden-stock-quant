/** 日期/时间格式化工具 */

/** ISO 日期时间 → "YYYY-MM-DD HH:mm" */
export const fmtDateTime = (v?: string | null): string => {
  if (!v) return "-";
  const d = new Date(v);
  if (Number.isNaN(d.getTime())) return v;
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(
    d.getHours(),
  )}:${pad(d.getMinutes())}`;
};

/** ISO 日期 → "YYYY-MM-DD" */
export const fmtDate = (v?: string | null): string => {
  if (!v) return "-";
  return v.slice(0, 10);
};
