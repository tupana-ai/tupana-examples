import express from "express";
import { constructWebhookEvent, WebhookVerificationError } from "@tupana-ai/sdk";

/**
 * Receptor de webhooks de Tupana.
 *
 * - Verifica X-Pana-Signature (HMAC SHA-256 del cuerpo CRUDO) antes de tocar el JSON.
 * - Descarta entregas repetidas por X-Pana-Event-Id.
 * - Responde 2xx rápido; el trabajo pesado va a una cola.
 */
export function createApp({ secret, processedEventIds = new Set(), log = console } = {}) {
  if (!secret) throw new Error("Falta TUPANA_WEBHOOK_SECRET");

  const handlers = {
    "document.issued": (data) => log.info(`Documento emitido: folio ${data.folio}, PDF ${data.pdf_file}`),
    "document.rejected": (data) => log.warn(`El SII rechazó el documento ${data.id}`),
    "document.paid": (data) => log.info(`Documento pagado: ${data.id}`),
    "payment_request.paid": (data) =>
      log.info(`Cobro ${data.payment_request_id} pagado (external_id=${data.external_id})`),
  };

  const app = express();

  // express.raw: necesitamos los bytes exactos para verificar la firma.
  app.post("/webhooks/tupana", express.raw({ type: "*/*", limit: "2mb" }), async (req, res) => {
    let event;
    try {
      event = await constructWebhookEvent(req.body, req.headers, secret);
    } catch (err) {
      if (err instanceof WebhookVerificationError) return res.status(400).json({ error: err.message });
      throw err;
    }

    // En producción guarda los ids en tu base de datos con un índice único.
    const eventId = req.get("x-pana-event-id");
    if (eventId && processedEventIds.has(eventId)) return res.json({ ok: true, duplicate: true });

    const handler = handlers[event.event];
    if (handler) handler(event.data ?? {});
    else log.info(`Evento sin handler: ${event.event}`);

    if (eventId) processedEventIds.add(eventId);
    res.json({ ok: true });
  });

  return app;
}
