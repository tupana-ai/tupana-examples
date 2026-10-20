import { createHash } from "node:crypto";
import { parse } from "csv-parse/sync";

export const MAX_BATCH_SIZE = 200;
const REQUIRED = ["ref", "dte_type", "receiver_rut", "item_name", "quantity", "unit_price"];
const CHILEAN_NUMBER = /^-?\d{1,3}(\.\d{3})+(,\d+)?$/;

/** Lee el CSV (coma o punto y coma, con o sin BOM). */
export function readCsv(text) {
  const firstLine = text.split(/\r?\n/, 1)[0] ?? "";
  const delimiter = firstLine.split(";").length > firstLine.split(",").length ? ";" : ",";
  return parse(text, { columns: true, skip_empty_lines: true, trim: true, bom: true, delimiter });
}

/** Acepta 49990, 49990.5, 49.990 y 49.990,5 (formato chileno). */
export function parseNumber(raw, field, line) {
  let text = String(raw).replace(/[$\s]/g, "");
  if (CHILEAN_NUMBER.test(text) || (text.includes(",") && !text.includes("."))) {
    text = text.replace(/\./g, "").replace(",", ".");
  }
  const value = Number(text);
  if (!Number.isFinite(value) || text === "") {
    throw new Error(`Fila ${line}: '${field}' no es un número (${raw})`);
  }
  return value;
}

/** Agrupa las filas por `ref`: cada grupo es un documento con sus líneas de detalle. */
export function buildDocuments(rows, issuerRut) {
  const missing = REQUIRED.filter((c) => rows.length && !(c in rows[0]));
  if (missing.length) throw new Error(`Faltan columnas: ${missing.join(", ")}`);
  const docs = new Map();
  rows.forEach((row, i) => {
    const line = i + 2;
    let doc = docs.get(row.ref);
    if (!doc) {
      doc = {
        dte_type: { code: String(row.dte_type) },
        document_issuer: { rut: issuerRut },
        document_receiver: { rut: row.receiver_rut },
        details: [],
        // Tu propio id: permite reencontrar el documento con
        // documents.list({ master_entity_id, json_param: { external_ref } }).
        json_param: { external_ref: row.ref },
      };
      if (row.due_date) doc.header = { due_date: row.due_date };
      docs.set(row.ref, doc);
    } else if (doc.document_receiver.rut !== row.receiver_rut) {
      throw new Error(`Fila ${line}: el documento ${row.ref} tiene dos receptores distintos`);
    }
    const item = {
      item_name: row.item_name,
      quantity: parseNumber(row.quantity, "quantity", line),
      unit_price: parseNumber(row.unit_price, "unit_price", line),
    };
    if (row.item_description) item.item_description = row.item_description;
    doc.details.push(item);
  });
  return [...docs.values()];
}

export function* chunks(items, size = MAX_BATCH_SIZE) {
  for (let i = 0; i < items.length; i += size) yield items.slice(i, i + size);
}

/** Misma entrada → misma key → la API no vuelve a emitir el lote si reintentas. */
export function idempotencyKey(chunk) {
  return `bulk-${createHash("sha256").update(JSON.stringify(chunk)).digest("hex").slice(0, 48)}`;
}

export const clp = (n) => `$${Math.round(n).toLocaleString("es-CL")}`;

/** Emite los documentos en lotes de 200 y devuelve el resultado por `ref`. */
export async function issueAll(tupana, docs, log = console.log) {
  const results = [];
  let number = 0;
  for (const chunk of chunks(docs)) {
    number += 1;
    log(`\nLote ${number}: enviando ${chunk.length} documento(s)…`);
    const created = await tupana.documents.createBatch(
      { documents: chunk },
      { useDefaults: true, idempotencyKey: idempotencyKey(chunk) },
    );
    for (const w of created.warnings ?? []) log(`  Aviso doc ${w.document_index}: ${w.message}`);
    const batch = await tupana.documents.waitForBatch(created.batch_id, { timeout: 600_000 });
    for (const item of batch.documents) {
      const ref = chunk[item.index]?.json_param?.external_ref;
      const doc = item.document ?? {};
      results.push({ ref, status: item.status, folio: doc.folio ?? "", document_id: doc.id ?? "", pdf_url: doc.pdf_url ?? "" });
      log(`  ${String(ref).padEnd(12)} ${String(item.status).padEnd(16)} folio ${doc.folio ?? "-"}`);
    }
  }
  return results;
}
