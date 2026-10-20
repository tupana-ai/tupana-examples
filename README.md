# Ejemplos de Tupana

Ejemplos listos para correr de la [API de Tupana](https://docs.tupana.ai): facturación electrónica ante el SII, links de pago, webhooks y agentes de IA. Usan los SDKs oficiales de [Node.js](https://github.com/tupana-ai/tupana-node) y [Python](https://github.com/tupana-ai/tupana-python).

| Ejemplo | Stack | Qué muestra |
| --- | --- | --- |
| [`nextjs-invoice`](nextjs-invoice) | Next.js (App Router) | Ruta de API que emite una factura con `Idempotency-Key`, consulta de estado y receptor de webhooks. |
| [`bulk-issue-node`](bulk-issue-node) | Node.js | Emisión masiva desde CSV en lotes de 200, idempotente y con modo prueba. |
| [`bulk-issue-python`](bulk-issue-python) | Python | Lo mismo desde Excel (`.xlsx`) o CSV. |
| [`webhook-express`](webhook-express) | Express | Receptor de webhooks con verificación de `X-Pana-Signature` y deduplicación. |
| [`webhook-fastapi`](webhook-fastapi) | FastAPI | El mismo receptor en Python. |
| [`payment-link`](payment-link) | Node.js | Link de pago que emite la boleta sola al pagarse. |
| [`ai-agent-mcp`](ai-agent-mcp) | Python + Claude | Agente que factura por el [MCP de Tupana](https://github.com/tupana-ai/tupana-mcp) y **pide tu confirmación antes de emitir**. Incluye variante con OpenAI Agents SDK. |

## Antes de empezar

1. Crea tu cuenta y tus API keys en [developers.tupana.ai](https://developers.tupana.ai). Tienes una key de **sandbox** (no emite al SII ni mueve dinero) y una de **producción**; el código es el mismo.
2. Conecta la empresa emisora con sus credenciales del SII (Tupana Connect).
3. Exporta la key: `export TUPANA_API_KEY="..."`.

Los SDKs oficiales están publicados en npm y PyPI:

```bash
npm install tupana
pip install tupana
```

## Buenas prácticas que verás en todos

- **Idempotencia:** cada emisión lleva un `Idempotency-Key` estable (el id de tu pedido o un hash del lote). Reintentar nunca emite dos veces.
- **Asíncrono:** la emisión al SII sigue en segundo plano. Usa webhooks en producción; el polling queda para scripts.
- **Webhooks seguros:** verifica la firma sobre el cuerpo crudo y deduplica por `X-Pana-Event-Id`.
- **Nada irreversible sin un humano:** los scripts de emisión masiva parten en modo prueba y el agente de IA pide confirmación explícita.

## Recursos

- Documentación: [docs.tupana.ai](https://docs.tupana.ai)
- Portal de desarrolladores: [developers.tupana.ai](https://developers.tupana.ai)
- Servidor MCP: [github.com/tupana-ai/tupana-mcp](https://github.com/tupana-ai/tupana-mcp) (`https://mcp.tupana.ai/mcp`)

## Licencia

[MIT](LICENSE)

---

## English summary

Runnable examples for the [Tupana API](https://docs.tupana.ai) (Chilean electronic invoicing): a Next.js route that issues an invoice, bulk issuing from CSV/Excel (Node and Python), webhook receivers (Express and FastAPI) with signature verification, a payment-link flow, and an AI agent that invoices through the Tupana MCP server (`https://mcp.tupana.ai/mcp`) with the Claude API — always asking the human to confirm before issuing — plus an OpenAI Agents SDK variant.
