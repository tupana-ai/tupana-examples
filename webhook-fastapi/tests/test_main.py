from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from tupana import compute_webhook_signature

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import main  # noqa: E402

SECRET = "whsec_test"


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TUPANA_WEBHOOK_SECRET", SECRET)
    main._processed_event_ids.clear()


def _post(client: TestClient, body: str, signature: str, event_id: str = "evt_1"):
    return client.post(
        "/webhooks/tupana",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Pana-Signature": signature,
            "X-Pana-Event-Id": event_id,
            "X-Pana-Event-Type": "document.issued",
        },
    )


def test_valid_signature_and_dedup() -> None:
    body = json.dumps({"event": "document.issued", "data": {"folio": "1234"}})
    client = TestClient(main.app)
    first = _post(client, body, compute_webhook_signature(body, SECRET))
    assert first.status_code == 200 and first.json() == {"ok": True}
    again = _post(client, body, compute_webhook_signature(body, SECRET))
    assert again.json() == {"ok": True, "duplicate": True}


def test_invalid_signature_is_rejected() -> None:
    body = json.dumps({"event": "document.issued", "data": {}})
    response = _post(TestClient(main.app), body, "00" * 32)
    assert response.status_code == 400
