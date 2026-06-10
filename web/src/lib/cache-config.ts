/** API 缓存：1 分钟 */
export const CACHE_MAX_AGE_SEC = 60;

export const CACHE_STALE_MS = CACHE_MAX_AGE_SEC * 1000;

export const REVALIDATE_SEC = CACHE_MAX_AGE_SEC;

export const CACHE_CONTROL_HEADER = `public, max-age=${CACHE_MAX_AGE_SEC}, stale-while-revalidate=${CACHE_MAX_AGE_SEC}`;

export const HEALTH_STALE_MS = CACHE_STALE_MS;

export function isCacheableApiGet(path: string, search = ""): boolean {
  if (!path.startsWith("/api/v1/")) return false;
  if (path.startsWith("/api/v1/admin/")) return false;
  if (path.startsWith("/api/v1/me/")) return false;
  if (path.startsWith("/api/v1/auth/")) return false;
  if (path === "/api/v1/health" || path === "/api/v1/version") return false;
  if (path.includes("/lump-sum") && !path.endsWith("/meta")) return false;
  if (search.includes("refresh=true")) return false;
  return (
    path.startsWith("/api/v1/instruments") ||
    path.startsWith("/api/v1/dashboard") ||
    path.startsWith("/api/v1/site/") ||
    path.startsWith("/api/v1/market/") ||
    path.startsWith("/api/v1/funds")
  );
}
