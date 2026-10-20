import assert from "node:assert/strict";
import { test } from "node:test";
import Tupana from "tupana";
import { createPaymentLink, waitForPayment } from "./payment-link.js";

test("crea el cobro con monto calculado y espera el pago", async () => {
  const statuses = ["pending", "paid"];
  const calls = [];
  const fetch = async (url, init) => {
    calls.push({ url, method: init.method, body: init.body ? JSON.parse(init.body) : undefined });
    if (init.method === "POST") {
      return Response.json({ payment_request_id: "pare_1", status: "pending", payment_url: "https://www.tupana.ai/pagos/tok" }, { status: 201 });
    }
    return Response.json({ payment_request_id: "pare_1", status: statuses.shift(), issued_document_id: "docu_9" });
  };
  const tupana = new Tupana({ apiKey: "k", fetch });
  const pr = await createPaymentLink(tupana, {
    recipientId: "ment_1",
    customer: { rut: "11111111-1", name: "Juan Soto" },
    items: [{ description: "Sesión", quantity: 2, unit_price: 25000 }],
    externalId: "booking_abc",
  });
  assert.equal(pr.payment_url, "https://www.tupana.ai/pagos/tok");
  assert.equal(calls[0].body.amount, 50000);
  assert.equal(calls[0].body.external_id, "booking_abc");
  assert.equal(calls[0].body.target_dte_type, 39);
  const final = await waitForPayment(tupana, "pare_1", { interval: 1 });
  assert.equal(final.status, "paid");
});
