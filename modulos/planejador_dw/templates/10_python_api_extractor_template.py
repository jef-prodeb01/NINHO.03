"""
==============================================================================
TEMPLATE PYTHON: EXTRATOR DE API REST -> CSV (Apache Hop) ou STAGING ORACLE
==============================================================================
Fonte única: modulos/planejador_dw/templates/10_python_api_extractor_template.py
(cópia sincronizada em .agents/skills/extrator-api-python/templates/, verificada
por tests/test_templates_sincronizados.py)

Contrato da skill `extrator-api-python`:
  - Autenticação OAuth2 client_credentials (API_CLIENT_ID/SECRET) ou Bearer fixo (API_TOKEN).
  - Credenciais SÓ por variável de ambiente, sem valor padrão.
  - Paginação por offset com retentativa e backoff exponencial (429/5xx/rede).
  - Flatten de JSON aninhado e deduplicação pela chave de negócio.
  - Destino CSV: escrita atômica (<arquivo>.csv.tmp -> os.replace), `;` e utf-8-sig;
    registros inválidos em <arquivo>_REJEITADOS.csv com MOTIVO_REJEICAO.
  - Destino Oracle: executemany em lotes na STG com ID_LOTE e DTC_EXTRACAO.
  - Última linha do stdout para o Hop: STATUS:SUCCESS|rows=<N>|output=<destino>
    ou STATUS:ERROR|reason=<msg> com exit code 1.

Ajuste os pontos marcados com <...> (endpoint, campos, tabela STG).
==============================================================================
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stderr,  # stdout fica reservado para a linha STATUS do Hop
)
logger = logging.getLogger("ETL_API_EXTRACTOR")

ENDPOINT = "<recurso>"                         # ex.: "entidades"
CHAVE_NEGOCIO = "ID_<ENTIDADE>"                # coluna usada na deduplicação
CAMPOS_OBRIGATORIOS = ("ID_<ENTIDADE>", "DATA_<EVENTO>")
TARGET_STG_TABLE = "STG_<SISTEMA>_<DOMINIO>_<ENTIDADE>"
TAMANHO_PAGINA = int(os.getenv("API_PAGE_SIZE", "100"))


class ConfiguracaoInvalida(RuntimeError):
    pass


def variavel_obrigatoria(nome: str) -> str:
    """Lê uma configuração/credencial do ambiente; segredos nunca têm valor padrão."""
    valor = os.getenv(nome, "").strip()
    if not valor:
        raise ConfiguracaoInvalida(f"variável de ambiente obrigatória ausente: {nome}")
    return valor


# ----------------------------------------------------------------------------
# Cliente HTTP (biblioteca padrão) com OAuth2/Bearer e retentativa
# ----------------------------------------------------------------------------
class ApiClient:
    def __init__(self, timeout: float = 60.0):
        self.base_url = variavel_obrigatoria("API_BASE_URL").rstrip("/")
        self.timeout = timeout
        self._token_fixo = os.getenv("API_TOKEN", "").strip()
        self._token: Optional[str] = None
        self._expira_em = 0.0

    def _requisitar(self, req: urllib.request.Request) -> Dict[str, Any]:
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def token(self) -> str:
        if self._token_fixo:
            return self._token_fixo
        if self._token is None or time.monotonic() >= self._expira_em - 60:
            corpo = urllib.parse.urlencode({
                "grant_type": "client_credentials",
                "client_id": variavel_obrigatoria("API_CLIENT_ID"),
                "client_secret": variavel_obrigatoria("API_CLIENT_SECRET"),
            }).encode()
            req = urllib.request.Request(variavel_obrigatoria("API_AUTH_URL"), data=corpo, method="POST")
            payload = self._requisitar(req)
            self._token = payload["access_token"]
            self._expira_em = time.monotonic() + float(payload.get("expires_in", 900))
            logger.info("Token OAuth2 renovado.")
        return self._token

    def get(self, recurso: str, params: Dict[str, Any], tentativas: int = 4) -> Dict[str, Any]:
        url = f"{self.base_url}/{recurso.lstrip('/')}?{urllib.parse.urlencode(params)}"
        for tentativa in range(1, tentativas + 1):
            req = urllib.request.Request(url, headers={"Authorization": f"Bearer {self.token()}", "Accept": "application/json"})
            try:
                return self._requisitar(req)
            except urllib.error.HTTPError as exc:
                if exc.code not in (429, 500, 502, 503, 504) or tentativa == tentativas:
                    raise
                motivo = f"HTTP {exc.code}"
            except urllib.error.URLError as exc:
                if tentativa == tentativas:
                    raise
                motivo = str(exc.reason)
            espera = 2 ** tentativa
            logger.warning("%s em %s; nova tentativa em %ds (%d/%d).", motivo, recurso, espera, tentativa, tentativas)
            time.sleep(espera)
        raise RuntimeError(f"Falha ao consultar {url}")


# ----------------------------------------------------------------------------
# Transformação
# ----------------------------------------------------------------------------
def flatten(d: Dict[str, Any], prefixo: str = "", sep: str = "_") -> Dict[str, Any]:
    """Achata JSON aninhado; listas de valores viram texto separado por vírgula."""
    plano: Dict[str, Any] = {}
    for chave, valor in d.items():
        nome = f"{prefixo}{sep}{chave}" if prefixo else chave
        if isinstance(valor, dict):
            plano.update(flatten(valor, nome, sep))
        elif isinstance(valor, list):
            plano[nome] = json.dumps(valor, ensure_ascii=False) if valor and isinstance(valor[0], dict) else ", ".join(map(str, valor))
        else:
            plano[nome] = valor
    return plano


def mapear_registro(item: Dict[str, Any], id_lote: int) -> Dict[str, Any]:
    """<AJUSTE> De/para do JSON da API para as colunas da STG."""
    plano = flatten(item)
    return {
        "ID_<ENTIDADE>": plano.get("id"),
        "DATA_<EVENTO>": plano.get("date"),
        "NOME_<ENTIDADE>": (plano.get("description") or "")[:200],
        "VAL_<VALOR_1>": plano.get("amount"),
        "ID_LOTE": id_lote,
    }


def validar(registro: Dict[str, Any]) -> Optional[str]:
    vazios = [c for c in CAMPOS_OBRIGATORIOS if registro.get(c) in (None, "")]
    return f"campo(s) obrigatório(s) vazio(s): {', '.join(vazios)}" if vazios else None


def extrair(client: ApiClient, inicio: str, fim: str, id_lote: int) -> Iterator[Dict[str, Any]]:
    offset = 0
    while True:
        dados = client.get(ENDPOINT, {"start_date": inicio, "end_date": fim, "offset": offset, "limit": TAMANHO_PAGINA})
        itens = dados.get("data", [])
        logger.info("Página offset=%d: %d registro(s).", offset, len(itens))
        for item in itens:
            yield mapear_registro(item, id_lote)
        if len(itens) < TAMANHO_PAGINA:
            return
        offset += TAMANHO_PAGINA


def separar(registros: Iterator[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Separa válidos e rejeitados; duplicatas da chave de negócio vão para rejeitados."""
    validos: List[Dict[str, Any]] = []
    rejeitados: List[Dict[str, Any]] = []
    vistos = set()
    for reg in registros:
        motivo = validar(reg)
        chave = reg.get(CHAVE_NEGOCIO)
        if motivo is None and chave in vistos:
            motivo = f"chave de negócio duplicada no lote: {chave}"
        if motivo:
            rejeitados.append({**reg, "MOTIVO_REJEICAO": motivo})
            continue
        vistos.add(chave)
        validos.append(reg)
    return validos, rejeitados


