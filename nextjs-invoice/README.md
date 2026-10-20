# Next.js: emitir una factura desde una ruta de API

App Router con tres rutas de servidor que usan [`@tupana-ai/sdk`](https://github.com/tupana-ai/tupana-node):

| Ruta | Qué hace |
| --- | --- |
| `POST /api/invoices` | Emite una factura electrónica (DTE 33) con `X-Use-Defaults` y el id de tu pedido como `Idempotency-Key`: un doble clic no emite dos veces. Responde `202` con el `batchId`. |
| `GET /api/invoices/[batchId]` | Estado de la emisión en el SII, folio, total y link al PDF. |
| `POST /api/webhooks/tupana` | Recibe los webhooks con la firma `X-Pana-Signature` verificada (usa `request.text()` para tener el cuerpo crudo). |

La página `/` tiene un formulario mínimo que emite y consulta el estado hasta que el SII responde.

## Correr

```bash
cd nextjs-invoice
npm install
cp .env.example .env.local   # completa TUPANA_API_KEY (usa la de sandbox), TUPANA_ISSUER_RUT y TUPANA_WEBHOOK_SECRET
npm run dev
```

Abre http://localhost:3000. Con la key de **sandbox** el documento se crea y se puede consultar, pero no va al SII.

Para recibir webhooks en local, expón el puerto (por ejemplo con `ngrok http 3000`) y crea el webhook apuntando a `https://<tu-túnel>/api/webhooks/tupana` con un `secret`.

## Antes de llevarlo a producción

- Protege `POST /api/invoices` con la autenticación de tu app: tal como está, cualquiera que llegue a la ruta puede emitir.
- La API key vive solo en el servidor (`lib/tupana.ts` importa `server-only`).
- Guarda el `X-Pana-Event-Id` de cada webhook procesado para no procesarlo dos veces.
- Cuando la página de estado no basta, escucha `document.issued` / `document.rejected` en vez de hacer polling.

Documentación: [docs.tupana.ai](https://docs.tupana.ai) · API keys: [developers.tupana.ai](https://developers.tupana.ai)
