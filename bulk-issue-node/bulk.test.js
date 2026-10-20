import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import Tupana from "tupana";
import { buildDocuments, idempotencyKey, issueAll, parseNumber, readCsv } from "./bulk.js";

const docs = buildDocuments(readCsv(readFileSync(new URL("./invoices.csv", import.meta.url), "utf8")), "76543210-3");

test("agrupa filas por ref", () => {
  assert.deepEqual(docs.map((d) => d.json_param.external_ref), ["PED-1001", "PED-1002", "PED-1003"]);
  assert.equal(docs[0].details.length, 2);
  assert.deepEqual(docs[0].header, { due_date: "2026-11-30" });
});

test("parsea números en formato chileno", () => {
  for (const [raw, expected] of [["49990", 49990], ["49.990", 49990], ["1.234.567", 1234567], ["49.990,5", 49990.5], ["12,5", 12.5], ["$ 5.990", 5990]]) {
    assert.equal(parseNumber(raw, "unit_price", 2), expected);
  }
  assert.throws(() => parseNumber("abc", "quantity", 3));
});

test("la idempotency key es estable", () => {
  assert.equal(idempotencyKey(docs), idempotencyKey(structuredClone(docs)));
  assert.notEqual(idempotencyKey(docs), idempotencyKey(docs.slice(1)));
});

test("emite en lotes con Idempotency-Key y X-Use-Defaults", async () => {
  const calls = [];
  const fetch = async (url, init) => {
    calls.push({ url, init });
    if (init.method === "POST") return Response.json({ batch_id: "b1", documents: [] }, { status: 201 });
    return Response.json({
      id: "b1",
      status: "completed",
      documents: docs.map((_, i) => ({ index: i, status: "success", document: { folio: String(100 + i) } })),
    });
  };
  const results = await issueAll(new Tupana({ apiKey: "k", fetch }), docs, () => {});
  assert.deepEqual(results.map((r) => r.folio), ["100", "101", "102"]);
  const headers = new Headers(calls[0].init.headers);
  assert.match(headers.get("idempotency-key"), /^bulk-/);
  assert.equal(headers.get("x-use-defaults"), "true");
});
