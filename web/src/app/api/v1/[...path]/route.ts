import { NextRequest } from "next/server";
import { proxyToBackend } from "@/lib/proxy";

type Ctx = { params: { path: string[] } };

async function handle(req: NextRequest, { params }: Ctx) {
  const segment = params.path.join("/");
  return proxyToBackend(req, `/api/v1/${segment}`);
}

export const GET = handle;
export const POST = handle;
export const PUT = handle;
export const PATCH = handle;
export const DELETE = handle;
