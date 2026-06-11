/**
 * Server-side proxy: forwards /api/* from the browser to the backend.
 *
 * Why a proxy instead of the browser calling the backend directly:
 *  - The backend URL is read at RUNTIME (BACKEND_URL), not baked into the
 *    client bundle at build time — so the same image works in any environment.
 *  - The browser only ever talks to its own origin, so there is no CORS to
 *    configure and no cross-origin surprises on Render.
 */
import { NextRequest } from "next/server";

export const dynamic = "force-dynamic";

// 127.0.0.1 (not "localhost") so Node doesn't try IPv6 ::1 first against an
// IPv4-only backend during local dev. BACKEND_URL overrides this everywhere else.
const RAW = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";
const BACKEND = /^https?:\/\//.test(RAW) ? RAW : `https://${RAW}`;

// Only forward headers that matter; let fetch set host/content-length itself.
const FORWARD = ["content-type", "x-admin-token"];

async function proxy(req: NextRequest, path: string[]): Promise<Response> {
  const target = `${BACKEND}/api/${path.join("/")}${req.nextUrl.search}`;

  const headers: Record<string, string> = {};
  for (const name of FORWARD) {
    const value = req.headers.get(name);
    if (value) headers[name] = value;
  }

  const hasBody = req.method !== "GET" && req.method !== "HEAD";
  const res = await fetch(target, {
    method: req.method,
    headers,
    body: hasBody ? await req.arrayBuffer() : undefined,
    cache: "no-store",
  });

  const body = await res.arrayBuffer();
  return new Response(body, {
    status: res.status,
    headers: { "content-type": res.headers.get("content-type") ?? "application/json" },
  });
}

type Ctx = { params: Promise<{ path: string[] }> };
const handler = async (req: NextRequest, ctx: Ctx) => proxy(req, (await ctx.params).path);

export { handler as GET, handler as POST, handler as PUT, handler as DELETE, handler as PATCH };
