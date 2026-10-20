/**
 * Crea un link de pago que, al pagarse, emite la boleta o factura solo.
 *
 * `externalId` es tu llave de idempotencia: si lo repites, Tupana devuelve el
 * mismo cobro en vez de crear otro (por ejemplo, el id de la reserva o del pedido).
 */
export async function createPaymentLink(tupana, { recipientId, customer, items, externalId, redirectUrl, dteType = 39 }) {
  const amount = items.reduce((sum, it) => sum + it.quantity * it.unit_price, 0);
  return tupana.paymentRequests.create({
    recipient_id: recipientId,
    amount,
    target_dte_type: dteType, // 39 boleta, 41 boleta exenta, 33 factura
    dte_recipient: customer,
    items,
    external_id: externalId,
    redirect_url: redirectUrl,
    expires_in_minutes: 60,
    metadata: { source: "tupana-examples" },
  });
}

const FINAL = new Set(["paid", "issued", "failed", "expired", "refunded"]);

/** Consulta el cobro hasta un estado final. En producción, escucha el webhook payment_request.paid. */
export async function waitForPayment(tupana, id, { interval = 5_000, timeout = 3_600_000, onPoll } = {}) {
  const deadline = Date.now() + timeout;
  for (;;) {
    const pr = await tupana.paymentRequests.retrieve(id);
    if (FINAL.has(pr.status)) return pr;
    onPoll?.(pr);
    if (Date.now() + interval > deadline) return pr;
    await new Promise((r) => setTimeout(r, interval));
  }
}
