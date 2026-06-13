/** 业务错误：响应 code != 0 时抛出，携带后端错误码与消息 */
export class ApiError extends Error {
  readonly code: number;

  constructor(code: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.code = code;
  }
}

/** 常见错误码（与 openapi responses 对齐，按需扩展） */
export const ErrorCode = {
  BadRequest: 10001,
  NotFound: 10002,
  Conflict: 10003,
  Unauthorized: 40101,
  Forbidden: 40301,
  QuotaExceeded: 42902,
  JobAccepted: 60001,
  StrategyInvalid: 61001,
  RiskRejected: 62001,
} as const;

/** 取得人类可读的错误提示（可后续接入 i18n 错误码映射） */
export function describeError(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.code === ErrorCode.QuotaExceeded) return `${err.message}（请升级套餐）`;
    return err.message;
  }
  if (err instanceof Error) return err.message;
  return "未知错误";
}
