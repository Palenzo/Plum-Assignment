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

// Dev/prod toggle. APP_ENV wins; otherwise fall back to Next's NODE_ENV.
// Verbose proxy request logging is on in development, and can be forced on in
// production (e.g. to debug a deploy) with PROXY_DEBUG=true. Errors are ALWAYS
// logged, regardless of this flag.
const APP_ENV = (process.env.APP_ENV ?? process.env.NODE_ENV ?? "production").toLowerCase();
const DEBUG = process.env.PROXY_DEBUG === "true" || APP_ENV === "development";

function log(...args: unknown[]): void {
  if (DEBUG) console.log("[proxy]", ...args);
}

// Surfaced once at boot so the resolved backend target is obvious in the logs.
log(`backend target = ${BACKEND} (APP_ENV=${APP_ENV}, BACKEND_URL ${process.env.BACKEND_URL ? "set" : "UNSET → using fallback"})`);

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
  const startedAt = Date.now();
  log(`-> ${req.method} ${target}`);
  try {
    const res = await fetch(target, {
      method: req.method,
      headers,
      body: hasBody ? await req.arrayBuffer() : undefined,
      cache: "no-store",
    });

    const body = await res.arrayBuffer();
    log(`<- ${res.status} ${req.method} ${target} (${Date.now() - startedAt}ms)`);
    return new Response(body, {
      status: res.status,
      headers: { "content-type": res.headers.get("content-type") ?? "application/json" },
    });
  } catch (err) {
    // Backend unreachable (wrong BACKEND_URL, cold start, DNS, network). Log the
    // real cause and return a clean 502 envelope instead of an opaque Next 500.
    const cause = err instanceof Error ? err.cause ?? err.message : err;
    console.error(`[proxy] FAILED ${req.method} ${target} ->`, cause);
    return new Response(
      JSON.stringify({
        error: "Backend is unreachable. Check BACKEND_URL and that the backend is up.",
        code: "UPSTREAM_ERROR",
      }),
      { status: 502, headers: { "content-type": "application/json" } },
    );
  }
}

type Ctx = { params: Promise<{ path: string[] }> };
const handler = async (req: NextRequest, ctx: Ctx) => proxy(req, (await ctx.params).path);

export { handler as GET, handler as POST, handler as PUT, handler as DELETE, handler as PATCH };
