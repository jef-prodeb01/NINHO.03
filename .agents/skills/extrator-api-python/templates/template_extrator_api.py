"""
Template Padrão de Extrator de API REST para Oracle Staging
Módulo: Planejador de DW
"""

import os
import sys
import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
import oracledb

# Configuração de Logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("ExtratorAPI")

# Parâmetros e Credenciais via Variáveis de Ambiente
API_URL = os.getenv("API_BASE_URL", "https://api.exemplo.gov.br/v1/dados")
API_TOKEN = os.getenv("API_TOKEN", "")
DB_USER = os.getenv("ORACLE_USER", "DW_USER")
DB_PASS = os.getenv("ORACLE_PASS", "DW_PASS")
DB_DSN = os.getenv("ORACLE_DSN", "localhost:1521/ORCLPDB1")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "2000"))


def criar_sessao_http() -> requests.Session:
    """Cria uma sessão HTTP com política de retry automático."""
    session = requests.Session()
    retry_strategy = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    if API_TOKEN:
        session.headers.update({"Authorization": f"Bearer {API_TOKEN}"})
    return session


def extrair_e_carregar():
    session = criar_sessao_http()
    
    logger.info("Conectando ao Oracle DW (%s)...", DB_DSN)
    connection = oracledb.connect(user=DB_USER, password=DB_PASS, dsn=DB_DSN)
    cursor = connection.cursor()

    try:
        logger.info("Truncando tabela de staging STG_API_DADOS...")
        cursor.execute("TRUNCATE TABLE STG_API_DADOS")

        insert_sql = """
            INSERT INTO STG_API_DADOS (
                ID_ORIGINAL,
                NOM_ENTIDADE,
                DTC_EVENTO,
                VAL_METRICA,
                DTC_CARGA
            ) VALUES (:1, :2, TO_DATE(:3, 'YYYY-MM-DD"T"HH24:MI:SS'), :4, SYSDATE)
        """

        page = 1
        total_processado = 0
        lote = []

        while True:
            logger.info("Requisitando página %d...", page)
            resp = session.get(API_URL, params={"pagina": page, "tamanho": BATCH_SIZE}, timeout=30)
            resp.raise_for_status()
            dados = resp.json()

            items = dados.get("itens", [])
            if not items:
                logger.info("Nenhum dado retornado. Fim da paginação.")
                break

            for item in items:
                lote.append((
                    item.get("id"),
                    item.get("nome"),
                    item.get("data_evento"),
                    item.get("valor")
                ))

            if len(lote) >= BATCH_SIZE:
                cursor.executemany(insert_sql, lote)
                connection.commit()
                total_processado += len(lote)
                logger.info("Inseridos %d registros na Staging.", total_processado)
                lote = []

            if not dados.get("tem_proxima_pagina", False):
                break
            page += 1

        if lote:
            cursor.executemany(insert_sql, lote)
            connection.commit()
            total_processado += len(lote)

        logger.info("Carga concluída com sucesso! Total de linhas aterrissadas: %d", total_processado)

    except Exception as e:
        logger.error("Erro durante a extração e carga: %s", str(e), exc_info=True)
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    extrair_e_carregar()
