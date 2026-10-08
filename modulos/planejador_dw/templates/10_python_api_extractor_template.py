"""
==============================================================================
TEMPLATE PYTHON: EXTRATOR DE API REST PARA STAGING ORACLE (ENTERPRISE)
==============================================================================
Padrão Corporativo: Ingestão de APIs complexas com paginação e flattening.
Destino Oracle:     STG_<SISTEMA>_<DOMINIO>_<ENTIDADE>
Recursos:
  - Autenticação OAuth2 / Bearer Token com renovação automática de expiração.
  - Paginação automática por offset, cursor ou página.
  - Flattening de JSON hierárquico com estruturas aninhadas e listas.
  - Carga em lote (batch) no Oracle via oracledb (executemany).
  - Controle de retentativas com backoff exponencial para 429/503.
  - Auditoria com ID_LOTE e DTC_EXTRACAO.
==============================================================================
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import sys
import time
from datetime import date, datetime, timedelta
from typing import Any, Dict, Generator, List, Optional

# Requer: pip install httpx oracledb python-dotenv
try:
    import httpx
except ImportError:
    httpx = None  # type: ignore

try:
    import oracledb
except ImportError:
    oracledb = None  # type: ignore

# ----------------------------------------------------------------------------
# CONFIGURAÇÃO DE LOGGING CORPORATIVO
# ----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ETL_API_EXTRACTOR")

# ----------------------------------------------------------------------------
# CONSTANTES E CONFIGURAÇÕES DE AMBIENTE
# ----------------------------------------------------------------------------
API_BASE_URL = os.getenv("API_BASE_URL", "https://api.empresa.gov.br/v1")
AUTH_TOKEN_URL = os.getenv("API_AUTH_URL", "https://sso.empresa.gov.br/oauth/token")
CLIENT_ID = os.getenv("API_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("API_CLIENT_SECRET", "")

# Configurações do Banco Oracle Alvo
DB_USER = os.getenv("DW_ORACLE_USER", "<SCHEMA_ALVO>")
DB_PASSWORD = os.getenv("DW_ORACLE_PASS", "")
DB_DSN = os.getenv("DW_ORACLE_DSN", "localhost:1521/XEPDB1")
TARGET_STG_TABLE = "STG_<SISTEMA>_<DOMINIO>_<ENTIDADE>"


# ----------------------------------------------------------------------------
# CLIENTE HTTP RESILIENTE COM OAUTH2
# ----------------------------------------------------------------------------
class OAuth2ApiClient:
    """Cliente HTTP com gerenciamento transparente de tokens e retentativas."""

    def __init__(self, client_id: str, client_secret: str, timeout: float = 60.0):
        if httpx is None:
            raise RuntimeError("Biblioteca 'httpx' necessaria. Execute: pip install httpx")
        self.client_id = client_id
        self.client_secret = client_secret
        self.client = httpx.Client(timeout=httpx.Timeout(timeout, connect=15.0))
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0.0

    def get_token(self) -> str:
        """Obtem token Bearer com auto-refresh antes da expiracao."""
        agora = time.monotonic()
        if self._access_token is None or agora >= (self._token_expires_at - 60):
            logger.info("Obtendo novo token de acesso OAuth2...")
            response = self.client.post(
                AUTH_TOKEN_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
            )
            if response.status_code != 200:
                raise RuntimeError(f"Falha de autenticacao ({response.status_code}): {response.text}")

            payload = response.json()
            self._access_token = payload["access_token"]
            expires_in = float(payload.get("expires_in", 900))
            self._token_expires_at = agora + expires_in
            logger.info("Token OAuth2 renovado com sucesso (valido por %ds).", expires_in)
        return self._access_token

    def get_page(self, endpoint: str, params: Optional[Dict[str, Any]] = None, max_retries: int = 3) -> Dict[str, Any]:
        """Executa requisicao GET com tratamento de backoff exponencial."""
        url = f"{API_BASE_URL.rstrip('/')}/{endpoint.lstrip('/')}"
        token = self.get_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }

        for tentativa in range(1, max_retries + 1):
            try:
                response = self.client.get(url, headers=headers, params=params)
                if response.status_code == 200:
                    return response.json()
                elif response.status_code in (429, 502, 503, 504):
                    espera = 2 ** tentativa
                    logger.warning("Status %d recebido. Aguardando %ds (tentativa %d/%d)...",
                                   response.status_code, espera, tentativa, max_retries)
                    time.sleep(espera)
                else:
                    response.raise_for_status()
            except httpx.RequestError as exc:
                if tentativa == max_retries:
                    raise
                logger.warning("Erro de conexao: %s. Retentando em %ds...", exc, 2 ** tentativa)
                time.sleep(2 ** tentativa)

        raise RuntimeError(f"Falha ao consultar {url} apos {max_retries} tentativas.")


# ----------------------------------------------------------------------------
# UTILITÁRIOS DE TRATAMENTO DE DADOS (FLATTEN & ENRIQUECIMENTO)
# ----------------------------------------------------------------------------
def flatten_dict(d: Dict[str, Any], parent_key: str = "", sep: str = "_") -> Dict[str, Any]:
    """Achata um dicionario aninhado recursivamente em formato tabular 1D."""
    items: List[tuple[str, Any]] = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        elif isinstance(v, list):
            # Se for lista de valores simples, junta em string; se for lista de dicts, converte em str
            if v and isinstance(v[0], dict):
                items.append((new_key, str(v)))
            else:
                items.append((new_key, ", ".join(str(x) for x in v)))
        else:
            items.append((new_key, v))
    return dict(items)


def extrai_sigla_padrao(texto: Optional[str]) -> str:
    """Aplica regex para derivar siglas ou codigos de negocio."""
    if not texto:
        return "N/I"
    match = re.search(r"\b([A-Z]{2,10})\b", texto.upper())
    return match.group(1) if match else "N/I"


# ----------------------------------------------------------------------------
# MOTOR DE CARGA NO BANCO DE DADOS ORACLE (STAGING)
# ----------------------------------------------------------------------------
class OracleStagingLoader:
    """Gerencia a conexao e insercao massiva na tabela STG do Oracle."""

    def __init__(self, user: str, password: str, dsn: str):
        if oracledb is None:
            raise RuntimeError("Biblioteca 'oracledb' necessaria. Execute: pip install oracledb")
        self.connection = oracledb.connect(user=user, password=password, dsn=dsn)
        logger.info("Conexao estabelecida com Oracle (%s).", dsn)

    def fechar(self) -> None:
        """Encerra a conexao com o banco."""
        if self.connection:
            self.connection.close()

    def carregar_lote(self, linhas: List[Dict[str, Any]], batch_size: int = 1000) -> int:
        """Executa carga em lote na tabela STG via executemany."""
        if not linhas:
            logger.info("Nenhum registro para gravar no Oracle.")
            return 0

        sql = f"""
            INSERT INTO {TARGET_STG_TABLE} (
                ID_<ENTIDADE>,
                DATA_<EVENTO>,
                SIGLA_<ENTIDADE>,
                NOME_<ENTIDADE>,
                VAL_<VALOR_1>,
                ID_LOTE,
                DTC_EXTRACAO
            ) VALUES (
                :ID_<ENTIDADE>,
                TO_DATE(:DATA_<EVENTO>, 'YYYY-MM-DD'),
                :SIGLA_<ENTIDADE>,
                :NOME_<ENTIDADE>,
                :VAL_<VALOR_1>,
                :ID_LOTE,
                SYSDATE
            )
        """

        total_inserido = 0
        cursor = self.connection.cursor()
        try:
            for i in range(0, len(linhas), batch_size):
                chunk = linhas[i:i + batch_size]
                cursor.executemany(sql, chunk)
                self.connection.commit()
                total_inserido += len(chunk)
                logger.info("Gravadas %d/%d linhas na tabela %s...", total_inserido, len(linhas), TARGET_STG_TABLE)
        finally:
            cursor.close()

        return total_inserido


# ----------------------------------------------------------------------------
# FLUXO PRINCIPAL DE EXECUÇÃO
# ----------------------------------------------------------------------------
def executar_extracao(start_date: str, end_date: str, dry_run: bool = False) -> None:
    """Orquestra o ciclo completo: Consulta -> Flatten -> Carga STG."""
    logger.info("Iniciando extracao de API para o periodo de %s a %s...", start_date, end_date)
    id_lote = int(datetime.now().strftime("%Y%m%d%H%M%S"))

    client = OAuth2ApiClient(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
    registros_processados: List[Dict[str, Any]] = []

    # Exemplo de paginacao por offset
    offset = 0
    limit = 100
    tem_mais = True

    while tem_mais:
        params = {
            "start_date": start_date,
            "end_date": end_date,
            "offset": offset,
            "limit": limit,
        }
        logger.info("Buscando registros (offset=%d, limit=%d)...", offset, limit)
        dados = client.get_page("entidades", params=params)
        itens = dados.get("data", [])

        if not itens:
            tem_mais = False
            break

        for item in itens:
            flat = flatten_dict(item)
            registro_stg = {
                "ID_<ENTIDADE>": flat.get("id"),
                "DATA_<EVENTO>": flat.get("date"),
                "SIGLA_<ENTIDADE>": extrai_sigla_padrao(flat.get("name")),
                "NOME_<ENTIDADE>": flat.get("description", "")[:200],
                "VAL_<VALOR_1>": float(flat.get("amount", 0.0)),
                "ID_LOTE": id_lote,
            }
            registros_processados.append(registro_stg)

        offset += limit
        if len(itens) < limit:
            tem_mais = False

    logger.info("Extracao concluida. Total de registros coletados: %d.", len(registros_processados))

    if dry_run:
        logger.info("Modo DRY-RUN ativado. Dados nao foram persistidos no Oracle.")
        return

    loader = OracleStagingLoader(user=DB_USER, password=DB_PASSWORD, dsn=DB_DSN)
    try:
        total = loader.carregar_lote(registros_processados)
        logger.info("Carga concluida com SUCESSO! Total inserido: %d registros (Lote: %d).", total, id_lote)
    finally:
        loader.fechar()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extrator corporativo de API REST para Oracle DW.")
    parser.add_argument("--start-date", default=(date.today() - timedelta(days=1)).isoformat(), help="Data inicial (YYYY-MM-DD)")
    parser.add_argument("--end-date", default=date.today().isoformat(), help="Data final (YYYY-MM-DD)")
    parser.add_argument("--dry-run", action="store_true", help="Executa sem persistir no Oracle")
    args = parser.parse_args()

    try:
        executar_extracao(args.start_date, args.end_date, args.dry_run)
    except Exception as e:
        logger.critical("Falha fatal na extracao de API: %s", e, exc_info=True)
        sys.exit(1)

