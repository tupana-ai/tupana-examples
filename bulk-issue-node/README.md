# Emisión masiva desde CSV (Node.js)

Lee un CSV donde cada fila es una línea de detalle, agrupa por `ref` (un documento por `ref`), y emite en lotes de hasta 200 documentos con [`tupana`](https://github.com/tupana-ai/tupana-node).

- **Modo prueba por defecto:** sin `--emit` solo valida el archivo y muestra el resumen; no llama a la API.
- **Seguro de reintentar:** cada lote viaja con un `Idempotency-Key` derivado de su contenido. Si el script se corta y lo vuelves a correr con el mismo archivo, Tupana devuelve el lote original en vez de emitir de nuevo.
- Guarda `ref` en `json_param.external_ref`, para reencontrar cada documento con `documents.list({ master_entity_id, json_param: { external_ref } })`.
- Escribe `results.csv` con estado, folio, id y PDF de cada documento.

## Formato del CSV

| Columna | Obligatoria | Ejemplo |
| --- | --- | --- |
| `ref` | sí | `PED-1001` (las filas con el mismo `ref` forman un documento) |
| `dte_type` | sí | `33` factura, `34` factura exenta, `39` boleta… |
| `receiver_rut` | sí | `76123456-0` |
| `item_name` | sí | `Plan Pro mensual` |
| `quantity` | sí | `1` |
| `unit_price` | sí | `49990` o `49.990` (neto, sin IVA) |
| `item_description` | no | `Octubre 2026` |
| `due_date` | no | `2026-11-30` |

Se aceptan comas o punto y coma como separador. Mira [`invoices.csv`](invoices.csv).

## Correr

```bash
cd bulk-issue-node
npm install
export TUPANA_API_KEY="tu-api-key"        # empieza con la de sandbox
node issue-from-csv.js invoices.csv --issuer-rut 76543210-3          # prueba
node issue-from-csv.js invoices.csv --issuer-rut 76543210-3 --emit   # emite
npm test
```

¿Excel? La versión en Python ([`../bulk-issue-python`](../bulk-issue-python)) lee `.xlsx` directamente.
