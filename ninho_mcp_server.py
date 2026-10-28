#!/usr/bin/env python3
"""
Servidor MCP (Model Context Protocol) do NINHO — só biblioteca padrão, transporte stdio.

Expõe cada comando de `ninho.py` como ferramenta tipada para qualquer agente MCP (Claude Code,
Cursor, Antigravity, agentes internos), sem depender de skills por IDE.

Configuração (ex.: `.mcp.json` na raiz do projeto):
    {"mcpServers": {"ninho": {"command": "python", "args": ["ninho_mcp_server.py"]}}}

Cada ferramenta recebe `argumentos` (texto, opcional) repassado ao comando. Ferramentas que
alteram arquivos em `saida/` ou `entrega/` são marcadas como não somente-leitura.
"""

import json
import shlex
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))
import ninho  # noqa: E402

VERSAO_PROTOCOLO = "2024-11-05"
SOMENTE_LEITURA = {
    "ajuda", "onde-estou", "duvida", "inspecionar-fontes", "inspecionar-pbix", "auditar-mapa-odi",
    "auditar-hop", "inspecionar-governanca", "validar-entrega", "estimar-volumetria",
}
TIMEOUT_SEGUNDOS = 600


def _ferramentas() -> list:
    ferramentas = []
    for cmd, descricao in ninho.DESCRICOES_SKILLS_SLASH.items():
        if cmd not in ninho.ROTAS_COMANDOS or cmd in ("instalar-comandos", "testar-ninho"):
            continue
        ferramentas.append({
            "name": cmd.replace("-", "_"),
            "description": descricao,
            "inputSchema": {
                "type": "object",
                "properties": {
                    "argumentos": {
                        "type": "string",
                        "description": "Argumentos opcionais do comando (ex.: caminho de arquivo, tema ou flags como --json).",
                    }
                },
            },
            "annotations": {"readOnlyHint": cmd in SOMENTE_LEITURA},
        })
    return ferramentas


def _executar_ferramenta(nome: str, argumentos: str) -> dict:
    cmd = nome.replace("_", "-")
    if cmd not in ninho.ROTAS_COMANDOS:
        return {"content": [{"type": "text", "text": f"Comando desconhecido: {cmd}"}], "isError": True}
    extras = shlex.split(argumentos or "", posix=True)
    proc = subprocess.run(
        [sys.executable, str(RAIZ / "ninho.py"), cmd, *extras],
        cwd=str(RAIZ), capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=TIMEOUT_SEGUNDOS, env={**__import__("os").environ, "NO_COLOR": "1"},
    )
    texto = proc.stdout.strip() or "(sem saída)"
    if proc.stderr.strip():
        texto += "\n\n[stderr]\n" + proc.stderr.strip()[-4000:]
    return {"content": [{"type": "text", "text": texto[-100_000:]}], "isError": proc.returncode not in (0,)}


def tratar(mensagem: dict):
    metodo, ident = mensagem.get("method"), mensagem.get("id")
    if ident is None:  # notificação (ex.: notifications/initialized): sem resposta
        return None
    try:
        if metodo == "initialize":
            resultado = {
                "protocolVersion": VERSAO_PROTOCOLO,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "ninho", "version": "0.13.0"},
            }
        elif metodo == "ping":
            resultado = {}
        elif metodo == "tools/list":
            resultado = {"tools": _ferramentas()}
        elif metodo == "tools/call":
            params = mensagem.get("params") or {}
            resultado = _executar_ferramenta(params.get("name", ""), (params.get("arguments") or {}).get("argumentos", ""))
        else:
            return {"jsonrpc": "2.0", "id": ident, "error": {"code": -32601, "message": f"Método não suportado: {metodo}"}}
        return {"jsonrpc": "2.0", "id": ident, "result": resultado}
    except Exception as exc:  # erro de ferramenta nunca derruba o servidor
        return {"jsonrpc": "2.0", "id": ident, "error": {"code": -32603, "message": str(exc)}}


def main() -> int:
    for linha in sys.stdin:
        linha = linha.strip()
        if not linha:
            continue
        try:
            resposta = tratar(json.loads(linha))
        except json.JSONDecodeError:
            resposta = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "JSON inválido"}}
        if resposta is not None:
            sys.stdout.write(json.dumps(resposta, ensure_ascii=False) + "\n")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stdin.reconfigure(encoding="utf-8")
    sys.exit(main())
