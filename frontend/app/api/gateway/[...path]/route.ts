import { NextRequest, NextResponse } from "next/server";

const gatewayBase = () =>
  (process.env.GATEWAY_URL ?? "http://127.0.0.1:3001").replace(/\/$/, "");

function authHeaders(): HeadersInit {
  const secret = process.env.API_SECRET;
  const h: Record<string, string> = {};
  if (secret) {
    h["Authorization"] = `Bearer ${secret}`;
  }
  return h;
}

async function proxy(req: NextRequest, segments: string[]) {
  const path = segments.join("/");
  const url = `${gatewayBase()}/api/${path}${req.nextUrl.search}`;
  const method = req.method.toUpperCase();
  const init: RequestInit = {
    method,
    headers: {
      ...authHeaders(),
      Accept: "application/json",
    },
  };
  if (method !== "GET" && method !== "HEAD") {
    const text = await req.text();
    if (text) {
      init.headers = {
        ...init.headers,
        "Content-Type": "application/json",
      };
      init.body = text;
    }
  }
  const res = await fetch(url, init);
  const body = await res.text();
  return new NextResponse(body, {
    status: res.status,
    headers: { "Content-Type": res.headers.get("content-type") ?? "application/json" },
  });
}

export async function GET(
  req: NextRequest,
  ctx: { params: Promise<{ path: string[] }> },
) {
  const { path } = await ctx.params;
  return proxy(req, path);
}

export async function POST(
  req: NextRequest,
  ctx: { params: Promise<{ path: string[] }> },
) {
  const { path } = await ctx.params;
  return proxy(req, path);
}
