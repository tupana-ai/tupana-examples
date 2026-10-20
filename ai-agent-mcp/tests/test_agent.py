"""Prueba el bucle del agente contra un servidor MCP en proceso y un Claude simulado.

No llama a Tupana ni a la API de Anthropic.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from mcp import Client
from mcp.server.mcpserver import MCPServer

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent import InvoicingAgent, mcp_tools_to_claude  # noqa: E402
from confirmation import DECLINED_MESSAGE, needs_confirmation  # noqa: E402

emitted: list[str] = []
server = MCPServer("fake-tupana")


@server.tool()
def get_entity_info() -> str:
    """Empresas del usuario."""
    return "ACME SpA (76.543.210-K)"


@server.tool()
def emit_document(document_id: str) -> str:
    """Emite un borrador al SII."""
    emitted.append(document_id)
    return f"Documento {document_id} emitido con folio 1234"


def _tool_use(id_: str, name: str, args: dict[str, Any]) -> Any:
    return SimpleNamespace(type="tool_use", id=id_, name=name, input=args)


def _text(text: str) -> Any:
    return SimpleNamespace(type="text", text=text)


class FakeClaude:
    """Devuelve respuestas guionadas y registra lo que recibe."""

    def __init__(self, script: list[Any]) -> None:
        self.script = script
        self.calls: list[dict[str, Any]] = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    async def _create(self, **kwargs: Any) -> Any:
        self.calls.append({**kwargs, "messages": list(kwargs["messages"])})
        return self.script.pop(0)


def _script() -> list[Any]:
    return [
        SimpleNamespace(
            stop_reason="tool_use",
            content=[
                _tool_use("t1", "get_entity_info", {}),
                _tool_use("t2", "emit_document", {"document_id": "docu_1"}),
            ],
        ),
        SimpleNamespace(stop_reason="end_turn", content=[_text("Listo.")]),
    ]


def test_policy_is_deny_by_default() -> None:
    assert not needs_confirmation("get_entity_info")
    assert needs_confirmation("emit_document")
    assert needs_confirmation("create_sale_invoice")
    assert needs_confirmation("una_herramienta_nueva")


@pytest.mark.anyio
async def test_declined_emission_is_not_executed() -> None:
    emitted.clear()
    asked: list[str] = []
    async with Client(server) as mcp:
        tools = mcp_tools_to_claude((await mcp.list_tools()).tools)
        claude = FakeClaude(_script())
        agent = InvoicingAgent(
            mcp, claude, tools, confirm=lambda name, args: asked.append(name) or False
        )  # type: ignore[arg-type]
        reply = await agent.send("emite la factura")
    assert reply == "Listo."
    assert asked == ["emit_document"]  # la lectura no pidió confirmación
    assert emitted == []
    results = claude.calls[1]["messages"][-1]["content"]
    assert results[0]["is_error"] is False and "ACME" in results[0]["content"]
    assert results[1] == {
        "type": "tool_result",
        "tool_use_id": "t2",
        "content": DECLINED_MESSAGE,
        "is_error": True,
    }


@pytest.mark.anyio
async def test_confirmed_emission_runs() -> None:
    emitted.clear()
    async with Client(server) as mcp:
        tools = mcp_tools_to_claude((await mcp.list_tools()).tools)
        claude = FakeClaude(_script())
        agent = InvoicingAgent(mcp, claude, tools, confirm=lambda name, args: True)  # type: ignore[arg-type]
        await agent.send("emite la factura")
    assert emitted == ["docu_1"]
    request = claude.calls[0]
    assert request["model"] == "claude-sonnet-5-5"
    assert {t["name"] for t in request["tools"]} == {"get_entity_info", "emit_document"}


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
