#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================================
🧪 SUÍTE AUTOMATIZADA DE TESTES END-TO-END (E2E) — PLATAFORMA NINHO
================================================================================
Executa uma bateria completa de testes de regressão e integração sobre todos os
motores de `core/scripts_comuns/` em ambiente controlado, garantindo ao final
que o workspace (`entrega/` e `saida/`) termine 100% limpo.

O que é testado:
  1. Central de Ajuda (`ajuda_ninho.py`) e Gerenciador de Workspace (`gerenciar_projeto.py`)
  2. Extrator Determinístico de DDLs + Radar Consultivo (`inspecionar_ddl_origem.py`)
  3. Simulador Ponta a Ponta + Parser Reverso DW & Semântica + KPIs Radar (`simular_projeto.py`)
  4. Gerador Dinâmico de Dados Sintéticos BI com Chaves -1 (`gerar_mock_dados.py`)
  5. Validador de Qualidade Pós-Geração (`validar_entrega.py saida`)
  6. Transição DW -> Semântica (`transicionar_dw_para_semantica.py`) e Micro-Modos (`modular_semantica.py`)
  7. Motor Fast-Track Não-Destrutivo (`melhorar_dw_existente.py`) + `validar_entrega.py fast-track`
  8. Motores de Auditoria Especializados:
     - ODI 12c (`auditar_mapa_odi.py` — heurísticas H1 a H9)
     - Apache Hop 2.x (`auditar_esteira_hop.py` — heurísticas HOP-H1 a HOP-H8)
     - Power BI `.pbix` (`inspecionar_pbix.py` — AST + heurísticas PBIX-H1 a PBIX-H5)
     - Governança Gate 0.5 (`inspecionar_insumos_governanca.py` — bloqueio na origem)

Uso:
  python core/scripts_comuns/testar_ninho.py
  python core/scripts_comuns/testar_ninho.py --manter-arquivos
================================================================================
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Callable, List, Tuple

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPT_DIR.parent.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))


DDL_ORIGEM_TESTE = """
-- DDL Transacional de Teste E2E (Compras e Contratos Públicos)
CREATE TABLE TB_ORGAO_PUBLICO (
    ID_ORGAO NUMBER(10) NOT NULL,
    SIG_ORGAO VARCHAR2(20) NOT NULL,
    NOM_ORGAO VARCHAR2(150) NOT NULL,
    DES_ESFERA VARCHAR2(50),
    CONSTRAINT PK_TB_ORGAO_PUBLICO PRIMARY KEY (ID_ORGAO)
);

CREATE TABLE TB_FORNECEDOR (
    ID_FORNECEDOR NUMBER(12) NOT NULL,
    NUM_CNPJ VARCHAR2(18) NOT NULL,
    NOM_FORNECEDOR VARCHAR2(200) NOT NULL,
    SIG_UF CHAR(2),
    DES_PORTE_EMPRESA VARCHAR2(60),
    CONSTRAINT PK_TB_FORNECEDOR PRIMARY KEY (ID_FORNECEDOR)
);

CREATE TABLE TB_LICITACAO_CONTRATO (
    ID_CONTRATO NUMBER(15) NOT NULL,
    ID_ORGAO NUMBER(10) NOT NULL,
    ID_FORNECEDOR NUMBER(12) NOT NULL,
    NUM_PROCESSO_SEI VARCHAR2(40) NOT NULL,
    DES_MODALIDADE VARCHAR2(60),
    DES_STATUS_CONTRATO VARCHAR2(40),
    DES_OBSERVACAO_INTERNA VARCHAR2(400),
    DTC_ASSINATURA DATE NOT NULL,
    DTC_VIGENCIA_FIM DATE,
    QTD_ITENS_CONTRATO NUMBER(8),
    VAL_ESTIMADO NUMBER(18,2),
    VAL_CONTRATO NUMBER(18,2) NOT NULL,
    VAL_PAGO_ACUMULADO NUMBER(18,2),
    CONSTRAINT PK_TB_LICITACAO_CONTRATO PRIMARY KEY (ID_CONTRATO),
    CONSTRAINT FK_CONTRATO_ORGAO FOREIGN KEY (ID_ORGAO) REFERENCES TB_ORGAO_PUBLICO (ID_ORGAO),
    CONSTRAINT FK_CONTRATO_FORN FOREIGN KEY (ID_FORNECEDOR) REFERENCES TB_FORNECEDOR (ID_FORNECEDOR)
);
"""


