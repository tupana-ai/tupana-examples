# Link de pago con boleta automática

Crea un cobro con [`@tupana-ai/sdk`](https://github.com/tupana-ai/tupana-node): Tupana te devuelve un `payment_url`, tu cliente paga (Webpay) y, al confirmarse el pago, Tupana **emite la boleta (39) o factura (33) sola** y deposita los fondos al destinatario.

- `external_id` es la llave de idempotencia: si repites la llamada con el mismo valor (por ejemplo el id de la reserva), obtienes el mismo cobro.
- `--watch` consulta el estado hasta que se pague o venza. En producción escucha el webhook `payment_request.paid` (mira [`../webhook-express`](../webhook-express)).
- Con la API key de **sandbox** el flujo usa el ambiente de integración de Transbank: no se mueve dinero ni se emite al SII.

## Correr

```bash
cd payment-link
npm install
export TUPANA_API_KEY="tu-api-key-de-sandbox"
export TUPANA_RECIPIENT_ID="ment_…"   # empresa que recibe los fondos (con cuenta bancaria registrada)
node create-payment-link.js --rut 11111111-1 --name "Juan Soto" --email juan@ejemplo.com \
  --description "Sesión de psicoterapia" --amount 50000 --ref booking_abc123 --watch
npm test
```

Más detalles del modelo de cobros (modo emisión vs. cobro directo de documentos existentes, comisiones, liquidaciones): [docs.tupana.ai](https://docs.tupana.ai).
