"""Login OAuth 2.1 contra el servidor MCP de Tupana (https://mcp.tupana.ai/mcp).

El servidor usa OAuth 2.1 con PKCE y registro dinámico de clientes: la primera
vez se abre el navegador para que inicies sesión en Tupana y autorices; los
tokens quedan guardados en ``~/.config/tupana-agent/oauth.json`` (permisos 600)
y se refrescan solos en las siguientes ejecuciones.
"""

from __future__ import annotations

import asyncio
import json
import os
import webbrowser
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from mcp.client.auth import OAuthClientProvider, TokenStorage
from mcp.shared.auth import (
    AuthorizationCodeResult,
    OAuthClientInformationFull,
    OAuthClientMetadata,
    OAuthToken,
)

MCP_URL = os.environ.get("TUPANA_MCP_URL", "https://mcp.tupana.ai/mcp")
CALLBACK_PORT = int(os.environ.get("TUPANA_OAUTH_CALLBACK_PORT", "8765"))
REDIRECT_URI = f"http://127.0.0.1:{CALLBACK_PORT}/callback"
STORE = Path(os.environ.get("TUPANA_AGENT_HOME", Path.home() / ".config" / "tupana-agent"))

_SUCCESS_PAGE = (
    b"HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\nConnection: close\r\n\r\n"
    b"<html><body style='font-family:sans-serif'><h2>Listo, ya puedes volver a la terminal."
    b"</h2></body></html>"
)


class FileTokenStorage(TokenStorage):
    """Guarda tokens y el registro del cliente en un JSON local."""

    def __init__(self, path: Path = STORE / "oauth.json") -> None:
        self.path = path

    def _read(self) -> dict:
        try:
            return json.loads(self.path.read_text())
        except (FileNotFoundError, ValueError):
            return {}

    def _write(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data))
        os.chmod(self.path, 0o600)

    async def get_tokens(self) -> OAuthToken | None:
        raw = self._read().get("tokens")
        return OAuthToken.model_validate(raw) if raw else None

    async def set_tokens(self, tokens: OAuthToken) -> None:
        data = self._read()
        data["tokens"] = tokens.model_dump(mode="json", exclude_none=True)
        self._write(data)

    async def get_client_info(self) -> OAuthClientInformationFull | None:
        raw = self._read().get("client")
        return OAuthClientInformationFull.model_validate(raw) if raw else None

    async def set_client_info(self, client_info: OAuthClientInformationFull) -> None:
        data = self._read()
        data["client"] = client_info.model_dump(mode="json", exclude_none=True)
        self._write(data)


class _LocalCallback:
    """Servidor HTTP mínimo en 127.0.0.1 que recibe el ``?code=`` del redirect."""

    def __init__(self) -> None:
        self._result: asyncio.Future[AuthorizationCodeResult] | None = None
        self._server: asyncio.base_events.Server | None = None

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        request_line = (await reader.readline()).decode(errors="replace")
        parts = request_line.split(" ")
        query = parse_qs(urlparse(parts[1]).query) if len(parts) > 1 else {}
        writer.write(_SUCCESS_PAGE)
        await writer.drain()
        writer.close()
        if self._result and not self._result.done():
            if "code" in query:
                self._result.set_result(
                    AuthorizationCodeResult(
                        code=query["code"][0],
                        state=query.get("state", [None])[0],
                        iss=query.get("iss", [None])[0],
                    )
                )
            else:
                error = query.get("error", ["sin código"])[0]
                self._result.set_exception(RuntimeError(f"Autorización rechazada: {error}"))

    async def open_browser(self, authorization_url: str) -> None:
        self._result = asyncio.get_running_loop().create_future()
        self._server = await asyncio.start_server(self._handle, "127.0.0.1", CALLBACK_PORT)
        print(
            f"\nAbre este link para conectar Tupana (si no se abrió solo):\n{authorization_url}\n"
        )
        webbrowser.open(authorization_url)

    async def wait_for_code(self) -> AuthorizationCodeResult:
        assert self._result is not None, "open_browser debe llamarse primero"
        try:
            return await asyncio.wait_for(self._result, timeout=300)
        finally:
            if self._server:
                self._server.close()


def build_oauth() -> OAuthClientProvider:
    """``httpx2.Auth`` listo para pasarle al transporte Streamable HTTP del MCP."""
    callback = _LocalCallback()
    return OAuthClientProvider(
        server_url=MCP_URL,
        client_metadata=OAuthClientMetadata(
            client_name="Tupana agent example",
            redirect_uris=[REDIRECT_URI],
            grant_types=["authorization_code", "refresh_token"],
            response_types=["code"],
            scope="tupana:read tupana:write",
            token_endpoint_auth_method="client_secret_post",
        ),
        storage=FileTokenStorage(),
        redirect_handler=callback.open_browser,
        callback_handler=callback.wait_for_code,
    )
