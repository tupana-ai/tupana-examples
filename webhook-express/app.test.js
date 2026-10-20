import assert from "node:assert/strict";
import { test } from "node:test";
import { computeWebhookSignature } from "@tupana-ai/sdk";
import { createApp } from "./app.js";

const secret = "whsec_test";
const quiet = { info() {}, warn() {} };

async function withServer(fn) {
  const server = createApp({ secret, log: quiet }).listen(0);
  await new Promise((r) => server.once("listening", r));
  const url = `http://127.0.0.1:${server.address().port}/webhooks/tupana`;
  try {
    await fn(url);
  } finally {
    server.close();
  }
}

const body = JSON.stringify({ event: "document.issued", data: { folio: "1234" } });

test("acepta una firma válida y deduplica por X-Pana-Event-Id", async () => {
  await withServer(async (url) => {
    const headers = {
      "Content-Type": "application/json",
      "X-Pana-Event-Id": "evt_1",
      "X-Pana-Signature": await computeWebhookSignature(body, secret),
    };
    const first = await fetch(url, { method: "POST", headers, body });
    assert.equal(first.status, 200);
    assert.deepEqual(await first.json(), { ok: true });
    const again = await fetch(url, { method: "POST", headers, body });
    assert.deepEqual(await again.json(), { ok: true, duplicate: true });
  });
});

test("rechaza una firma inválida", async () => {
  await withServer(async (url) => {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Pana-Signature": "00".repeat(32) },
      body,
    });
    assert.equal(res.status, 400);
  });
});
