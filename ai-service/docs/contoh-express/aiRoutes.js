// CONTOH untuk tim Full-stack: salin ke server/src/routes/aiRoutes.js
// Pasang di app.js:  app.use('/api/ai', createAiRouter({ requireAdmin }))
import { Router } from "express";

export function createAiRouter({ requireAdmin } = {}) {
  const router = Router();
  const base = () => process.env.AI_SERVICE_URL || "http://localhost:8000";

  async function forward(req, res, path) {
    try {
      const upstream = await fetch(base() + path, {
        method: req.method,
        headers: {
          "content-type": "application/json",
          "x-internal-key": process.env.INTERNAL_API_KEY || "",
        },
        body: req.method === "POST" ? JSON.stringify(req.body) : undefined,
        signal: AbortSignal.timeout(30000),
      });
      res.status(upstream.status).json(await upstream.json());
    } catch {
      res.status(503).json({ detail: "Layanan AI sedang tidak tersedia." });
    }
  }

  router.get("/areas", (req, res) => forward(req, res, "/v1/areas"));
  router.get("/products/search", (req, res) =>
    forward(req, res, "/v1/products/search?" + new URLSearchParams(req.query)));
  router.post("/branches/recommend", (req, res) => forward(req, res, "/v1/branches/recommend"));
  // TODO FS: tambahkan rate limit pada chat agar kuota gratis tidak habis.
  router.post("/chat", (req, res) => forward(req, res, "/v1/assistant/chat"));

  // Rute memuat lokasi pelanggan: WAJIB admin. Tanpa middleware, endpoint ditutup.
  const adminOnly = requireAdmin || ((req, res) => res.status(403).json({ detail: "Autentikasi admin belum dipasang." }));
  router.post("/routes/optimize", adminOnly, (req, res) => forward(req, res, "/v1/routes/optimize"));

  return router;
}
