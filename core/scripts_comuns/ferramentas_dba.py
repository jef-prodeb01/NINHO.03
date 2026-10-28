#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ferramentas DBA do NINHO (Fase 3):

  /comparar-modelo      DW em produção (entrega/planejador_dw/ddl) x modelo novo (saida/planejador_dw)
                        -> saida/planejador_dw/05_procedimentos_manutencao/12_alter_incremental.sql
  /estimar-volumetria   tamanho, índices, crescimento em 5 anos e particionamento
                        -> 09_relatorio_estrategias/VOLUMETRIA_<PROJETO>.md + 01_controle_carga/01_dimensionamento_tablespaces.sql
  /inspecionar-banco    lê o DDL real do schema Oracle (DBMS_METADATA) para entrega/planejador_dw/ddl/
                        (com oracledb + ORACLE_USER/ORACLE_PASS/ORACLE_DSN); sem conexão, gera o script de extração.

Uso:
  python core/scripts_comuns/ferramentas_dba.py comparar-modelo [--atual PASTA_OU_ARQ] [--novo PASTA_OU_ARQ] [--schema S]
  python core/scripts_comuns/ferramentas_dba.py estimar-volumetria [--ddl PASTA_OU_ARQ] [--linhas FATO_X=50000000 ...] [--crescimento 0.02]
  python core/scripts_comuns/ferramentas_dba.py inspecionar-banco --schema SCHEMA [--apenas-script]
"""

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from inspecionar_ddl_origem import ler_texto_sql, parse_ddl_text  # noqa: E402
from ninho_core.comparador_modelo import comparar, gerar_script_alter  # noqa: E402
from ninho_core.console import configurar_saida_utf8, print_err, print_ok, print_warn  # noqa: E402
from ninho_core.paths import ENTREGA_DIR, SAIDA_DIR  # noqa: E402
from ninho_core.volumetria import estimar, relatorio_markdown, script_tablespaces  # noqa: E402

configurar_saida_utf8()

SAIDA_DW = SAIDA_DIR / "planejador_dw"
DDL_ENTREGA = ENTREGA_DIR / "planejador_dw" / "ddl"


def _arquivos_ddl(alvo: Path, padrao_saida: bool = False) -> list:
    if alvo.is_file():
        return [alvo]
    if padrao_saida:
        return sorted(p for p in alvo.rglob("0[2-4]_create_*.sql"))
    return sorted(p for ext in ("*.sql", "*.ddl", "*.txt") for p in alvo.rglob(ext) if p.name.lower() != "readme.md")


def _ler_tabelas(alvo: Path, padrao_saida: bool = False) -> list:
    tabelas = []
    for arq in _arquivos_ddl(alvo, padrao_saida):
        tabelas.extend(parse_ddl_text(ler_texto_sql(arq), arq.name))
    return tabelas


def cmd_comparar(args) -> int:
    atual = _ler_tabelas(Path(args.atual))
    novo = _ler_tabelas(Path(args.novo), padrao_saida=Path(args.novo) == SAIDA_DW)
    if not atual or not novo:
        print_err(f"DDL ausente: atual={len(atual)} tabela(s) em {args.atual}; novo={len(novo)} tabela(s) em {args.novo}.")
        print("Deposite o DDL do DW em produção em entrega/planejador_dw/ddl/ e gere o modelo novo (/executar-dw).")
        return 1
    dif = comparar(atual, novo)
    destino = SAIDA_DW / "05_procedimentos_manutencao" / "12_alter_incremental.sql"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(gerar_script_alter(dif, novo, args.schema), encoding="utf-8")
    print_ok(f"Tabelas novas: {len(dif.tabelas_novas)} | colunas novas: {len(dif.colunas_novas)} | tipos alterados: {len(dif.tipos_alterados)}")
    if dif.colunas_removidas or dif.tabelas_removidas:
        print_warn(f"{len(dif.colunas_removidas)} coluna(s) e {len(dif.tabelas_removidas)} tabela(s) ausentes no modelo novo (saem comentadas).")
    print_ok(f"Script gerado: {destino.relative_to(SAIDA_DIR.parent).as_posix()}")
    return 0


def cmd_volumetria(args) -> int:
    alvo = Path(args.ddl) if args.ddl else (SAIDA_DW if any(SAIDA_DW.rglob("0[2-4]_create_*.sql")) else DDL_ENTREGA)
    tabelas = _ler_tabelas(alvo, padrao_saida=alvo == SAIDA_DW)
    if not tabelas:
        print_err(f"Nenhum DDL encontrado em {alvo}.")
        return 1
    linhas = {}
    for item in args.linhas or []:
        nome, _, valor = item.partition("=")
        linhas[nome.strip().upper()] = int(valor.replace(".", "").replace("_", ""))
    est = estimar(tabelas, linhas, args.crescimento)
    projeto = args.projeto.upper()
    rel = SAIDA_DW / "09_relatorio_estrategias" / f"VOLUMETRIA_{projeto}.md"
    ts = SAIDA_DW / "01_controle_carga" / "01_dimensionamento_tablespaces.sql"
    for p in (rel, ts):
        p.parent.mkdir(parents=True, exist_ok=True)
    rel.write_text(relatorio_markdown(est, projeto, args.crescimento), encoding="utf-8")
    ts.write_text(script_tablespaces(est, f"{projeto}_DATA", f"{projeto}_INDEX"), encoding="utf-8")
    print(relatorio_markdown(est, projeto, args.crescimento))
    print_ok(f"Relatório: {rel.name} | Tablespaces: {ts.name}")
    return 0


SQL_EXTRACAO = """-- NINHO — extração do DDL do schema {schema} (rode no SQL*Plus/SQLcl e salve a saída em
-- entrega/planejador_dw/ddl/ddl_banco_{schema_min}.sql; depois use /inspecionar-fontes ou /comparar-modelo)
SET LONG 200000 LONGCHUNKSIZE 200000 PAGESIZE 0 LINESIZE 32767 TRIMSPOOL ON FEEDBACK OFF HEADING OFF
BEGIN
  DBMS_METADATA.SET_TRANSFORM_PARAM(DBMS_METADATA.SESSION_TRANSFORM, 'STORAGE', FALSE);
  DBMS_METADATA.SET_TRANSFORM_PARAM(DBMS_METADATA.SESSION_TRANSFORM, 'SEGMENT_ATTRIBUTES', FALSE);
  DBMS_METADATA.SET_TRANSFORM_PARAM(DBMS_METADATA.SESSION_TRANSFORM, 'SQLTERMINATOR', TRUE);
