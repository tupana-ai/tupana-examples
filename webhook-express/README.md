# Receptor de webhooks con Express

Recibe las notificaciones de Tupana (`document.issued`, `document.rejected`, `payment_request.paid`…) de forma segura:

1. Lee el cuerpo **crudo** con `express.raw` (si lo parseas antes, la firma no calza).
2. Verifica `X-Pana-Signature`, el HMAC SHA-256 en hex del cuerpo con tu `secret`, con `constructWebhookEvent` de [`tupana`](https://github.com/tupana-ai/tupana-node).
3. Descarta entregas repetidas por `X-Pana-Event-Id` (la firma no incluye timestamp; la deduplicación es tu protección contra reenvíos).
4. Responde `2xx` rápido; si el trabajo es pesado, encólalo.

## Correr

```bash
cd webhook-express
npm install
export TUPANA_WEBHOOK_SECRET="un-secreto-largo"
npm start
# en otra terminal: firma y envía un evento de prueba
TUPANA_WEBHOOK_SECRET="un-secreto-largo" npm run send-test-event
npm test
```

Para que Tupana te alcance en local, expón el puerto (por ejemplo `ngrok http 3000`) y crea el webhook con el SDK:

```js
await tupana.webhooks.create({
  master_entity_id: "ment_…",
  url: "https://<tu-túnel>/webhooks/tupana",
  events: ["document.issued", "document.rejected", "payment_request.paid"],
  secret: process.env.TUPANA_WEBHOOK_SECRET,
});
```
