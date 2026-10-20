// Firma un evento de prueba igual que Tupana y lo envía a tu receptor local.
import { randomUUID } from "node:crypto";
import { computeWebhookSignature } from "@tupana-ai/sdk";

const url = process.env.WEBHOOK_URL ?? "http://localhost:3000/webhooks/tupana";
const secret = process.env.TUPANA_WEBHOOK_SECRET;
if (!secret) throw new Error("Define TUPANA_WEBHOOK_SECRET");

const body = JSON.stringify({
  event: "document.issued",
  created_at: new Date().toISOString(),
  data: {
    id: "docu_8371029384756",
    folio: "1234",
    date_issued: "2026-10-20",
    amount_with_iva: 119000,
    dte_type: { code: "33", description: "Factura Electrónica" },
    pdf_file: "https://example.com/factura.pdf",
  },
});

const res = await fetch(url, {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "X-Pana-Event-Id": randomUUID(),
    "X-Pana-Event-Type": "document.issued",
    "X-Pana-Signature": await computeWebhookSignature(body, secret),
  },
  body,
});
console.log(res.status, await res.text());
