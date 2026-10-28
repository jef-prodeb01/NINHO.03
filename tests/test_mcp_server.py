"""Servidor MCP do NINHO: handshake, listagem e chamada de ferramenta via stdio."""

import json
import subprocess
import sys

from ninho_core.paths import BASE_DIR


def _conversar(*mensagens) -> list:
    entrada = "\n".join(json.dumps(m) for m in mensagens) + "\n"
    proc = subprocess.run(
        [sys.executable, str(BASE_DIR / "ninho_mcp_server.py")], input=entrada, capture_output=True,
        text=True, encoding="utf-8", timeout=120, cwd=str(BASE_DIR),
    )
    return [json.loads(linha) for linha in proc.stdout.splitlines() if linha.strip()]


def test_handshake_lista_e_chamada():
    respostas = _conversar(
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05"}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "duvida", "arguments": {"argumentos": "rls"}}},
        {"jsonrpc": "2.0", "id": 4, "method": "metodo/inexistente"},
    )
    por_id = {r["id"]: r for r in respostas}
    assert set(por_id) == {1, 2, 3, 4}, "notificação não deve gerar resposta"
    assert por_id[1]["result"]["serverInfo"]["name"] == "ninho"
    nomes = {t["name"] for t in por_id[2]["result"]["tools"]}
    assert {"executar_governanca", "simular_dw", "gerar_rls", "duvida"} <= nomes
    texto = por_id[3]["result"]["content"][0]["text"]
    assert por_id[3]["result"]["isError"] is False and "RLS_CONTAS_SERVICO" in texto
    assert por_id[4]["error"]["code"] == -32601
