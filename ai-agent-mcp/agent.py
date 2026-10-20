"""Agente que factura con Tupana usando el MCP remoto y la API de Claude.

- Se conecta a https://mcp.tupana.ai/mcp con OAuth (se abre el navegador la primera vez).
- Le entrega a Claude las herramientas del MCP y ejecuta él mismo cada llamada.
- Antes de cualquier herramienta que no sea de solo lectura (crear borradores,
  emitir al SII, enviar correos, conciliar…) te muestra la llamada y espera tu "si".

Uso:
    export ANTHROPIC_API_KEY=...
    python agent.py
"""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Callable
from typing import Any

import anthropic
import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client

from confirmation import DECLINED_MESSAGE, ask_human, needs_confirmation
from tupana_mcp_auth import MCP_URL, build_oauth

MODEL = os.environ.get("TUPANA_AGENT_MODEL", "claude-sonnet-5-5")

SYSTEM_PROMPT = """Eres un asistente de facturación de una empresa chilena que usa Tupana.
Respondes en español de Chile, tuteando, breve y claro. Montos en pesos chilenos ($1.234.567).

Cómo facturar:
1. Identifica la empresa emisora (get_entity_info) y al cliente por RUT (find_clients o
   enrich_client_from_rut). Si falta un dato obligatorio (giro, dirección, comuna), pregúntalo.
2. Crea el BORRADOR (create_sale_invoice u otra herramienta create_*). Nunca emite.
3. Genera la vista previa (get_document_preview) y muéstrale al usuario el resumen y el link.
4. Solo cuando el usuario diga explícitamente que emita, llama a emit_document.

El sistema le pide confirmación al usuario antes de cada acción que modifica datos. Si el
usuario rechaza una acción, no la reintentes ni busques un camino alternativo: pregúntale qué
quiere cambiar. Nunca inventes RUTs, folios ni montos."""


def mcp_tools_to_claude(tools: list[Any]) -> list[dict[str, Any]]:
    """Convierte las herramientas MCP al formato de herramientas de la API de Claude."""
    return [
        {
            "name": tool.name,
            "description": (tool.description or "")[:4000],
            "input_schema": tool.input_schema or {"type": "object", "properties": {}},
        }
        for tool in tools
    ]


def tool_result_text(result: Any) -> str:
    """Aplana el contenido de un CallToolResult a texto para Claude."""
    parts: list[str] = []
    for block in result.content:
        text = getattr(block, "text", None)
        if text is not None:
            parts.append(text)
        else:
            parts.append(f"[{getattr(block, 'type', 'contenido')} omitido]")
    if not parts and getattr(result, "structured_content", None) is not None:
        parts.append(json.dumps(result.structured_content, ensure_ascii=False))
    return "\n".join(parts) or "(sin contenido)"


class InvoicingAgent:
    """Bucle de herramientas: Claude decide, el agente confirma con el humano y ejecuta."""

    def __init__(
        self,
        mcp: Any,
        claude: anthropic.AsyncAnthropic,
        tools: list[dict[str, Any]],
        confirm: Callable[[str, dict[str, Any]], bool] = ask_human,
        model: str = MODEL,
    ) -> None:
        self.mcp = mcp
        self.claude = claude
        self.tools = tools
        self.confirm = confirm
        self.model = model
        self.messages: list[dict[str, Any]] = []

    async def _run_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if needs_confirmation(name) and not self.confirm(name, arguments):
            return {"content": DECLINED_MESSAGE, "is_error": True}
        try:
            result = await self.mcp.call_tool(name, arguments)
        except Exception as exc:  # error de transporte o protocolo
            return {"content": f"Error llamando {name}: {exc}", "is_error": True}
        return {"content": tool_result_text(result), "is_error": bool(result.is_error)}

    async def send(self, user_text: str, max_steps: int = 25) -> str:
        """Agrega un mensaje del usuario y corre el bucle hasta la respuesta final."""
        self.messages.append({"role": "user", "content": user_text})
        for _ in range(max_steps):
            response = await self.claude.beta.messages.create(
                model=self.model,
                max_tokens=16000,
                system=SYSTEM_PROMPT,
                tools=self.tools,
                messages=self.messages,
                thinking={"type": "adaptive"},
                cache_control={"type": "ephemeral"},
                # Si un clasificador de seguridad declina, el servidor reintenta en el
                # modelo recomendado en vez de devolver la negativa.
                fallbacks="default",
                betas=["server-side-fallback-2026-07-01"],
            )
            # Se agrega el contenido completo (incluye bloques de thinking) para no romper
            # la continuidad del razonamiento entre turnos.
            self.messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "refusal":
                return "El modelo no pudo ayudar con esta solicitud."
            if response.stop_reason == "max_tokens":
                return "La respuesta se cortó por largo; intenta pedirlo en partes."
            if response.stop_reason == "pause_turn":
                continue
            tool_uses = [b for b in response.content if b.type == "tool_use"]
            if response.stop_reason != "tool_use" or not tool_uses:
                return "".join(b.text for b in response.content if b.type == "text").strip()

            # Todas las respuestas de herramientas van juntas en UN mensaje de usuario.
            results = []
            for block in tool_uses:
                outcome = await self._run_tool(block.name, dict(block.input or {}))
                results.append({"type": "tool_result", "tool_use_id": block.id, **outcome})
            self.messages.append({"role": "user", "content": results})
        return "Llegué al máximo de pasos sin terminar; revisa lo que alcancé a hacer."


async def main() -> None:
    claude = anthropic.AsyncAnthropic()
    http = httpx2.AsyncClient(auth=build_oauth(), timeout=httpx2.Timeout(30.0, read=300.0))
    async with http, Client(streamable_http_client(MCP_URL, http_client=http)) as mcp:
        listed = await mcp.list_tools()
        agent = InvoicingAgent(mcp, claude, mcp_tools_to_claude(listed.tools))
        print(f"Conectado a Tupana MCP ({len(agent.tools)} herramientas). 'salir' para terminar.")
        print("Ejemplo: Hazle una factura a 76.123.456-7 por 2 horas de asesoría a $45.000 + IVA\n")
        while True:
            try:
                text = input("Tú: ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not text:
                continue
            if text.lower() in {"salir", "exit", "quit"}:
                break
            reply = await agent.send(text)
            print(f"\nAgente: {reply}\n")


if __name__ == "__main__":
    asyncio.run(main())
