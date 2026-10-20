# Receptor de webhooks con FastAPI

Lo mismo que el [ejemplo de Express](../webhook-express), en Python:

- `await request.body()` para tener el cuerpo **crudo**.
- `construct_webhook_event` del [SDK de Python](https://github.com/tupana-ai/tupana-python) verifica `X-Pana-Signature` (HMAC SHA-256 en hex) y parsea el evento; si la firma no calza responde `400`.
- Deduplica por `X-Pana-Event-Id` y despacha según `event`.

## Correr

```bash
cd webhook-fastapi
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export TUPANA_WEBHOOK_SECRET="un-secreto-largo"
uvicorn main:app --port 8000
```

Pruebas:

```bash
pip install -r requirements-dev.txt
pytest -q
```
