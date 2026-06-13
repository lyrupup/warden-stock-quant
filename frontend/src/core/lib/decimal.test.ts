import { describe, expect, it } from "vitest";
import { fmtMoney, fmtPct, toNum } from "./decimal";

describe("decimal utils", () => {
  it("toNum 转换字符串与数值，空值返回 NaN", () => {
    expect(toNum("10.5")).toBe(10.5);
    expect(toNum(3)).toBe(3);
    expect(Number.isNaN(toNum(null))).toBe(true);
    expect(Number.isNaN(toNum(""))).toBe(true);
  });

  it("fmtPct 比率转百分比", () => {
    expect(fmtPct("0.1234")).toBe("12.34%");
    expect(fmtPct(null)).toBe("-");
  });

  it("fmtMoney 金额本地化两位小数", () => {
    expect(fmtMoney("1000")).toBe("1,000.00");
    expect(fmtMoney(null)).toBe("-");
  });
});
