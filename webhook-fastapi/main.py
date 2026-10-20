"""Receptor de webhooks de Tupana con FastAPI.

Verifica X-Pana-Signature (HMAC SHA-256 del cuerpo crudo), descarta entregas
repetidas por X-Pana-Event-Id y despacha según el tipo de evento.

    export TUPANA_WEBHOOK_SECRET=...
    uvicorn main:app --port 8000
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from tupana import WebhookVerificationError, construct_webhook_event

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("tupana-webhooks")

app = FastAPI(title="Receptor de webhooks de Tupana")

# En producción guarda los ids procesados en tu base de datos (con índice único).
_processed_event_ids: set[str] = set()


def on_document_issued(data: dict[str, Any]) -> None:
    log.info("Documento emitido: folio %s, PDF %s", data.get("folio"), data.get("pdf_file"))


def on_document_rejected(data: dict[str, Any]) -> None:
    log.warning("El SII rechazó el documento %s", data.get("id"))


def on_payment_paid(data: dict[str, Any]) -> None:
    log.info(
        "Cobro %s pagado (external_id=%s)", data.get("payment_request_id"), data.get("external_id")
    )


HANDLERS: dict[str, Callable[[dict[str, Any]], None]] = {
    "document.issued": on_document_issued,
    "document.rejected": on_document_rejected,
    "payment_request.paid": on_payment_paid,
}


@app.post("/webhooks/tupana")
async def tupana_webhook(request: Request) -> dict[str, Any]:
    secret = os.environ["TUPANA_WEBHOOK_SECRET"]
    try:
        # Cuerpo CRUDO: re-serializar el JSON cambiaría los bytes y la firma no calzaría.
        event = construct_webhook_event(await request.body(), request.headers, secret)
    except WebhookVerificationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    event_id = request.headers.get("X-Pana-Event-Id", "")
    if event_id and event_id in _processed_event_ids:
        return {"ok": True, "duplicate": True}

    handler = HANDLERS.get(str(event.get("event")))
    if handler:
        handler(event.get("data") or {})
    else:
        log.info("Evento sin handler: %s", event.get("event"))

    if event_id:
        _processed_event_ids.add(event_id)
    # Responde rápido (2xx): si necesitas trabajo pesado, encólalo.
    return {"ok": True}
