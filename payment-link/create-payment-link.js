// Crea un link de pago con boleta automática y espera a que lo paguen.
//
//   export TUPANA_API_KEY=...            # usa tu key de SANDBOX para probar sin mover dinero
//   export TUPANA_RECIPIENT_ID=ment_...  # empresa que recibe los fondos (con cuenta bancaria)
//   node create-payment-link.js --rut 11111111-1 --name "Juan Soto" --email juan@ejemplo.com \
//     --description "Sesión de psicoterapia" --amount 50000 --ref booking_abc123 --watch
import { parseArgs } from "node:util";
import Tupana from "tupana";
import { createPaymentLink, waitForPayment } from "./payment-link.js";

const { values: v } = parseArgs({
  options: {
    rut: { type: "string" },
    name: { type: "string" },
    email: { type: "string" },
    description: { type: "string" },
    amount: { type: "string" },
    ref: { type: "string" },
    "redirect-url": { type: "string" },
    watch: { type: "boolean", default: false },
  },
});

const recipientId = process.env.TUPANA_RECIPIENT_ID;
if (!recipientId || !v.rut || !v.name || !v.description || !v.amount || !v.ref) {
  console.error("Faltan datos: TUPANA_RECIPIENT_ID, --rut, --name, --description, --amount y --ref");
  process.exit(2);
}

const tupana = new Tupana();
const payment = await createPaymentLink(tupana, {
  recipientId,
  customer: { rut: v.rut, name: v.name, ...(v.email ? { email: v.email } : {}) },
  items: [{ description: v.description, quantity: 1, unit_price: Number(v.amount) }],
  externalId: v.ref,
  redirectUrl: v["redirect-url"],
});

console.log(`Cobro ${payment.payment_request_id} (${payment.status})`);
console.log(`Link de pago: ${payment.payment_url}`);
console.log(`Vence: ${payment.expires_at}`);

if (v.watch) {
  console.log("\nEsperando el pago…");
  const final = await waitForPayment(tupana, payment.payment_request_id, {
    onPoll: (pr) => process.stdout.write(`  estado: ${pr.status}\r`),
  });
  console.log(`\nEstado final: ${final.status}`);
  if (final.issued_document_id) console.log(`Documento emitido: ${final.issued_document_id}`);
}
