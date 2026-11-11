// Cloud Run entry point: POST /compile, POST /scan, GET /risk, and the demo pages under /demo.
import http from "node:http";
import { readFile } from "node:fs/promises";
import { join, normalize } from "node:path";
import { fileURLToPath } from "node:url";
import { compile } from "./compile.js";
import { scan } from "./scan.js";
import { risk } from "./risk.js";

const DEMO = join(fileURLToPath(new URL(".", import.meta.url)), "demo");
const TYPES = { ".html": "text/html; charset=utf-8", ".js": "text/javascript", ".css": "text/css" };

function send(res, status, body, type = "application/json") {
  res.writeHead(status, {
    "content-type": type,
    "access-control-allow-origin": "*",
    "access-control-allow-headers": "content-type",
  });
  res.end(type === "application/json" ? JSON.stringify(body) : body);
}

async function readJson(req) {
  let raw = "";
  for await (const chunk of req) { raw += chunk; if (raw.length > 64_000) throw new RangeError("body too large"); }
  return JSON.parse(raw || "{}");
}

async function handle(req, res) {
  const url = new URL(req.url, "http://x");
  if (req.method === "OPTIONS") return send(res, 204, "", "text/plain");
  if (req.method === "POST" && url.pathname === "/compile") {
    const { mandate, currentUrl } = await readJson(req);
    return send(res, 200, await compile(mandate, currentUrl));
  }
  if (req.method === "POST" && url.pathname === "/scan") {
    const { url: page, snippets } = await readJson(req);
    return send(res, 200, await scan(page, snippets));
  }
  if (req.method === "GET" && url.pathname === "/risk") {
    return send(res, 200, { threats: await risk(url.searchParams.get("url")) });
  }
  if (req.method === "POST" && url.pathname === "/demo/api/transfer") {
    return send(res, 200, { ok: true, received: await readJson(req) });
  }
  if (req.method === "GET" && url.pathname.startsWith("/demo")) {
    const rel = normalize(url.pathname.slice(5) || "/index.html").replace(/^(\.\.[/\\])+/, "");
    const file = join(DEMO, rel === "/" ? "index.html" : rel);
    if (!file.startsWith(DEMO)) return send(res, 404, { error: "not found" });
    const ext = file.slice(file.lastIndexOf("."));
    return send(res, 200, await readFile(file), TYPES[ext] || "application/octet-stream");
  }
  if (url.pathname === "/") return send(res, 200, { service: "mandat", ok: true });
  send(res, 404, { error: "not found" });
}

http.createServer((req, res) => {
  handle(req, res).catch((e) => {
    const status = e instanceof RangeError || e instanceof SyntaxError || e instanceof TypeError ? 400 : e.code === "ENOENT" ? 404 : 500;
    console.error(e);
    send(res, status, { error: e.message });
  });
}).listen(process.env.PORT || 8080, () => console.log(`mandat backend on :${process.env.PORT || 8080}`));
