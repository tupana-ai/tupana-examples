"""Variante con el OpenAI Agents SDK: el mismo MCP de Tupana y la misma confirmación humana.

El SDK pausa la corrida en cada herramienta que requiere aprobación
(`require_approval`); aquí se le muestra al usuario y se aprueba o rechaza.

Uso:
    export OPENAI_API_KEY=...
    python openai_agent.py
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any

from agent import SYSTEM_PROMPT
from agents import Agent, Runner
from agents.mcp import MCPServerStreamableHttp
from confirmation import DECLINED_MESSAGE, ask_human, needs_confirmation
from tupana_mcp_auth import MCP_URL, build_oauth

MODEL = os.environ.get("TUPANA_OPENAI_MODEL", "gpt-5")


def _requires_approval(_ctx: Any, _agent: Any, tool: Any) -> bool:
    return needs_confirmation(tool.name)


def _arguments(item: Any) -> dict[str, Any]:
    raw = item.arguments
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except ValueError:
            return {"raw": raw}
    return dict(raw or {})


async def main() -> None:
    async with MCPServerStreamableHttp(
        name="tupana",
        params={"url": MCP_URL, "auth": build_oauth(), "timeout": 30, "sse_read_timeout": 300},
        require_approval=_requires_approval,
        cache_tools_list=True,
    ) as tupana:
        agent = Agent(
            name="Asistente de facturación Tupana",
            instructions=SYSTEM_PROMPT,
            model=MODEL,
            mcp_servers=[tupana],
        )
        history: Any = []
        print("Conectado a Tupana MCP. Escribe 'salir' para terminar.\n")
        while True:
            try:
                text = input("Tú: ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not text:
                continue
            if text.lower() in {"salir", "exit", "quit"}:
                break
            result = await Runner.run(agent, [*history, {"role": "user", "content": text}])
            while result.interruptions:
                state = result.to_state()
                for item in result.interruptions:
                    if ask_human(item.tool_name or "?", _arguments(item)):
                        state.approve(item)
                    else:
                        state.reject(item, rejection_message=DECLINED_MESSAGE)
                result = await Runner.run(agent, state)
            history = result.to_input_list()
            print(f"\nAgente: {result.final_output}\n")


if __name__ == "__main__":
    asyncio.run(main())
