// Server-side proxy to the FastAPI backend. The browser only ever talks to
// this origin; backend location and any API key stay on the server.
import { NextRequest } from "next/server";

const BACKEND = process.env.BACKEND_URL ?? "http://localhost:8000";
const API_KEY = process.env.MAVIRA_API_KEY;
const PASS_REQ = ["content-type", "x-analyst"];
const PASS_RES = ["content-type", "content-disposition"];

async function proxy(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  if (path.some((p) => p === ".." || p.includes("/"))) return new Response("Bad path", { status: 400 });
  const url = `${BACKEND}/api/${path.map(encodeURIComponent).join("/")}${req.nextUrl.search}`;
  const headers = new Headers();
  for (const h of PASS_REQ) {
    const v = req.headers.get(h);
    if (v) headers.set(h, v);
  }
  if (API_KEY) headers.set("x-api-key", API_KEY);
  const init: RequestInit & { duplex?: string } = { method: req.method, headers, cache: "no-store" };
  if (!["GET", "HEAD"].includes(req.method)) {
    init.body = await req.arrayBuffer();
  }
  try {
    const res = await fetch(url, init);
    const out = new Headers();
    for (const h of PASS_RES) {
      const v = res.headers.get(h);
      if (v) out.set(h, v);
    }
    return new Response(res.body, { status: res.status, headers: out });
  } catch {
    return Response.json({ error: "The assessment service is not reachable. Check that the backend is running." }, { status: 502 });
  }
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const dynamic = "force-dynamic";