# ----------------------------------------------------------------------------
# Destinos
# ----------------------------------------------------------------------------
def gravar_csv_atomico(caminho: Path, linhas: List[Dict[str, Any]]) -> None:
    """Grava em <arquivo>.tmp e troca no final: o Hop nunca lê arquivo parcial."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    temporario = caminho.with_name(caminho.name + ".tmp")
    colunas = list(linhas[0].keys()) if linhas else [CHAVE_NEGOCIO]
    with temporario.open("w", encoding="utf-8-sig", newline="") as arq:
        escritor = csv.DictWriter(arq, fieldnames=colunas, delimiter=";")
        escritor.writeheader()
        escritor.writerows(linhas)
    os.replace(temporario, caminho)


def carregar_oracle(linhas: List[Dict[str, Any]], lote: int = 1000) -> None:
    import oracledb  # pip install oracledb (necessário só para --destino oracle)

    colunas = [c for c in linhas[0].keys()] if linhas else []
    sql = (
        f"INSERT INTO {TARGET_STG_TABLE} ({', '.join(colunas)}, DTC_EXTRACAO) "
        f"VALUES ({', '.join(':' + c for c in colunas)}, SYSDATE)"
    )
    with oracledb.connect(
        user=variavel_obrigatoria("ORACLE_USER"),
        password=variavel_obrigatoria("ORACLE_PASS"),
        dsn=variavel_obrigatoria("ORACLE_DSN"),
    ) as conexao:
        with conexao.cursor() as cursor:
            for i in range(0, len(linhas), lote):
                cursor.executemany(sql, linhas[i:i + lote])
                conexao.commit()
                logger.info("Gravadas %d/%d linhas em %s.", min(i + lote, len(linhas)), len(linhas), TARGET_STG_TABLE)


def main() -> int:
    parser = argparse.ArgumentParser(description="Extrator de API REST para CSV (Hop) ou Staging Oracle.")
    parser.add_argument("--start-date", default=(date.today() - timedelta(days=1)).isoformat())
    parser.add_argument("--end-date", default=date.today().isoformat())
    parser.add_argument("--destino", choices=("csv", "oracle"), default="csv")
    parser.add_argument("--saida", default=os.getenv("ENV_DIR_DEST", "./entrada") + "/<ENTIDADE>.csv",
                        help="Arquivo CSV de saída (destino csv).")
    parser.add_argument("--dry-run", action="store_true", help="Extrai e valida sem gravar.")
    args = parser.parse_args()

    try:
        id_lote = int(datetime.now().strftime("%Y%m%d%H%M%S"))
        validos, rejeitados = separar(extrair(ApiClient(), args.start_date, args.end_date, id_lote))
        logger.info("Lote %d: %d válido(s), %d rejeitado(s).", id_lote, len(validos), len(rejeitados))

        saida = Path(args.saida)
        if rejeitados and not args.dry_run:
            gravar_csv_atomico(saida.with_name(saida.stem + "_REJEITADOS.csv"), rejeitados)
        if args.dry_run:
            destino = "dry-run"
        elif args.destino == "csv":
            gravar_csv_atomico(saida, validos)
            destino = str(saida)
        else:
            carregar_oracle(validos)
            destino = TARGET_STG_TABLE
        print(f"STATUS:SUCCESS|rows={len(validos)}|rejected={len(rejeitados)}|output={destino}")
        return 0
    except Exception as exc:  # o Hop decide o fluxo pelo exit code + linha STATUS
        logger.critical("Falha na extração: %s", exc, exc_info=not isinstance(exc, ConfiguracaoInvalida))
        print(f"STATUS:ERROR|reason={str(exc).replace('|', '/')}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
