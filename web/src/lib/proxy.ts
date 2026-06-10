import { NextRequest, NextResponse } from "next/server";
import {
  CACHE_CONTROL_HEADER,
  isCacheableApiGet,
  REVALIDATE_SEC,
} from "@/lib/cache-config";

/** 运行时读取：Docker 用 http://api:8001，本地 dev 用 http://127.0.0.1:8001 */
export function getApiBase(): string {
  return (
    process.env.API_INTERNAL_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    "http://127.0.0.1:8001"
  );
}

const PROXY_RETRIES = 3;
const PROXY_RETRY_DELAY_MS = 400;

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function fetchBackend(
  url: string,
  init: RequestInit,
  cacheable: boolean
): Promise<Response> {
  let lastErr: unknown;
  for (let attempt = 1; attempt <= PROXY_RETRIES; attempt++) {
    try {
      return await fetch(url, {
        ...init,
        ...(cacheable
          ? { next: { revalidate: REVALIDATE_SEC } }
          : { cache: "no-store" }),
        signal: AbortSignal.timeout(120_000),
      });
    } catch (err) {
      lastErr = err;
      if (attempt < PROXY_RETRIES) {
        await sleep(PROXY_RETRY_DELAY_MS * attempt);
      }
    }
  }
  throw lastErr;
}

export async function proxyToBackend(
  req: NextRequest,
  backendPath: string
): Promise<NextResponse> {
  const base = getApiBase().replace(/\/$/, "");
  const search = req.nextUrl.search;
  const url = `${base}${backendPath}${search}`;
  const cacheable =
    req.method === "GET" && isCacheableApiGet(backendPath, search);

  const headers = new Headers();
  const contentType = req.headers.get("content-type");
  if (contentType) headers.set("content-type", contentType);
  const authorization = req.headers.get("authorization");
  if (authorization) headers.set("authorization", authorization);

  let body: string | undefined;
  if (req.method !== "GET" && req.method !== "HEAD") {
    body = await req.text();
  }

  try {
    const res = await fetchBackend(
      url,
      {
        method: req.method,
        headers,
        body,
      },
      cacheable
    );
    const resType = res.headers.get("content-type") || "";
    if (resType.includes("text/event-stream") && res.body) {
      return new NextResponse(res.body, {
        status: res.status,
        headers: {
          "content-type": resType,
          "cache-control": "no-cache",
          connection: "keep-alive",
        },
      });
    }
    const text = await res.text();
    const outHeaders: Record<string, string> = {
      "content-type": resType || "application/json",
    };
    const backendCache = res.headers.get("cache-control");
    if (cacheable) {
      outHeaders["cache-control"] = backendCache || CACHE_CONTROL_HEADER;
    }
    return new NextResponse(text, {
      status: res.status,
      headers: outHeaders,
    });
  } catch (err) {
    const msg = err instanceof Error ? err.message : "proxy error";
    return NextResponse.json(
      {
        error: "backend_unreachable",
        message: msg,
        hint: `无法连接 ${base}。Docker 请执行: docker compose -p invest-analyzer up -d api web；本地开发请设 API_INTERNAL_URL=http://127.0.0.1:8001`,
      },
      { status: 502 }
    );
  }
}
