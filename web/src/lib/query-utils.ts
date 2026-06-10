/** 将 fetch / React Query 错误转为可读中文（避免整段 JSON 贴在页面上） */
export function formatQueryError(err: unknown): string {
  if (!(err instanceof Error)) return "未知错误";
  const raw = err.message.trim();
  if (!raw) return "请求失败";
  try {
    const j = JSON.parse(raw) as {
      error?: string;
      hint?: string;
      message?: string;
      detail?: string;
    };
    if (j.error === "backend_unreachable") {
      return j.hint || j.message || "后端暂不可用，请稍后刷新";
    }
    if (typeof j.detail === "string") return j.detail;
    if (typeof j.message === "string") return j.message;
  } catch {
    /* 非 JSON */
  }
  if (raw.includes("backend_unreachable")) {
    return "后端暂不可用（多为 API 正在重启），请稍后刷新页面";
  }
  return raw.length > 200 ? `${raw.slice(0, 200)}…` : raw;
}

export const defaultQueryRetry = (failureCount: number, err: unknown) => {
  if (failureCount >= 2) return false;
  if (err instanceof Error) {
    const m = err.message;
    if (m.includes("backend_unreachable") || m.includes("fetch failed")) {
      return true;
    }
  }
  return failureCount < 1;
};
