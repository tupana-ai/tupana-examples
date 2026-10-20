# Emisión masiva desde Excel o CSV (Python)

Lee un `.xlsx` (primera hoja) o un `.csv` donde cada fila es una línea de detalle, agrupa por `ref` y emite en lotes de hasta 200 documentos con el [SDK de Python](https://github.com/tupana-ai/tupana-python).

- **Modo prueba por defecto:** sin `--emit` solo valida el archivo y muestra el resumen; no llama a la API.
- **Seguro de reintentar:** cada lote viaja con un `Idempotency-Key` derivado de su contenido; volver a correr el mismo archivo no emite de nuevo.
- Guarda `ref` en `json_param.external_ref` y escribe `results.csv` con estado, folio, id y PDF.

## Formato

Mismas columnas que la [versión en Node](../bulk-issue-node#formato-del-csv): `ref`, `dte_type`, `receiver_rut`, `item_name`, `quantity`, `unit_price` y opcionales `item_description`, `due_date`. Los montos pueden venir como `49990`, `49.990` o `49.990,5`.

## Correr

```bash
cd bulk-issue-python
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export TUPANA_API_KEY="tu-api-key"        # empieza con la de sandbox
python issue_from_file.py invoices.csv --issuer-rut 76543210-3            # prueba
python issue_from_file.py facturas.xlsx --issuer-rut 76543210-3 --emit    # emite
```

Pruebas (sin llamar a la API):

```bash
pip install -r requirements-dev.txt
pytest -q
```