END;
/
SPOOL ddl_banco_{schema_min}.sql
SELECT DBMS_METADATA.GET_DDL('TABLE', TABLE_NAME, OWNER) FROM ALL_TABLES WHERE OWNER = '{schema}' ORDER BY TABLE_NAME;
SELECT 'COMMENT ON COLUMN ' || OWNER || '.' || TABLE_NAME || '.' || COLUMN_NAME || ' IS ''' || REPLACE(COMMENTS, '''', '''''') || ''';'
  FROM ALL_COL_COMMENTS WHERE OWNER = '{schema}' AND COMMENTS IS NOT NULL ORDER BY TABLE_NAME, COLUMN_NAME;
SPOOL OFF
"""


def cmd_inspecionar_banco(args) -> int:
    schema = args.schema.upper()
    credenciais = all(os.getenv(v) for v in ("ORACLE_USER", "ORACLE_PASS", "ORACLE_DSN"))
    try:
        import oracledb  # noqa: F401
        tem_driver = True
    except ImportError:
        tem_driver = False
    if args.apenas_script or not (credenciais and tem_driver):
        destino = SAIDA_DW / "05_procedimentos_manutencao" / f"extrair_ddl_{schema.lower()}.sql"
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(SQL_EXTRACAO.format(schema=schema, schema_min=schema.lower()), encoding="utf-8")
        if not args.apenas_script:
            print_warn("Sem conexão direta (instale `oracledb` e defina ORACLE_USER, ORACLE_PASS e ORACLE_DSN).")
        print_ok(f"Script de extração gerado para o DBA: {destino.relative_to(SAIDA_DIR.parent).as_posix()}")
        return 0

    import oracledb

    with oracledb.connect(user=os.environ["ORACLE_USER"], password=os.environ["ORACLE_PASS"], dsn=os.environ["ORACLE_DSN"]) as con:
        cur = con.cursor()
        cur.callproc("DBMS_METADATA.SET_TRANSFORM_PARAM", [-1, "STORAGE", False])
        cur.callproc("DBMS_METADATA.SET_TRANSFORM_PARAM", [-1, "SEGMENT_ATTRIBUTES", False])
        cur.callproc("DBMS_METADATA.SET_TRANSFORM_PARAM", [-1, "SQLTERMINATOR", True])
        cur.execute("SELECT DBMS_METADATA.GET_DDL('TABLE', TABLE_NAME, OWNER) FROM ALL_TABLES WHERE OWNER = :s ORDER BY TABLE_NAME", s=schema)
        ddls = [str(linha[0].read() if hasattr(linha[0], "read") else linha[0]) for linha in cur]
        cur.execute(
            "SELECT OWNER, TABLE_NAME, COLUMN_NAME, COMMENTS FROM ALL_COL_COMMENTS WHERE OWNER = :s AND COMMENTS IS NOT NULL", s=schema
        )
        comentarios = [f"COMMENT ON COLUMN {o}.{t}.{c} IS '{(txt or '').replace(chr(39), chr(39) * 2)}';" for o, t, c, txt in cur]
    destino = DDL_ENTREGA / f"ddl_banco_{schema.lower()}.sql"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text("\n\n".join(ddls + comentarios) + "\n", encoding="utf-8")
    print_ok(f"{len(ddls)} tabela(s) e {len(comentarios)} comentário(s) extraídos para {destino.relative_to(ENTREGA_DIR.parent).as_posix()}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Ferramentas DBA do NINHO.")
    sub = parser.add_subparsers(dest="comando", required=True)
    p = sub.add_parser("comparar-modelo")
    p.add_argument("--atual", default=str(DDL_ENTREGA))
    p.add_argument("--novo", default=str(SAIDA_DW))
    p.add_argument("--schema", default="<SCHEMA_DW>")
    p = sub.add_parser("estimar-volumetria")
    p.add_argument("--ddl", default=None)
    p.add_argument("--linhas", nargs="*", help="TABELA=QTD (ex.: FATO_CONTRATO=50000000)")
    p.add_argument("--crescimento", type=float, default=0.02, help="Crescimento mensal (0.02 = 2%%)")
    p.add_argument("--projeto", default="PROJETO")
    p = sub.add_parser("inspecionar-banco")
    p.add_argument("--schema", required=True)
    p.add_argument("--apenas-script", action="store_true")
    args = parser.parse_args()
    return {"comparar-modelo": cmd_comparar, "estimar-volumetria": cmd_volumetria, "inspecionar-banco": cmd_inspecionar_banco}[args.comando](args)


if __name__ == "__main__":
    sys.exit(main())
