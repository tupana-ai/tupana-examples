// Emisión masiva de DTEs desde un CSV.
//
// Por defecto NO emite nada (modo prueba). Agrega --emit para emitir de verdad.
//
//   export TUPANA_API_KEY=...
//   node issue-from-csv.js invoices.csv --issuer-rut 76543210-3          # prueba
//   node issue-from-csv.js invoices.csv --issuer-rut 76543210-3 --emit   # emite
import { readFileSync, writeFileSync } from "node:fs";
import { parseArgs } from "node:util";
import Tupana, { APIError } from "tupana";
import { buildDocuments, clp, issueAll, readCsv } from "./bulk.js";

const { values, positionals } = parseArgs({
  allowPositionals: true,
  options: {
    "issuer-rut": { type: "string", default: process.env.TUPANA_ISSUER_RUT },
    emit: { type: "boolean", default: false },
    results: { type: "string", default: "results.csv" },
  },
});

const file = positionals[0];
if (!file || !values["issuer-rut"]) {
  console.error("Uso: node issue-from-csv.js <archivo.csv> --issuer-rut <RUT> [--emit]");
  process.exit(2);
}

const docs = buildDocuments(readCsv(readFileSync(file, "utf8")), values["issuer-rut"]);
console.log(`${docs.length} documento(s) en ${file}:`);
for (const d of docs) {
  const net = d.details.reduce((sum, it) => sum + it.quantity * it.unit_price, 0);
  console.log(
    `  ${d.json_param.external_ref.padEnd(12)} DTE ${d.dte_type.code.padEnd(3)} → ${d.document_receiver.rut.padEnd(12)} ${d.details.length} línea(s), neto ${clp(net)}`,
  );
}

if (!values.emit) {
  console.log("\nModo prueba: no se emitió nada. Agrega --emit para emitir.");
  process.exit(0);
}

try {
  const results = await issueAll(new Tupana(), docs);
  const header = "ref,status,folio,document_id,pdf_url";
  const lines = results.map((r) => [r.ref, r.status, r.folio, r.document_id, r.pdf_url].join(","));
  writeFileSync(values.results, `${[header, ...lines].join("\n")}\n`);
  console.log(`\nResultados en ${values.results}`);
} catch (err) {
  if (err instanceof APIError) {
    console.error(`Error ${err.status} (${err.code}): ${err.message} [request_id ${err.requestId}]`);
    process.exit(1);
  }
  throw err;
}