def _executar_cli(args_lista: List[str]) -> Tuple[int, str, str]:
    """Executa um script Python via subprocess e retorna (returncode, stdout, stderr)."""
    cmd = [sys.executable] + args_lista
    proc = subprocess.run(
        cmd,
        cwd=str(BASE_DIR),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return proc.returncode, proc.stdout, proc.stderr


ARQUIVOS_PRESERVADOS_TEMPLATE = {".gitkeep", "README.md", "01_create_meta_tables.sql"}

ARQUIVOS_TEMPLATE_PARA_SNAPSHOT = [
    BASE_DIR / "modulos" / "camada_semantica" / "INTAKE_SEMANTICA.md",
    BASE_DIR / "documentacao" / "catalogo_projetos" / "PROJETO_RESUMO.md",
    BASE_DIR / "documentacao" / "catalogo_projetos" / "PROJETO_VERSION.md",
]


def _limpar_artefatos_workspace() -> None:
    """Remove todos os arquivos temporários gerados em entrega/ e saida/ preservando .gitkeep, README.md e base DDL."""
    for raiz_rel in ("entrega", "saida"):
        pasta_raiz = BASE_DIR / raiz_rel
        if not pasta_raiz.exists():
            continue
        for item in sorted(pasta_raiz.rglob("*"), key=lambda p: len(p.parts), reverse=True):
            if item.is_file() and item.name not in ARQUIVOS_PRESERVADOS_TEMPLATE:
                item.unlink(missing_ok=True)
            elif item.is_dir():
                try:
                    if not any(item.iterdir()):
                        item.rmdir()
                except OSError:
                    pass


def _contar_arquivos_workspace() -> Tuple[int, int]:
    """Retorna (qtd_arquivos_entrega, qtd_arquivos_saida) ignorando arquivos preservados do template."""
    qtd_e = sum(
        1
        for p in (BASE_DIR / "entrega").rglob("*")
        if p.is_file() and p.name not in ARQUIVOS_PRESERVADOS_TEMPLATE
    ) if (BASE_DIR / "entrega").exists() else 0
    qtd_s = sum(
        1
        for p in (BASE_DIR / "saida").rglob("*")
        if p.is_file() and p.name not in ARQUIVOS_PRESERVADOS_TEMPLATE
    ) if (BASE_DIR / "saida").exists() else 0
    return qtd_e, qtd_s


# ==============================================================================
# CASOS DE TESTE E2E
# ==============================================================================

def teste_01_ajuda_e_status() -> str:
    rc, out, err = _executar_cli(["core/scripts_comuns/ajuda_ninho.py", "--topico", "simulacao"])
    assert rc == 0, f"ajuda_ninho.py falhou: {err}"
    assert "/simular-dw" in out and "/executar-simulacao" in out, "Comandos de simulação ausentes no /help"

    rc2, out2, err2 = _executar_cli(["core/scripts_comuns/gerenciar_projeto.py", "--status"])
    assert rc2 == 0, f"gerenciar_projeto.py --status falhou: {err2}"
    return "Catálogo /help e gerenciador de status validados."


def teste_02_inspecionar_ddl_origem() -> str:
    pasta_sql = BASE_DIR / "entrega" / "planejador_dw" / "ddl"
    pasta_sql.mkdir(parents=True, exist_ok=True)
    arq_ddl = pasta_sql / "01_origem_licitacao.sql"
    arq_ddl.write_text(DDL_ORIGEM_TESTE.strip() + "\n", encoding="utf-8")

    rc, out, err = _executar_cli(["core/scripts_comuns/inspecionar_ddl_origem.py"])
    assert rc == 0, f"inspecionar_ddl_origem.py falhou: {err}\n{out}"
    assert "TB_LICITACAO_CONTRATO" in out, "Tabela Fato transacional não detectada pelo extrator DDL"
    assert "TB_ORGAO_PUBLICO" in out and "TB_FORNECEDOR" in out, "Tabelas de domínio não detectadas"
    return "Extrator determinístico de DDL e Radar Consultivo validados (3 tabelas)."


def teste_03_simulacao_edicao_reversa_dw_e_semantica() -> str:
    # 1. Gera as duas Blueprints editáveis
    rc, out, err = _executar_cli(
        ["core/scripts_comuns/simular_projeto.py", "--modulo", "ambos", "--acao", "simular"]
    )
    assert rc == 0, f"simular_projeto.py --acao simular falhou: {err}\n{out}"

    bp_dw = BASE_DIR / "entrega" / "planejador_dw" / "SIMULACAO_BLUEPRINT_DW.md"
    bp_sem = BASE_DIR / "entrega" / "camada_semantica" / "SIMULACAO_BLUEPRINT_SEMANTICA.md"
    assert bp_dw.exists(), "SIMULACAO_BLUEPRINT_DW.md não foi gerada"
    assert bp_sem.exists(), "SIMULACAO_BLUEPRINT_SEMANTICA.md não foi gerada"

    # 2. Edita a Blueprint do DW:
    #    - Desmarca a coluna DES_OBSERVACAO_INTERNA (`| [ ] |`)
    #    - Altera a descrição da coluna VAL_CONTRATO
    #    - Marca o checkbox de aprovação final
    txt_dw = bp_dw.read_text(encoding="utf-8")
    linhas_dw_editadas = []
    desmarcou_obs = False
    editou_desc_val = False
    for ln in txt_dw.splitlines():
        if "`DES_OBSERVACAO_INTERNA`" in ln and "| [x] |" in ln:
            ln = ln.replace("| [x] |", "| [ ] |", 1)
            desmarcou_obs = True
        elif "`VAL_CONTRATO`" in ln and "| [x] |" in ln:
            partes = [p.strip() for p in ln.strip().strip("|").split("|")]
            if len(partes) >= 7:
                partes[6] = "COMENTARIO_CUSTOMIZADO_TESTE_E2E_VALOR_CONTRATO"
                ln = "| " + " | ".join(partes) + " |"
                editou_desc_val = True
        elif "SIMULAÇÃO 100% FECHADA E APROVADA PARA EXECUÇÃO REAL" in ln:
            ln = ln.replace("- [ ]", "- [x]")
        linhas_dw_editadas.append(ln)

    assert desmarcou_obs, "Não encontrou coluna DES_OBSERVACAO_INTERNA para desmarcar na Blueprint DW"
    assert editou_desc_val, "Não encontrou coluna VAL_CONTRATO para editar descrição na Blueprint DW"
    bp_dw.write_text("\n".join(linhas_dw_editadas) + "\n", encoding="utf-8")

    # 3. Edita a Blueprint da Camada Semântica:
    #    - Altera COLUNA_SEGREGACAO_RLS para SK_ORGAO_CUSTOM_RLS
    #    - Renomeia a View de Evento (Camada 2) para VW_EVENTO_CONTRATOS_CUSTOM e customiza seu grão
    #    - Desmarca QTD_TOTAL_* na Seção 5 e adiciona nova métrica VAL_ECONOMIA_GERADA
    #    - Mantém os KPIs do Radar (Seção 6.1: TICKET_MEDIO_* e TAXA_QUALID_*) marcados [x]
    #    - Marca o checkbox de aprovação final
    txt_sem = bp_sem.read_text(encoding="utf-8")
    linhas_sem_editadas = []
    renomeou_vw_evento = False
    desmarcou_qtd_reg = False
    inseriu_metrica_custom = False

    for ln in txt_sem.splitlines():
        if "`COLUNA_SEGREGACAO_RLS`" in ln:
            ln = "| `COLUNA_SEGREGACAO_RLS` | `SK_ORGAO_CUSTOM_RLS` | Coluna customizada no teste E2E |"
        elif "`CAMADA_2_EVENTO`" in ln and "| [x] |" in ln:
            partes = [p.strip() for p in ln.strip().strip("|").split("|")]
            if len(partes) >= 6:
                partes[2] = "`VW_EVENTO_CONTRATOS_CUSTOM`"
                partes[4] = "Uma linha representa um contrato auditado no teste E2E"
                ln = "| " + " | ".join(partes) + " |"
                renomeou_vw_evento = True
        elif "`QTD_TOTAL_" in ln and "| [x] |" in ln:
            partes_m = [p.strip() for p in ln.strip().strip("|").split("|")]
            vw_kpi_alvo = partes_m[4].strip("`") if len(partes_m) >= 5 else "VW_KPI_CONTRATO"
            ln = ln.replace("| [x] |", "| [ ] |", 1)
            desmarcou_qtd_reg = True
            linhas_sem_editadas.append(ln)
            linhas_sem_editadas.append(
                f"| [x] | `VAL_ECONOMIA_GERADA` | Economia Licitatória Gerada | `ROUND(SUM(NVL(e.VAL_CONTRATO, 0)) * 0.12, 2)` | `{vw_kpi_alvo}` | `MOEDA` |"
            )
            inseriu_metrica_custom = True
            continue
        elif "SIMULAÇÃO 100% FECHADA E APROVADA PARA EXECUÇÃO REAL" in ln:
            ln = ln.replace("- [ ]", "- [x]")
        linhas_sem_editadas.append(ln)

    assert renomeou_vw_evento, "Não conseguiu renomear a View de Evento na Blueprint Semântica"
    assert desmarcou_qtd_reg and inseriu_metrica_custom, "Não conseguiu editar métricas da Seção 5 na Blueprint Semântica"
    bp_sem.write_text("\n".join(linhas_sem_editadas) + "\n", encoding="utf-8")

    # 4. Executa a geração real de ambos os módulos a partir das Blueprints editadas
    rc_exec, out_exec, err_exec = _executar_cli(
        ["core/scripts_comuns/simular_projeto.py", "--modulo", "ambos", "--acao", "executar"]
    )
    assert rc_exec == 0, f"simular_projeto.py --acao executar falhou: {err_exec}\n{out_exec}"

    # 5. Verifica se as edições da Blueprint DW refletiram fisicamente em saida/planejador_dw/
    arq_ddl_dw = BASE_DIR / "saida" / "planejador_dw" / "04_fatos" / "04_create_fato_tables.sql"
    assert arq_ddl_dw.exists(), "04_create_fato_tables.sql não foi gerado"
    conteudo_ddl_dw = arq_ddl_dw.read_text(encoding="utf-8")
    assert "DES_OBSERVACAO_INTERNA" not in conteudo_ddl_dw, (
        "Coluna desmarcada [ ] (DES_OBSERVACAO_INTERNA) não deveria estar no DDL físico!"
    )
    assert "COMENTARIO_CUSTOMIZADO_TESTE_E2E_VALOR_CONTRATO" in conteudo_ddl_dw, (
        "Comentário editado na Blueprint DW não foi refletido em 04_create_fato_tables.sql!"
    )

    # 6. Verifica se as edições da Blueprint Semântica + Radar da IA refletiram em saida/camada_semantica/
    arq_vw_ev = BASE_DIR / "saida" / "camada_semantica" / "vw_analiticas" / "02_vw_eventos.sql"
    arq_vw_kpi = BASE_DIR / "saida" / "camada_semantica" / "vw_analiticas" / "03_vw_kpis.sql"
    arq_meta_m = BASE_DIR / "saida" / "camada_semantica" / "meta_projeto" / "02_meta_metrica.sql"
    arq_meta_p = BASE_DIR / "saida" / "camada_semantica" / "meta_projeto" / "06_meta_pergunta_negocio.sql"
    arq_rls = BASE_DIR / "saida" / "camada_semantica" / "meta_projeto" / "02_rls.sql"

    sql_ev = arq_vw_ev.read_text(encoding="utf-8")
    sql_kpi = arq_vw_kpi.read_text(encoding="utf-8")
    sql_meta_m = arq_meta_m.read_text(encoding="utf-8")
    sql_meta_p = arq_meta_p.read_text(encoding="utf-8")
    sql_rls = arq_rls.read_text(encoding="utf-8")

    assert "VW_EVENTO_CONTRATOS_CUSTOM" in sql_ev, "Nome customizado da View de Evento não refletiu em 02_vw_eventos.sql"
    assert "Uma linha representa um contrato auditado no teste E2E" in sql_ev, "Grão customizado não refletiu em 02_vw_eventos.sql"
    assert "VAL_ECONOMIA_GERADA" in sql_kpi, "Métrica customizada VAL_ECONOMIA_GERADA ausente em 03_vw_kpis.sql"
    assert "TICKET_MEDIO_" in sql_kpi and "TAXA_QUALID_" in sql_kpi, "KPIs do Radar da IA (Seção 6.1) ausentes em 03_vw_kpis.sql"
    assert "QTD_TOTAL_" not in sql_meta_m, "Métrica desmarcada [ ] (QTD_TOTAL_*) não deveria estar em 02_meta_metrica.sql"
    assert "VAL_ECONOMIA_GERADA" in sql_meta_m and "TICKET_MEDIO_" in sql_meta_m, "Métricas custom/Radar ausentes em 02_meta_metrica.sql"
    assert "_RAD_" in sql_meta_p, "Golden Queries do Radar da IA (Seção 6.2) ausentes em 06_meta_pergunta_negocio.sql"
    assert "SK_ORGAO_CUSTOM_RLS" in sql_rls, "COLUNA_SEGREGACAO_RLS editada não refletiu em 02_rls.sql"

    return "Parser reverso DW + Semântica + KPIs do Radar da IA validados com 100% de fidelidade."


def teste_04_gerador_mock_dinamico() -> str:
    from gerar_mock_dados import gerar_dados_mock

    caminho_csv = str(BASE_DIR / "saida" / "planejador_dw" / "08_datasets_bi" / "mock_dados_bi.csv")
    res = gerar_dados_mock(
        num_linhas=40,
        caminho_saida=caminho_csv,
        separar_tabelas=True,
    )
    assert res["modo"] == "dinamico", f"Esperava modo dinamico, obteve {res['modo']}"
    assert res["linhas"] == 40, f"Esperava 40 linhas, obteve {res['linhas']}"
    assert res["sentinelas"] >= 1, "Esperava pelo menos 1 chave sentinela -1 gerada"
    assert "VAL_CONTRATO" in res["colunas"], "Coluna real VAL_CONTRATO ausente no CSV dinâmico"
    assert "DES_OBSERVACAO_INTERNA" not in res["colunas"], "Coluna desmarcada apareceu no CSV dinâmico"

    conteudo_csv = Path(caminho_csv).read_text(encoding="utf-8")
    assert ";-1;" in conteudo_csv or "\n-1;" in conteudo_csv, "Valor -1 não encontrado nas linhas do CSV"
    assert "NAO INFORMADO" in conteudo_csv, "Descrição 'NAO INFORMADO' não encontrada para chave -1"
    return f"Mock dinâmico BI validado ({len(res['colunas'])} colunas reais, {res['sentinelas']} chaves -1)."


def teste_05_validar_entrega_saida() -> str:
    rc, out, err = _executar_cli(["core/scripts_comuns/validar_entrega.py", "saida"])
    assert rc == 0, f"validar_entrega.py saida encontrou erros:\n{out}\n{err}"
    assert "ERROS CRÍTICOS: 0" in out or "0 erro" in out.lower() or "APROVAD" in out.upper(), (
        f"Saída inesperada do validador:\n{out}"
    )
    return "Auditoria pós-geração (validar_entrega.py saida) aprovada com 0 erros."


def teste_06_transicao_e_micro_modos_semantica() -> str:
    rc, out, err = _executar_cli(["core/scripts_comuns/transicionar_dw_para_semantica.py"])
    assert rc == 0, f"transicionar_dw_para_semantica.py falhou: {err}\n{out}"

    for modo in ("views-kpi", "catalogo-meta", "rls"):
        rc_m, out_m, err_m = _executar_cli(["core/scripts_comuns/modular_semantica.py", "--modo", modo])
        assert rc_m == 0, f"modular_semantica.py --modo {modo} falhou: {err_m}\n{out_m}"
    return "Transição contínua DW -> Semântica e micro-processos modulares validados."


def teste_07_fast_track_melhorar_dw_existente() -> str:
    rc, out, err = _executar_cli(["core/scripts_comuns/melhorar_dw_existente.py", "--modo", "tudo"])
    assert rc == 0, f"melhorar_dw_existente.py --modo tudo falhou: {err}\n{out}"

    arq_diag = BASE_DIR / "saida" / "planejador_dw" / "09_relatorio_estrategias" / "DIAGNOSTICO_MELHORIAS_DW_EXISTENTE.md"
    arq_html = BASE_DIR / "saida" / "planejador_dw" / "11_dicionario_dados" / "dicionario_dados.html"
    assert arq_diag.exists(), "DIAGNOSTICO_MELHORIAS_DW_EXISTENTE.md não foi gerado"
    assert arq_html.exists(), "dicionario_dados.html não foi gerado"

    rc_v, out_v, err_v = _executar_cli(["core/scripts_comuns/validar_entrega.py", "fast-track"])
    assert rc_v == 0, f"validar_entrega.py fast-track falhou:\n{out_v}\n{err_v}"
    return "Motor Fast-Track (melhorar_dw_existente.py + validar_entrega.py fast-track) validado."


def teste_08_motores_auditoria_odi_hop_pbix_governanca() -> str:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        # 8.1. Teste ODI 12c (auditar_mapa_odi.py)
        xml_odi = tmp / "MAP_FATO_CONTRATO.xml"
        xml_odi.write_text(
            """<?xml version="1.0" encoding="UTF-8"?>
<SunopsisExport>
  <Object class="com.sunopsis.dwg.dbobj.SnpMapping">
    <Field name="Name" type="java.lang.String"><![CDATA[MAP_FATO_CONTRATO]]></Field>
  </Object>
  <Object class="com.sunopsis.dwg.dbobj.SnpMapComp">
    <Field name="Name" type="java.lang.String"><![CDATA[FATO_CONTRATO]]></Field>
    <Field name="CompType" type="java.lang.String"><![CDATA[DATASTORE]]></Field>
  </Object>
  <Object class="com.sunopsis.dwg.dbobj.SnpMapComp">
    <Field name="Name" type="java.lang.String"><![CDATA[DIM_FORNECEDOR]]></Field>
    <Field name="CompType" type="java.lang.String"><![CDATA[LOOKUP]]></Field>
  </Object>
  <Object class="com.sunopsis.dwg.dbobj.SnpMapProp">
    <Field name="PropValue" type="java.lang.String"><![CDATA[IKM SQL Incremental Update]]></Field>
  </Object>
  <Object class="com.sunopsis.dwg.dbobj.SnpMapProp">
    <Field name="PropValue" type="java.lang.String"><![CDATA[LKM SQL to Oracle]]></Field>
  </Object>
  <Object class="com.sunopsis.dwg.dbobj.SnpMapExpr">
    <Field name="Txt" type="java.lang.String"><![CDATA[DES_ATUALIZAR = 'X' AND DTH_ABERTURA >= SYSDATE - 30 AND DTH_CONCLUSAO IS NOT NULL]]></Field>
  </Object>
</SunopsisExport>""",
            encoding="utf-8",
        )
        rel_odi = tmp / "relatorio_odi.md"
        rc_odi, out_odi, err_odi = _executar_cli(
            ["core/scripts_comuns/auditar_mapa_odi.py", str(xml_odi), "--output", str(rel_odi)]
        )
        assert rc_odi == 0 and rel_odi.exists(), f"auditar_mapa_odi.py falhou: {err_odi}\n{out_odi}"
        txt_rel_odi = rel_odi.read_text(encoding="utf-8")
        assert "IKM" in txt_rel_odi and "LKM" in txt_rel_odi, "Heurísticas ODI não geradas no relatório"

        # 8.2. Teste Apache Hop 2.x (auditar_esteira_hop.py)
        pasta_hop = tmp / "projeto_hop_teste"
        pasta_hop.mkdir()
        (pasta_hop / "pipeline_carga.hpl").write_text(
            """<?xml version="1.0" encoding="UTF-8"?>
<pipeline>
  <info><name>pipeline_carga</name></info>
  <transform>
    <name>Table output</name>
    <type>TableOutput</type>
    <table>STG_CONTRATO</table>
    <commit>100</commit>
  </transform>
</pipeline>""",
            encoding="utf-8",
        )
        rel_hop = tmp / "relatorio_hop.md"
        rc_hop, out_hop, err_hop = _executar_cli(
            ["core/scripts_comuns/auditar_esteira_hop.py", str(pasta_hop), "--saida", str(rel_hop)]
        )
        assert rc_hop == 0 and rel_hop.exists(), f"auditar_esteira_hop.py falhou: {err_hop}\n{out_hop}"
        txt_rel_hop = rel_hop.read_text(encoding="utf-8")
        assert "HOP-H" in txt_rel_hop, "Heurísticas HOP-H1..H8 não reportadas"

        # 8.3. Teste Power BI .pbix (inspecionar_pbix.py)
        arq_pbix = tmp / "Painel_SAEB_Teste.pbix"
        layout_json = {
            "sections": [
                {
                    "displayName": "Visão Geral",
                    "filters": "[]",
                    "visualContainers": [
                        {
                            "config": json.dumps(
                                {
                                    "singleVisual": {
                                        "visualType": "card",
                                        "prototypeQuery": {
                                            "From": [{"Name": "d", "Entity": "dadosConsolidados"}],
                                            "Select": [
                                                {
                                                    "Column": {
                                                        "Expression": {"SourceRef": {"Source": "d"}},
                                                        "Property": "processo_sei",
                                                    },
                                                    "Name": "dadosConsolidados.processo_sei",
                                                }
                                            ],
                                        },
                                    }
                                }
                            ),
                            "filters": json.dumps(
                                [
                                    {
                                        "filter": {
                                            "From": [{"Name": "d", "Entity": "dadosConsolidados"}],
                                            "Where": [
                                                {
                                                    "Condition": {
                                                        "Not": {
                                                            "Expression": {
                                                                "Comparison": {
                                                                    "ComparisonKind": 0,
                                                                    "Left": {
                                                                        "Column": {
                                                                            "Expression": {"SourceRef": {"Source": "d"}},
                                                                            "Property": "processo_sei",
                                                                        }
                                                                    },
                                                                    "Right": {"Literal": {"Value": "'TESTE-SEI'"}},
                                                                }
                                                            }
                                                        }
                                                    }
                                                }
                                            ],
                                        }
                                    }
                                ]
                            ),
                        }
                    ],
                }
            ]
        }
        with zipfile.ZipFile(arq_pbix, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("Report/Layout", json.dumps(layout_json).encode("utf-16-le"))

        rel_pbix = tmp / "relatorio_pbix.md"
        rc_pbix, out_pbix, err_pbix = _executar_cli(
            ["core/scripts_comuns/inspecionar_pbix.py", str(arq_pbix), "--output", str(rel_pbix)]
        )
        assert rc_pbix == 0 and rel_pbix.exists(), f"inspecionar_pbix.py falhou: {err_pbix}\n{out_pbix}"
        txt_rel_pbix = rel_pbix.read_text(encoding="utf-8")
        assert "TESTE-SEI" in txt_rel_pbix and "dadosConsolidados" in txt_rel_pbix, (
            "Extrator AST de filtros Power BI não detectou filtro TESTE-SEI ou tabela dadosConsolidados"
        )

        # 8.4. Teste Governança Gate 0.5 (inspecionar_insumos_governanca.py)
        pasta_gov = tmp / "insumos_gov"
        pasta_gov.mkdir()
        arq_csv_ruim = pasta_gov / "amostra_suja.csv"
        arq_csv_ruim.write_text(
            "NUM_CPF;NOM_SERVIDOR;VAL_SALARIO;;\n"
            "12345678901;JOAO SILVA;5500.00;;\n"
            ";;;;\n",
            encoding="utf-8",
        )
        rel_gov = tmp / "relatorio_gov.md"
        rc_gov, out_gov, err_gov = _executar_cli(
            [
                "core/scripts_comuns/inspecionar_insumos_governanca.py",
                str(pasta_gov),
                "--salvar-relatorio",
                str(rel_gov),
            ]
        )
        assert rel_gov.exists(), f"inspecionar_insumos_governanca.py não gerou relatório: {err_gov}\n{out_gov}"
        txt_rel_gov = rel_gov.read_text(encoding="utf-8")
        assert "REPROVADO" in txt_rel_gov.upper() or "DEVOLU" in txt_rel_gov.upper(), (
            "Gate 0.5 deveria reprovar CSV com linhas vazias e colunas fantasmas (;;;)"
        )

    return "Motores ODI 12c, Apache Hop 2.x, Power BI (.pbix) e Governança (Gate 0.5) validados."


def teste_09_experiencia_ux_conversacional() -> str:
    # 9.1. Assistente de Onboarding (/comecar)
    rc_onb, out_onb, err_onb = _executar_cli(["core/scripts_comuns/ajuda_ninho.py", "--onboarding"])
    assert rc_onb == 0 and "/comecar" in out_onb and "/demo" in out_onb, f"Falha em --onboarding: {err_onb}"

    # 9.2. Oráculo de Dúvidas (/duvida <tema>)
    rc_lst, out_lst, err_lst = _executar_cli(["core/scripts_comuns/ajuda_ninho.py", "--explicar", "listar"])
    assert rc_lst == 0 and "estrategia-carga" in out_lst, f"Falha em --explicar listar: {err_lst}"

    rc_exp, out_exp, err_exp = _executar_cli(["core/scripts_comuns/ajuda_ninho.py", "--explicar", "estrategia-carga"])
    assert rc_exp == 0 and "BITMAP" in out_exp and "B-Tree" in out_exp, f"Falha em --explicar estrategia-carga: {err_exp}"

    # 9.3. Check-up /doctor com auto-organização de arquivo solto
    _limpar_artefatos_workspace()
    arq_solto = BASE_DIR / "entrega" / "ddl_solto_teste_doctor.sql"
    arq_solto.write_text("CREATE TABLE DW_TESTE.DIM_TESTE (SK_TESTE NUMBER PRIMARY KEY);", encoding="utf-8")
    rc_doc, out_doc, err_doc = _executar_cli(["core/scripts_comuns/ajuda_ninho.py", "--doctor", "--corrigir"])
    assert rc_doc == 0, f"Falha em --doctor --corrigir: {err_doc}"
    arq_movido = BASE_DIR / "entrega" / "planejador_dw" / "ddl" / "ddl_solto_teste_doctor.sql"
    assert not arq_solto.exists() and arq_movido.exists(), "O /doctor --corrigir não moveu o arquivo .sql solto para entrega/planejador_dw/ddl/"

    # 9.4. Bússola Contextual (/onde-estou)
    rc_oe, out_oe, err_oe = _executar_cli(["core/scripts_comuns/ajuda_ninho.py", "--onde-estou"])
    assert rc_oe == 0 and "Bússola Contextual do NINHO" in out_oe and "Fase" in out_oe, f"Falha em --onde-estou: {err_oe}"

    # 9.5. Modo Playground (/demo e /limpar-demo)
    rc_demo, out_demo, err_demo = _executar_cli(["core/scripts_comuns/ajuda_ninho.py", "--demo"])
    assert rc_demo == 0 and "Projeto de Demonstração do NINHO Criado com Sucesso" in out_demo, f"Falha em --demo: {err_demo}\n{out_demo}"
    assert (BASE_DIR / "saida" / "planejador_dw" / "11_dicionario_dados" / "dicionario_dados.html").exists(), "Demo não gerou dicionario_dados.html"
    assert (BASE_DIR / "saida" / "camada_semantica" / "vw_analiticas" / "03_vw_kpis.sql").exists(), "Demo não gerou 03_vw_kpis.sql"

    rc_ld, out_ld, err_ld = _executar_cli(["core/scripts_comuns/ajuda_ninho.py", "--limpar-demo"])
    assert rc_ld == 0, f"Falha em --limpar-demo: {err_ld}"
    q_e, q_s = _contar_arquivos_workspace()
    assert q_e == 0 and q_s == 0, f"--limpar-demo deixou resíduos ({q_e} em entrega/, {q_s} em saida/)"

    return "Onboarding (/comecar), Bússola (/onde-estou), Oráculo (/duvida), Doctor (--corrigir) e Playground (/demo) validados."


def executar_suite_completa(manter_arquivos: bool = False) -> int:
    print("=" * 88)
    print("🦅 PLATAFORMA NINHO — SUÍTE AUTOMATIZADA DE TESTES END-TO-END (E2E)")
    print("=" * 88)

    testes: List[Tuple[str, Callable[[], str]]] = [
        ("T01: Central de Ajuda (/help) & Gerenciador de Projeto", teste_01_ajuda_e_status),
        ("T02: Extrator de DDLs de Origem & Radar Consultivo", teste_02_inspecionar_ddl_origem),
        ("T03: Simulação Editável + Parser Reverso DW & Semântica + KPIs Radar", teste_03_simulacao_edicao_reversa_dw_e_semantica),
        ("T04: Gerador Dinâmico de Mock BI (Colunas Reais + Sentinela -1)", teste_04_gerador_mock_dinamico),
        ("T05: Validador de Qualidade Pós-Geração (validar_entrega.py saida)", teste_05_validar_entrega_saida),
        ("T06: Transição DW -> Semântica & Micro-Modos Isolados", teste_06_transicao_e_micro_modos_semantica),
        ("T07: Motor Fast-Track Não-Destrutivo (melhorar_dw_existente.py)", teste_07_fast_track_melhorar_dw_existente),
        ("T08: Auditoria Especializada (ODI 12c, Hop 2.x, Power BI .pbix, Gov Gate 0.5)", teste_08_motores_auditoria_odi_hop_pbix_governanca),
        ("T09: Experiência Conversacional UX (/comecar, /onde-estou, /duvida, /doctor, /demo)", teste_09_experiencia_ux_conversacional),
    ]

    passou = 0
    falhou = 0
    inicio_total = time.time()

    snapshots = {
        arq: arq.read_bytes() for arq in ARQUIVOS_TEMPLATE_PARA_SNAPSHOT if arq.exists()
    }

    try:
        _limpar_artefatos_workspace()
        for nome_teste, fn in testes:
            t0 = time.time()
            try:
                detalhe = fn()
                dur = time.time() - t0
                print(f"  ✅ [PASS] {nome_teste} ({dur:.2f}s)")
                print(f"         ↳ {detalhe}")
                passou += 1
            except Exception as exc:
                dur = time.time() - t0
                print(f"  ❌ [FAIL] {nome_teste} ({dur:.2f}s)")
                print(f"         ↳ Erro: {exc}")
                falhou += 1
                break
    finally:
        if not manter_arquivos:
            _limpar_artefatos_workspace()
            for arq, conteudo_orig in snapshots.items():
                try:
                    arq.write_bytes(conteudo_orig)
                except OSError:
                    pass

    qtd_e, qtd_s = _contar_arquivos_workspace()
    dur_total = time.time() - inicio_total

    print("-" * 88)
    if not manter_arquivos:
        status_limpeza = "LIMPO (0 arquivos residuais)" if (qtd_e == 0 and qtd_s == 0) else f"RESÍDUOS ({qtd_e} em entrega/, {qtd_s} em saida/)"
        print(f"🧹 Workspace pós-teste: {status_limpeza}")
    print(f"📊 Resultado Final: {passou}/{len(testes)} suítes aprovadas em {dur_total:.2f}s.")
    print("=" * 88)

    return 0 if (falhou == 0 and (manter_arquivos or (qtd_e == 0 and qtd_s == 0))) else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Executa a suíte automatizada de testes E2E da plataforma NINHO.")
    parser.add_argument(
        "--manter-arquivos",
        action="store_true",
        help="Não limpa as pastas entrega/ e saida/ ao término dos testes (útil para inspeção manual).",
    )
    args = parser.parse_args()
    return executar_suite_completa(manter_arquivos=args.manter_arquivos)


if __name__ == "__main__":
    sys.exit(main())
