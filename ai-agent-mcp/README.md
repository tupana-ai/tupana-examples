# Agente que factura con confirmación humana (MCP + Claude)

Un agente de terminal que conversa contigo, consulta tu facturación en Tupana y prepara facturas usando el [servidor MCP de Tupana](https://github.com/tupana-ai/tupana-mcp) (`https://mcp.tupana.ai/mcp`) y la API de Claude (`claude-sonnet-5-5`).

**Nunca emite ni modifica nada sin tu "sí".** El agente ejecuta él mismo cada herramienta que pide el modelo y aplica una política de *deny by default*:

- Las herramientas de solo lectura (consultar documentos, clientes, reportes, vista previa…) corren directo.
- Cualquier otra (crear borradores, `emit_document`, enviar correos, conciliar, asientos…) muestra la llamada con sus argumentos y espera que escribas `si`. Si el servidor agrega una herramienta nueva, también pide confirmación.
- La emisión al SII es un paso aparte: borrador → vista previa en PDF → `emit_document` solo cuando lo autorizas.

```
Tú: Hazle una factura a 76.123.456-7 por 2 horas de asesoría a $45.000 + IVA

⚠️  Acción que modifica datos
Herramienta: create_sale_invoice
Argumentos:
{ "receiver_rut": "76123456-7", "items": [{"name": "Asesoría", "quantity": 2, "unit_price": 45000}], ... }
¿Confirmas? Escribe 'si' para continuar: si

Agente: Dejé el borrador listo: neto $90.000, IVA $17.100, total $107.100.
Vista previa: https://... ¿Lo emito al SII?

Tú: sí, emítelo

⚠️  EMISIÓN AL SII (irreversible: el documento queda emitido con folio)
Herramienta: emit_document
...
```

## Requisitos

- Python 3.10+
- Una cuenta de Tupana con al menos una empresa conectada ([developers.tupana.ai](https://developers.tupana.ai)).
- Una API key de Anthropic ([console.anthropic.com](https://console.anthropic.com)).

## Correr

```bash
cd ai-agent-mcp
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY="sk-ant-..."
python agent.py
```

La primera vez se abre el navegador para que inicies sesión en Tupana y autorices al agente (OAuth 2.1 con PKCE y registro dinámico de cliente). El callback llega a `http://127.0.0.1:8765/callback` y los tokens quedan en `~/.config/tupana-agent/oauth.json` (permisos `600`); las siguientes veces se reutilizan y se refrescan solos. Para cerrar la sesión, borra ese archivo.

Variables opcionales:

| Variable | Por defecto |
| --- | --- |
| `TUPANA_AGENT_MODEL` | `claude-sonnet-5-5` |
| `TUPANA_MCP_URL` | `https://mcp.tupana.ai/mcp` |
| `TUPANA_OAUTH_CALLBACK_PORT` | `8765` |
| `TUPANA_AGENT_HOME` | `~/.config/tupana-agent` |

## Variante con OpenAI Agents SDK

`openai_agent.py` usa el mismo MCP, el mismo login y la misma política de confirmación con el [OpenAI Agents SDK](https://github.com/openai/openai-agents-python): `require_approval` pausa la corrida en cada herramienta que no es de solo lectura y el script te pregunta antes de aprobarla.

```bash
pip install -r requirements-openai.txt
export OPENAI_API_KEY="sk-..."
python openai_agent.py
```

## Cómo está armado

| Archivo | Qué hace |
| --- | --- |
| `agent.py` | Bucle de herramientas con la API de Claude: lista las herramientas del MCP, las pasa a Claude, ejecuta las llamadas y devuelve los resultados. |
| `confirmation.py` | Lista de herramientas de solo lectura, mensajes de confirmación y la respuesta que recibe el modelo cuando rechazas. |
| `tupana_mcp_auth.py` | Login OAuth: almacenamiento de tokens y servidor local para el callback. |
| `openai_agent.py` | La variante con OpenAI Agents SDK. |
| `tests/` | Pruebas con un servidor MCP en proceso y un modelo simulado (no llaman a Tupana ni a Anthropic). |

```bash
pip install -r requirements-dev.txt
pytest -q
```

¿Prefieres no escribir código? Conecta el mismo servidor en Claude, Claude Code, Cursor o ChatGPT siguiendo [tupana-ai/tupana-mcp](https://github.com/tupana-ai/tupana-mcp).
