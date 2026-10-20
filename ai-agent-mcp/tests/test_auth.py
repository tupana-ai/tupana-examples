"""Prueba el almacenamiento de tokens y el callback local del login OAuth (sin red externa)."""

from __future__ import annotations

import asyncio
import os
import stat
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp.shared.auth import OAuthToken  # noqa: E402

import tupana_mcp_auth  # noqa: E402


@pytest.mark.anyio
async def test_token_storage_roundtrip(tmp_path: Path) -> None:
    storage = tupana_mcp_auth.FileTokenStorage(tmp_path / "oauth.json")
    assert await storage.get_tokens() is None
    await storage.set_tokens(OAuthToken(access_token="abc", token_type="Bearer", expires_in=3600))
    tokens = await storage.get_tokens()
    assert tokens is not None and tokens.access_token == "abc"
    mode = stat.S_IMODE(os.stat(tmp_path / "oauth.json").st_mode)
    assert mode == 0o600


@pytest.mark.anyio
async def test_local_callback_captures_code(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tupana_mcp_auth, "CALLBACK_PORT", 8799)
    monkeypatch.setattr(tupana_mcp_auth.webbrowser, "open", lambda url: True)
    callback = tupana_mcp_auth._LocalCallback()
    await callback.open_browser("https://mcp.tupana.ai/authorize?x=1")
    reader, writer = await asyncio.open_connection("127.0.0.1", 8799)
    writer.write(b"GET /callback?code=CODE123&state=st HTTP/1.1\r\nHost: localhost\r\n\r\n")
    await writer.drain()
    assert b"200 OK" in await reader.read()
    result = await callback.wait_for_code()
    assert result.code == "CODE123"
    assert result.state == "st"


def test_build_oauth_metadata() -> None:
    provider = tupana_mcp_auth.build_oauth()
    meta = provider.context.client_metadata
    assert [str(u) for u in meta.redirect_uris or []] == [tupana_mcp_auth.REDIRECT_URI]
    assert meta.scope == "tupana:read tupana:write"


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
