from __future__ import annotations

import sys
from pathlib import Path

import pytest
import respx
from openpyxl import Workbook

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import issue_from_file as bulk  # noqa: E402

HERE = Path(__file__).resolve().parent.parent


def test_groups_rows_into_documents() -> None:
    docs = bulk.build_documents(bulk.read_rows(HERE / "invoices.csv"), "76543210-3")
    assert [d["json_param"]["external_ref"] for d in docs] == ["PED-1001", "PED-1002", "PED-1003"]
    assert len(docs[0]["details"]) == 2
    assert docs[0]["header"] == {"due_date": "2026-11-30"}
    assert docs[2]["dte_type"] == {"code": "34"}


def test_reads_xlsx(tmp_path: Path) -> None:
    wb = Workbook()
    ws = wb.active
    ws.append(["ref", "dte_type", "receiver_rut", "item_name", "quantity", "unit_price"])
    ws.append(["A1", 33, "76123456-0", "Servicio", 1, 1000])
    wb.save(tmp_path / "f.xlsx")
    docs = bulk.build_documents(bulk.read_rows(tmp_path / "f.xlsx"), "76543210-3")
    assert docs[0]["details"][0]["unit_price"] == 1000


def test_idempotency_key_is_stable() -> None:
    docs = bulk.build_documents(bulk.read_rows(HERE / "invoices.csv"), "76543210-3")
    assert bulk.idempotency_key(docs) == bulk.idempotency_key(list(docs))
    assert bulk.idempotency_key(docs) != bulk.idempotency_key(docs[:1])


def test_dry_run_makes_no_requests(capsys: pytest.CaptureFixture[str]) -> None:
    with respx.mock(assert_all_called=False) as mock:
        assert bulk.main([str(HERE / "invoices.csv"), "--issuer-rut", "76543210-3"]) == 0
        assert not mock.calls
    assert "Modo prueba" in capsys.readouterr().out


def test_emit(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("TUPANA_API_KEY", "k")
    base = "https://api.tupana.ai/v2"
    with respx.mock(base_url=base) as mock:
        create = mock.post("/documents/batch/").respond(
            201, json={"batch_id": "b1", "documents": []}
        )
        mock.get("/documents/batch/b1/").respond(
            200,
            json={
                "id": "b1",
                "status": "completed",
                "documents": [
                    {"index": i, "status": "success", "document": {"folio": str(100 + i)}}
                    for i in range(3)
                ],
            },
        )
        out = tmp_path / "r.csv"
        code = bulk.main(
            [
                str(HERE / "invoices.csv"),
                "--issuer-rut",
                "76543210-3",
                "--emit",
                "--results",
                str(out),
            ]
        )
    assert code == 0
    assert create.calls.last.request.headers["idempotency-key"].startswith("bulk-")
    assert create.calls.last.request.headers["x-use-defaults"] == "true"
    assert "PED-1003,success,102" in out.read_text()


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("49990", 49990),
        ("49.990", 49990),
        ("1.234.567", 1234567),
        ("49990.5", 49990.5),
        ("49.990,5", 49990.5),
        ("12,5", 12.5),
        ("$ 5.990", 5990),
    ],
)
def test_number_formats(raw: str, expected: float) -> None:
    assert bulk._number(raw, "unit_price", 2) == expected
