import express from "express";
import path from "path";
import http from "http";
import { spawn } from "child_process";
import { createServer as createViteServer } from "vite";

async function startServer() {
  const app = express();
  const PORT = 3000;

  // 1. Spawn FastAPI as a Python child process on port 8000
  console.log("[Server] Spawning FastAPI backend on port 8000...");
  const pythonProcess = spawn("python3", [
    "-m", "uvicorn", "backend.main:app",
    "--host", "127.0.0.1",
    "--port", "8000"
  ], {
    env: {
      ...process.env,
      PYTHONPATH: path.join(process.cwd(), "backend")
    }
  });

  pythonProcess.stdout.on("data", (data) => {
    console.log(`[FastAPI] ${data.toString().trim()}`);
  });

  pythonProcess.stderr.on("data", (data) => {
    console.error(`[FastAPI-Err] ${data.toString().trim()}`);
  });

  process.on("exit", () => {
    pythonProcess.kill();
  });

  // 2. Proxy API routes directly to the FastAPI server
  app.all("/api/*", (req, res) => {
    const targetUrl = `http://127.0.0.1:8000${req.originalUrl}`;
    const parsedUrl = new URL(targetUrl);

    const proxyReq = http.request({
      hostname: parsedUrl.hostname,
      port: parsedUrl.port,
      path: parsedUrl.pathname + parsedUrl.search,
      method: req.method,
      headers: req.headers
    }, (proxyRes) => {
      res.writeHead(proxyRes.statusCode || 200, proxyRes.headers);
      proxyRes.pipe(res, { end: true });
    });

    proxyReq.on("error", (err) => {
      console.error("[Proxy Error] Failed to connect to FastAPI:", err.message);
      res.status(502).send("Bad Gateway: FastAPI backend not available yet.");
    });

    req.pipe(proxyReq, { end: true });
  });

  // 3. Vite development / production static asset serving
  if (process.env.NODE_ENV !== "production") {
    console.log("[Server] Mounting Vite middleware (development mode)...");
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    console.log("[Server] Serving static files in production mode...");
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`[Server] Core Server running at http://0.0.0.0:${PORT}`);
  });
}

startServer().catch((err) => {
  console.error("[Server] Start failure:", err);
});
