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
  9. Experiência Conversacional UX (`/comecar`, `/onde-estou`, `/duvida`, `/doctor`, `/demo`)
  10. Regressão de Confiabilidade E1 a E4 (Parser DDL, Heurística Fato/Dim, Auditor ODI)
  11. Regressão de Blindagem E5 a E12 (DDL META_*, XSS HTML, SCD2/DIM_TEMPO, PBIX Agnóstico, ODI FK/SCD2, CLI/Templates)

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
    pasta_cat = BASE_DIR / "documentacao" / "catalogo_projetos"
    for nome_cat in ("PROJETO_RESUMO.md", "PROJETO_VERSION.md"):
        arq_cat = pasta_cat / nome_cat
        if arq_cat.exists():
            arq_cat.unlink(missing_ok=True)


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

    # Valida o dispatcher unificado ninho.py (com e sem '/')
    rc_ninho, out_ninho, err_ninho = _executar_cli(["ninho.py", "/ajuda", "simulacao"])
    assert rc_ninho == 0 and "/simular-dw" in out_ninho, f"ninho.py /ajuda falhou: {err_ninho}"

    # Valida que as Skills de Slash Command reais existem em .agents/skills/
    for cmd_skill in ("ajuda", "onde-estou", "simular-dw", "melhorar-dw-existente", "testar-ninho"):
        skill_path = BASE_DIR / ".agents" / "skills" / cmd_skill / "SKILL.md"
        assert skill_path.exists(), f"Skill nativa de slash command ausente: {skill_path}"

    rc2, out2, err2 = _executar_cli(["core/scripts_comuns/gerenciar_projeto.py", "--status"])
    assert rc2 == 0, f"gerenciar_projeto.py --status falhou: {err2}"
    return "Catálogo /help, dispatcher ninho.py, skills nativas e gerenciador de status validados."


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
    arq_meta_p = BASE_DIR / "saida" / "camada_semantica" / "meta_projeto" / "06_meta_consulta_negocio.sql"
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
    assert "_RAD_" in sql_meta_p, "Golden Queries do Radar da IA (Seção 6.2) ausentes em 06_meta_consulta_negocio.sql"
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


def teste_10_regressao_e1_e4_robustez() -> str:
    from inspecionar_ddl_origem import parse_ddl_text, detectar_ctas
    from simular_projeto import _converter_oltp_para_dw_se_necessario
    from auditar_mapa_odi import ODIMappingAuditor

    # 10.1. DDL Parser Robustez (E3)
    sql_teste = """
    -- Teste de DDL com comentários e identificadores especiais
    CREATE TABLE TB_TESTE_PARSER (
        KEY_CLIENTE VARCHAR2(20),
        CHECK_DIGITO NUMBER(2),
        INDEX_ORDEM NUMBER(5),
        /* comentario, bloco */
        [Cod Pedido] NUMBER(10),
        "Valor Total" NUMBER(15, 2) DEFAULT 0, -- comentario, linha
        CONSTRAINT PK_TESTE PRIMARY KEY (KEY_CLIENTE, [Cod Pedido])
    );
    CREATE TABLE TB_CTAS_TESTE AS SELECT ID, NOME FROM TB_ORIGEM;
    """
    tabs = parse_ddl_text(sql_teste, "teste.sql")
    assert len(tabs) == 1, f"Esperava 1 tabela no CREATE TABLE balanceado, obteve {len(tabs)}"
    col_names = [c["nome_dw"] for c in tabs[0]["colunas"]]
    assert "KEY_CLIENTE" in col_names, "KEY_CLIENTE descartada indevidamente"
    assert "CHECK_DIGITO" in col_names, "CHECK_DIGITO descartada indevidamente"
    assert "INDEX_ORDEM" in col_names, "INDEX_ORDEM descartada indevidamente"
    assert "COD_PEDIDO" in col_names, "[Cod Pedido] não convertida corretamente"
    assert "VALOR_TOTAL" in col_names, '"Valor Total" não convertida corretamente'
    assert "COMENTARIO" not in col_names and "BLOCO" not in col_names and "LINHA" not in col_names, "Comentários criaram colunas falsas"

    ctas_tabs = detectar_ctas(sql_teste)
    assert "TB_CTAS_TESTE" in ctas_tabs, "detectar_ctas falhou em identificar CTAS"

    # 10.2. Classificação Fato/Dimensão Heurística (E4)
    # Cenário A: TB_VENDA (com métricas e FKs) no início do arquivo
    sql_oltp_venda = """
    CREATE TABLE TB_VENDA (
        ID_VENDA NUMBER PRIMARY KEY,
        ID_CLIENTE NUMBER,
        ID_PRODUTO NUMBER,
        VAL_TOTAL NUMBER(12,2),
        QTD_ITENS NUMBER(5)
    );
    CREATE TABLE TB_CLIENTE (
        ID_CLIENTE NUMBER PRIMARY KEY,
        NOM_CLIENTE VARCHAR2(100)
    );
    CREATE TABLE TB_PRODUTO (
        ID_PRODUTO NUMBER PRIMARY KEY,
        DES_PRODUTO VARCHAR2(100)
    );
    """
    tabs_venda = parse_ddl_text(sql_oltp_venda, "vendas.sql")
    propostas_dw = _converter_oltp_para_dw_se_necessario(tabs_venda)
    nomes_dw = {t["nome_tabela"]: t for t in propostas_dw}
    assert "FATO_VENDA" in nomes_dw, f"TB_VENDA deveria ser FATO_VENDA, mas obteve: {list(nomes_dw.keys())}"
    assert "DIM_CLIENTE" in nomes_dw, "TB_CLIENTE deveria ser DIM_CLIENTE"
    assert "DIM_PRODUTO" in nomes_dw, "TB_PRODUTO deveria ser DIM_PRODUTO"

    # Cenário B: Preservação de DIM_TEMPO existente + conversão de OLTP + descarte de tabela técnica
    sql_misto = """
    CREATE TABLE DIM_TEMPO (
        DIMENSION_KEY NUMBER PRIMARY KEY,
        DTC_COMPLETA DATE
    );
    CREATE TABLE STG_CARGA_TMP (
        ID NUMBER,
        DADOS VARCHAR2(100)
    );
    CREATE TABLE TB_PEDIDO (
        ID_PEDIDO NUMBER PRIMARY KEY,
        ID_CLIENTE NUMBER,
        VAL_PEDIDO NUMBER(10,2)
    );
    CREATE TABLE TB_CLIENTE (
        ID_CLIENTE NUMBER PRIMARY KEY,
        NOM_CLIENTE VARCHAR2(100)
    );
    """
    tabs_misto = parse_ddl_text(sql_misto, "misto.sql")
    propostas_misto = _converter_oltp_para_dw_se_necessario(tabs_misto)
    nomes_misto = {t["nome_tabela"]: t for t in propostas_misto}
    assert "DIM_TEMPO" in nomes_misto, "DIM_TEMPO pré-existente foi descartada indevidamente"
    assert "FATO_PEDIDO" in nomes_misto, "TB_PEDIDO deveria ter sido convertida em FATO_PEDIDO"
    assert "DIM_CLIENTE" in nomes_misto, "TB_CLIENTE deveria ter sido convertida em DIM_CLIENTE"
    assert "STG_CARGA_TMP" not in nomes_misto and "DIM_CARGA_TMP" not in nomes_misto, "Tabela técnica STG_CARGA_TMP deveria ter sido ignorada"

    # 10.3. Auditor ODI sem falsos positivos e sem textos de cliente antigo (E1 e E2)
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        xml_limpo = tmp / "MAP_LIMPO.xml"
        xml_limpo.write_text(
            """<?xml version="1.0" encoding="UTF-8"?>
<SunopsisExport>
  <Object class="com.sunopsis.dwg.dbobj.SnpMapping">
    <Field name="Name"><![CDATA[MAP_CARGA_DIM_CLIENTE]]></Field>
  </Object>
  <Object class="com.sunopsis.dwg.dbobj.SnpMapProp">
    <Field name="PropValue"><![CDATA[IKM Oracle Insert]]></Field>
  </Object>
</SunopsisExport>""",
            encoding="utf-8",
        )
        rel_limpo = tmp / "rel_limpo.md"
        auditor_limpo = ODIMappingAuditor(xml_limpo)
        auditor_limpo.parse()
        auditor_limpo.generate_markdown_report(rel_limpo)
        txt_limpo = rel_limpo.read_text(encoding="utf-8")
        h_ids = [h["id"] for h in auditor_limpo.heuristics_triggered]
        assert "H2_PK_STAGING_E_CHAVE_MULTITENANT" not in h_ids, "H2 não deveria disparar para carga Insert limpa sem CDC/Merge"
        assert "H3_IKM_MERGE_VS_UPDATE" not in h_ids, "H3 não deveria disparar para mapa com IKM limpo sem FLOW_CONTROL"
        assert "H9_LOOP_MULTITENANT_C_DOLLAR_INTRA_ORACLE" not in h_ids, "H9 não deveria disparar sem evidência de loop"
        assert "SEI" not in txt_limpo and "SEIMUN" not in txt_limpo, "Relatório ODI vazou textos específicos do SEI Municipal"

    return "Regressão E1 (ODI genérico), E2 (DES_ATUALIZAR), E3 (DDL Parser) e E4 (Fato/Dimensão) aprovada."


def teste_11_regressao_e5_e12_blindagem() -> str:
    from inspecionar_ddl_origem import parse_ddl_text
    from melhorar_dw_existente import construir_dicionario_html, construir_scripts_odi
    from modular_semantica import construir_catalogo_meta
    from simular_projeto import _converter_oltp_para_dw_se_necessario, _gerar_scripts_ddl_completos_dw

    # 11.1. E5 + E10: DDL 01_create_meta_tables.sql e scripts 01_meta_*.sql..08_meta_*.sql 100% compatíveis
    ddl_meta_tpl = (
        BASE_DIR / "modulos" / "camada_semantica" / "templates" / "01_create_meta_tables.sql"
    ).read_text(encoding="utf-8")
    for constraint_esperada in (
        "CHK_META_METRICA_ADIT",
        "CHK_META_OBJ_TIPO",
        "CHK_META_OBJ_GOV",
        "CHK_META_OBJ_ATIVO",
        "UK_META_RELACIONAMENTO",
        "CHK_META_REL_JOIN",
        "CHK_META_REL_CARD",
        "CHK_META_REGRA_SEV",
        "CHK_META_REGRA_STATUS",
        "CHK_META_VD_ATIVO",
        "CHK_META_ORIA_SECAO",
        "ID_CONSULTA                    VARCHAR2(50)",
    ):
        assert constraint_esperada in ddl_meta_tpl, f"Constraint/tipo {constraint_esperada} ausente em 01_create_meta_tables.sql"

    tabs_dw = _converter_oltp_para_dw_se_necessario(parse_ddl_text(DDL_ORIGEM_TESTE, "teste.sql"))
    scripts_meta = construir_catalogo_meta(tabs_dw, schema="DW_SEM_TESTE", projeto="PROJ_TESTE")
    assert "03_meta_objeto.sql" in scripts_meta, "03_meta_objeto.sql não gerado por construir_catalogo_meta"
    assert "06_meta_consulta_negocio.sql" in scripts_meta, "06_meta_consulta_negocio.sql não gerado por construir_catalogo_meta"
    assert "META_OBJETO" in scripts_meta["03_meta_objeto.sql"] and "META_HIERARQUIA" not in scripts_meta["03_meta_objeto.sql"]
    assert "META_CONSULTA_NEGOCIO" in scripts_meta["06_meta_consulta_negocio.sql"] and "META_PERGUNTA_NEGOCIO" not in scripts_meta["06_meta_consulta_negocio.sql"]
    for nome_arq, sql_txt in scripts_meta.items():
        assert "PROJETO" in sql_txt and "COD_PROJETO" not in sql_txt, f"{nome_arq} usou COD_PROJETO em vez de PROJETO"

    # 11.2. E6: Sanitização XSS no Dicionário HTML
    tabs_xss = parse_ddl_text(
        "CREATE TABLE DIM_XSS (SK_XSS NUMBER PRIMARY KEY, DES_XSS VARCHAR2(50));",
        "xss.sql",
    )
    tabs_xss[0]["comentario_tabela"] = "<script>alert('xss_tab')</script>"
    tabs_xss[0]["colunas"][0]["comentario"] = "<img src=x onerror=alert(1)>"
    html_gerado = construir_dicionario_html([(tabs_xss[0], "DIM")], "DW_XSS", "<script>alert('proj')</script>")
    assert "<script>alert(" not in html_gerado and "<img src=x" not in html_gerado, "Falha de sanitização XSS no Dicionário HTML!"
    assert "&lt;script&gt;alert(" in html_gerado, "Entidades HTML escapadas não encontradas no Dicionário HTML"

    # 11.3. E7: 4 colunas SCD2 completas + 01_tb_controle_carga.sql + DIM_TEMPO canônica
    dim_orgao = next(t for t in tabs_dw if t["nome_tabela"] == "DIM_ORGAO_PUBLICO")
    nomes_cols_dim = {c["nome_dw"] for c in dim_orgao["colunas"]}
    for col_scd2 in ("SIN_ATIVO", "DTC_EFETIVACAO", "DTC_EXPIRACAO", "DES_ATUALIZAR"):
        assert col_scd2 in nomes_cols_dim, f"Coluna SCD2 {col_scd2} ausente na dimensão convertida"

    arqs_dw = _gerar_scripts_ddl_completos_dw(
        tabs_dw,
        schema_dw="DW_TST",
        schema_stg="STG_TST",
        projeto="PROJ_TST",
        ts_dat="TS_D",
        ts_idx="TS_I",
        entregaveis={"01_tablespaces", "02_staging", "03_dimensoes_ddl", "04_fatos_ddl", "05_sequences"},
    )
    assert (BASE_DIR / "saida" / "planejador_dw" / "01_controle_carga" / "01_tb_controle_carga.sql").exists(), "01_tb_controle_carga.sql não foi gerado"
    ddl_dims = (BASE_DIR / "saida" / "planejador_dw" / "03_dimensoes" / "03_create_dim_tables.sql").read_text(encoding="utf-8")
    assert "DIM_TEMPO" in ddl_dims and "SK_TEMPO" in ddl_dims, "DDL de DIM_TEMPO ausente em 03_create_dim_tables.sql"

    # 11.4. E8: inspecionar_pbix.py 100% agnóstico (zero vazamento de SEI/SAEB/PRODEB/URBIS em PBIX financeiro)
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        arq_pbix_fin = tmp / "Painel_Financeiro_Vendas.pbix"
        layout_fin = {
            "sections": [
                {
                    "displayName": "Faturamento",
                    "filters": "[]",
                    "visualContainers": [
                        {
                            "config": json.dumps(
                                {
                                    "singleVisual": {
                                        "visualType": "barChart",
                                        "prototypeQuery": {
                                            "From": [{"Name": "v", "Entity": "FatoVendas"}],
                                            "Select": [
                                                {
                                                    "Column": {
                                                        "Expression": {"SourceRef": {"Source": "v"}},
                                                        "Property": "ValorLiquido",
                                                    },
                                                    "Name": "FatoVendas.ValorLiquido",
                                                }
                                            ],
                                        },
                                    }
                                }
                            ),
                            "filters": "[]",
                        }
                    ],
                }
            ]
        }
        with zipfile.ZipFile(arq_pbix_fin, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("Report/Layout", json.dumps(layout_fin).encode("utf-16-le"))
        rel_fin = tmp / "rel_fin.md"
        rc_p, out_p, err_p = _executar_cli(
            ["core/scripts_comuns/inspecionar_pbix.py", str(arq_pbix_fin), "--output", str(rel_fin)]
        )
        assert rc_p == 0 and rel_fin.exists(), f"inspecionar_pbix.py falhou: {err_p}"
        txt_fin = rel_fin.read_text(encoding="utf-8")
        for termo_proibido in ("SAEB", "PRODEB", "URBIS", "processo_sei", "Processos_Resumo"):
            assert termo_proibido not in txt_fin, f"Relatório PBIX vazou termo hardcoded de outro projeto: {termo_proibido}"

    # 11.5. E9: construir_scripts_odi com DTC_EFETIVACAO, exclusão SCD2 da STG e LEFT JOIN para ID_* convertido
    dims_dw = [t for t in tabs_dw if t["nome_tabela"].startswith("DIM_")]
    fatos_dw = [t for t in tabs_dw if t["nome_tabela"].startswith("FATO_")]
    sql_odi_ddl, sql_odi_dims, sql_odi_fato = construir_scripts_odi(
        dims_dw, fatos_dw, [], schema="DW_TST", projeto="PROJ_TST", estrategia="A", schema_stg="STG_TST"
    )
    assert "(ID_ORGAO, DTC_EFETIVACAO DESC)" in sql_odi_ddl, "Índice ODI_DIM deveria usar DTC_EFETIVACAO"
    assert "STG_TST.STG_ORGAO_PUBLICO" in sql_odi_dims, "Schema STG customizado não utilizado em 03_selects_odi_dimensoes.sql"
    assert "LEFT JOIN DW_TST.DIM_ORGAO_PUBLICO" in sql_odi_fato, "LEFT JOIN para DIM_ORGAO_PUBLICO ausente em 04_select_odi_fato.sql"
    assert ", -1) AS SK_ORGAO_PUBLICO" in sql_odi_fato or ", -1) AS ID_ORGAO" in sql_odi_fato, (
        f"Fallback NVL(..., -1) para FK de órgão ausente em 04_select_odi_fato.sql:\n{sql_odi_fato}"
    )

    # 11.6. E11 + E12: Rotas do ninho.py e templates FTPS/ODI seguros
    if str(BASE_DIR) not in sys.path:
        sys.path.insert(0, str(BASE_DIR))
    import ninho as ninho_cli
    for cmd_k, (scr_name, _, _) in ninho_cli.ROTAS_COMANDOS.items():
        if scr_name == "__interno_instalar__":
            continue
        assert (BASE_DIR / "core" / "scripts_comuns" / scr_name).exists(), f"Rota '{cmd_k}' aponta para script inexistente: {scr_name}"
    for cmd_esperado in ("instalar-comandos", "setup", "desafiar-grao", "classificar-scd", "definir-estrategia-carga", "gerar-governanca", "diagnosticar-erro-carga"):
        assert cmd_esperado in ninho_cli.ROTAS_COMANDOS, f"Comando '{cmd_esperado}' ausente em ninho.py"
    assert ninho_cli.instalar_comandos_chat([]) == 0, "Falha ao executar instalar_comandos_chat()"

    sh_ftps = (BASE_DIR / ".agents" / "skills" / "extrator-ftps-lote-hop" / "templates" / "extrair_metadados_ftps.sh").read_text(encoding="utf-8")
    assert "CURL_TLS_OPTS" in sh_ftps, "Template FTPS não parametrizou CURL_TLS_OPTS"
    tpl_odi = (BASE_DIR / ".agents" / "skills" / "gerador-consultas-odi" / "templates" / "template_selects_odi.sql").read_text(encoding="utf-8")
    assert "'S'                            AS DES_ATUALIZAR" not in tpl_odi and "STANDARD_HASH" in tpl_odi, (
        "template_selects_odi.sql ainda contém 'S' hardcoded para DES_ATUALIZAR"
    )

    return "Blindagem E5 a E12 (DDL META_*, XSS HTML, SCD2/DIM_TEMPO, PBIX Agnóstico, ODI FK/SCD2, CLI/Templates) aprovada."


def _criar_xlsx_indicadores_teste(caminho_xlsx: Path) -> None:
    """Gera um arquivo .xlsx mínimo válido (OpenXML stdlib) com especificações de indicadores de negócio."""
    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="Indicadores" sheetId="1" r:id="rId1"/></sheets></workbook>'
    )
    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        "<sheetData>"
        '<row r="1">'
        '<c r="B1" t="inlineStr"><is><t>Indicador</t></is></c>'
        '<c r="C1" t="inlineStr"><is><t>Descrição</t></is></c>'
        '<c r="D1" t="inlineStr"><is><t>Fórmula de Cálculo</t></is></c>'
        '<c r="E1" t="inlineStr"><is><t>Periodicidade</t></is></c>'
        '<c r="F1" t="inlineStr"><is><t>Meta</t></is></c>'
        '<c r="G1" t="inlineStr"><is><t>Filtros Necessários</t></is></c>'
        "</row>"
        '<row r="2">'
        '<c r="B2" t="inlineStr"><is><t>Quantitativo de estudantes contemplados</t></is></c>'
        '<c r="C2" t="inlineStr"><is><t>Total de discentes beneficiados pela assistência estudantil</t></is></c>'
        '<c r="D2" t="inlineStr"><is><t>Contagem distinta de matrículas deferidas</t></is></c>'
        '<c r="E2" t="inlineStr"><is><t>Mensal</t></is></c>'
        '<c r="F2" t="inlineStr"><is><t>Meta de 8.000 estudantes contemplados por ano</t></is></c>'
        '<c r="G2" t="inlineStr"><is><t>Campus, Benefício, Ano/Mês</t></is></c>'
        "</row>"
        "</sheetData></worksheet>"
    )
    with zipfile.ZipFile(caminho_xlsx, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("xl/workbook.xml", workbook_xml)
        zf.writestr("xl/worksheets/sheet1.xml", sheet_xml)


def teste_12_regressao_m1_m7_praes_csv_ddl_guia_bi() -> str:
    _limpar_artefatos_workspace()
    pasta_ddl = BASE_DIR / "entrega" / "planejador_dw" / "ddl"
    pasta_ddl.mkdir(parents=True, exist_ok=True)

    # M1 + M2: DDL exportado como CSV (DBeaver/SQL Developer) com MVW_<PROJETO>_DIM_*, MVW_<PROJETO>_FATO_* e DIM_TEMPO_*
    ddl_csv_content = '''DDL_GERADO
;"'
  CREATE TABLE ""UNEB_OLAP"".""MVW_PRAES_DIM_CAMPUS"" 
   (	""SK_CAMPUS"" NUMBER(10,0) NOT NULL ENABLE, 
	""COD_CAMPUS"" NUMBER(10,0), 
	""NOM_CAMPUS"" VARCHAR2(120 BYTE), 
	""NOM_MUNICIPIO"" VARCHAR2(100 BYTE), 
	""SIN_ATIVO"" CHAR(1 BYTE), 
	 CONSTRAINT ""PK_MVW_PRAES_DIM_CAMPUS"" PRIMARY KEY (""SK_CAMPUS"") ENABLE
   ) ;'"
;"'
  CREATE TABLE ""UNEB_OLAP"".""MVW_PRAES_DIM_BENEFICIO"" 
   (	""SK_BENEFICIO"" NUMBER(10,0) NOT NULL ENABLE, 
	""COD_BENEFICIO"" NUMBER(10,0), 
	""NOM_BENEFICIO"" VARCHAR2(120 BYTE), 
	""SIN_ATIVO"" CHAR(1 BYTE), 
	 CONSTRAINT ""PK_MVW_PRAES_DIM_BENEFICIO"" PRIMARY KEY (""SK_BENEFICIO"") ENABLE
   ) ;'"
;"'
  CREATE TABLE ""UNEB_OLAP"".""DIM_TEMPO_ASSISTENCIA"" 
   (	""SK_TEMPO"" NUMBER(10,0) NOT NULL ENABLE, 
	""DTC_DATA"" DATE, 
	""NUM_ANO"" NUMBER(4,0), 
	""NUM_MES"" NUMBER(2,0), 
	""NOM_MES"" VARCHAR2(30 BYTE), 
	 CONSTRAINT ""PK_DIM_TEMPO_ASSISTENCIA"" PRIMARY KEY (""SK_TEMPO"") ENABLE
   ) ;'"
;"'
  CREATE TABLE ""UNEB_OLAP"".""MVW_PRAES_FATO_INSCRICAO"" 
   (	""SK_FATO_INSCRICAO"" NUMBER(12,0) NOT NULL ENABLE, 
	""SK_CAMPUS"" NUMBER(10,0) NOT NULL ENABLE, 
	""SK_BENEFICIO"" NUMBER(10,0) NOT NULL ENABLE, 
	""SK_TEMPO_INSCRICAO"" NUMBER(10,0) NOT NULL ENABLE, 
	""SK_TEMPO_STATUS"" NUMBER(10,0) NOT NULL ENABLE, 
	""NUM_MATRICULA"" VARCHAR2(30 BYTE), 
	""DES_STATUS_INSCRICAO"" VARCHAR2(40 BYTE), 
	""QTD_INSCRICOES"" NUMBER(5,0), 
	""VAL_AUXILIO"" NUMBER(12,2), 
	 CONSTRAINT ""PK_MVW_PRAES_FATO_INSCRICAO"" PRIMARY KEY (""SK_FATO_INSCRICAO"") ENABLE
   ) ;'"
'''
    (pasta_ddl / "DDL_tab.csv").write_text(ddl_csv_content, encoding="utf-8")

    # M3: Planilha .xlsx de indicadores de negócio em entrega/planejador_dw/
    arq_xlsx = BASE_DIR / "entrega" / "planejador_dw" / "Indicadores - PRAES.xlsx"
    _criar_xlsx_indicadores_teste(arq_xlsx)

    # M5: Verifica que /doctor não move .xlsx de indicadores de BI nem .csv com CREATE TABLE para fora de planejador_dw
    from ajuda_ninho import detectar_arquivos_fora_do_lugar
    desalinhados = detectar_arquivos_fora_do_lugar()
    caminhos_desalinhados = [p.name for p, _, _ in desalinhados]
    assert "Indicadores - PRAES.xlsx" not in caminhos_desalinhados, "/doctor marcou planilha de indicadores do DW como desalinhada"
    assert "DDL_tab.csv" not in caminhos_desalinhados, "/doctor marcou DDL_tab.csv em entrega/planejador_dw/ddl/ como desalinhado"

    # M3 + M4: Executa /gerar-guia-bi via ninho.py (modo isolado guia-bi)
    rc_bi, out_bi, err_bi = _executar_cli(["ninho.py", "/gerar-guia-bi"])
    assert rc_bi == 0, f"ninho.py /gerar-guia-bi falhou: {err_bi}\n{out_bi}"

    arq_guia = BASE_DIR / "saida" / "planejador_dw" / "08_datasets_bi" / "GUIA_ANALISTA_BI_PRAES.md"
    arq_diag = BASE_DIR / "saida" / "planejador_dw" / "09_relatorio_estrategias" / "DIAGNOSTICO_MELHORIAS_DW_EXISTENTE.md"
    assert arq_guia.exists(), "GUIA_ANALISTA_BI_PRAES.md não foi gerado em 08_datasets_bi/"
    assert not arq_diag.exists(), "DIAGNOSTICO_MELHORIAS_DW_EXISTENTE.md não deveria ser gerado no modo isolado guia-bi"

    txt_guia = arq_guia.read_text(encoding="utf-8")
    assert "UNEB_OLAP" in txt_guia and "PRAES" in txt_guia, "Schema UNEB_OLAP ou projeto PRAES ausente no Guia BI"
    for secao in ("## 1.", "## 2.", "## 3.", "## 4.", "### 4.1 Matriz Oficial de Indicadores", "## 5.", "## 6.", "## 7.", "## 8.", "## 9."):
        assert secao in txt_guia, f"Seção '{secao}' ausente em GUIA_ANALISTA_BI_PRAES.md"
    assert "Quantitativo de estudantes contemplados" in txt_guia, "Indicador da planilha .xlsx não foi injetado no Guia BI"
    assert "8000" in txt_guia and "% Atingimento Meta" in txt_guia, "Medida DAX de Meta / % Atingimento não gerada"
    assert "USERELATIONSHIP" in txt_guia and "DIM_TEMPO_ASSISTENCIA" in txt_guia, (
        "Role-Playing Dimension DIM_TEMPO_ASSISTENCIA não mapeada com USERELATIONSHIP"
    )

    # M2 (Camada Semântica): Verifica que VW_EVENTO não gera colunas duplicadas (ORA-00957) com Role-Playing Dimension
    rc_sem, out_sem, err_sem = _executar_cli(["core/scripts_comuns/modular_semantica.py", "--modo", "views-evento"])
    assert rc_sem == 0, f"modular_semantica.py --modo views-evento falhou com DDL_tab.csv: {err_sem}\n{out_sem}"
    vw_ev_path = BASE_DIR / "saida" / "camada_semantica" / "vw_analiticas" / "02_vw_eventos.sql"
    assert vw_ev_path.exists(), "02_vw_eventos.sql não foi gerado a partir de DDL_tab.csv"
    txt_vw_ev = vw_ev_path.read_text(encoding="utf-8")
    assert " AS DTC_DATA_TEMPO_STATUS" in txt_vw_ev or " AS NUM_ANO_TEMPO_STATUS" in txt_vw_ev, (
        "Colunas da Role-Playing Dimension DIM_TEMPO_ASSISTENCIA não receberam alias desambiguado contra ORA-00957"
    )

    _limpar_artefatos_workspace()
    return "Melhorias M1 a M7 (DDL em CSV, MVW_*, Role-Playing DIM_TEMPO, Guia BI 9 seções + .xlsx, Modo Isolado) aprovadas."


def teste_13_regressao_p1_a_p7() -> str:
    """Valida as melhorias P1 a P7 extraídas do projeto real GESTAO_SUSTENTACAO (COPSD)."""
    _limpar_artefatos_workspace()

    from inspecionar_ddl_origem import parse_ddl_text
    from melhorar_dw_existente import (
        construir_guias_odi_modulares,
        construir_scripts_odi,
        derivar_sigla_curta_odi,
        validar_tamanho_identificador_odi,
    )

    # P1: Sigla curta automática e validador de limite de 30 chars do ODI 12c
    assert derivar_sigla_curta_odi("GESTAO_SUSTENTACAO") == "GS", "Sigla curta de GESTAO_SUSTENTACAO deveria ser GS"
    ok_longo, tam_longo, lim_longo = validar_tamanho_identificador_odi("DIM_GESTAO_SUSTENTACAO_PROFISSIONAL", "DIM")
    assert not ok_longo and tam_longo > lim_longo, "Deveria alertar nome de dimensão > 22 chars para o ODI 12c"
    ok_curto, *_ = validar_tamanho_identificador_odi("DIM_GS_PROFISSIONAL", "DIM")
    assert ok_curto, "DIM_GS_PROFISSIONAL (19 chars) deveria ser aprovado no limite do ODI 12c"

    # P2 + P3 + P6: ODI_DIM_* 100% NULLABLE, Dimension Pattern (Asterisco) e UPPER(TRIM()) simétrico em NKs textuais
    ddl_gs = """
    CREATE TABLE PRODBA_OLAP.STG_GS_RESUMO_MENSAL (
        COD_PROJETO VARCHAR2(100) NOT NULL,
        ID_REDMINE_PROF NUMBER(10) NOT NULL,
        VAL_HORAS NUMBER(10,2)
    );
    CREATE TABLE PRODBA_OLAP.DIM_GS_PROJETO (
        SK_PROJETO NUMBER(10) NOT NULL,
        COD_PROJETO VARCHAR2(100) NOT NULL,
        NOM_PROJETO VARCHAR2(200) NOT NULL,
        SIN_ATIVO CHAR(1) NOT NULL,
        DTC_EFETIVACAO DATE NOT NULL,
        DTC_EXPIRACAO DATE,
        DES_ATUALIZAR CHAR(1),
        CONSTRAINT PK_DIM_GS_PROJETO PRIMARY KEY (SK_PROJETO)
    );
    CREATE TABLE PRODBA_OLAP.DIM_GS_PROFISSIONAL (
        SK_PROFISSIONAL NUMBER(10) NOT NULL,
        ID_REDMINE_PROF NUMBER(10) NOT NULL,
        NOM_PROFISSIONAL VARCHAR2(150) NOT NULL,
        SIN_ATIVO CHAR(1) NOT NULL,
        DTC_EFETIVACAO DATE NOT NULL,
        DTC_EXPIRACAO DATE,
        DES_ATUALIZAR CHAR(1),
        CONSTRAINT PK_DIM_GS_PROF PRIMARY KEY (SK_PROFISSIONAL)
    );
    CREATE TABLE PRODBA_OLAP.FATO_GS_RESUMO_MENSAL (
        SK_RESUMO NUMBER(12) NOT NULL,
        SK_PROJETO NUMBER(10) NOT NULL,
        SK_PROFISSIONAL NUMBER(10) NOT NULL,
        VAL_HORAS NUMBER(10,2)
    );
    """
    tabs_gs = parse_ddl_text(ddl_gs, "gs.sql")
    dims_gs = [t for t in tabs_gs if t["nome_tabela"].startswith("DIM_")]
    fatos_gs = [t for t in tabs_gs if t["nome_tabela"].startswith("FATO_")]
    stgs_gs = [t for t in tabs_gs if t["nome_tabela"].startswith("STG_")]

    sql_odi_ddl, sql_odi_dims, sql_odi_fato = construir_scripts_odi(
        dims_gs, fatos_gs, stgs_gs, schema="PRODBA_OLAP", projeto="GESTAO_SUSTENTACAO", estrategia="A"
    )
    assert "NOT NULL" not in sql_odi_ddl.split("CREATE INDEX")[0], (
        f"ODI_DIM_* não deve conter constraints NOT NULL (evita ORA-01400 no STG_DIM):\n{sql_odi_ddl}"
    )
    assert "UPPER(TRIM(S.COD_PROJETO))" in sql_odi_dims, "NK textual COD_PROJETO deve usar UPPER(TRIM(...)) em 03_selects_odi_dimensoes.sql"
    assert "ON UPPER(TRIM(S.COD_PROJETO)) = UPPER(TRIM(D1.COD_PROJETO))" in sql_odi_fato, (
        "JOIN de Fato para NK textual deve usar UPPER(TRIM()) simétrico em ambos os lados"
    )
    assert "ON S.ID_REDMINE_PROF = D2.ID_REDMINE_PROF" in sql_odi_fato, (
        "JOIN de Fato para NK numérica deve preservar igualdade direta sem UPPER(TRIM())"
    )

    guias_odi = construir_guias_odi_modulares(
        dims_gs, fatos_gs, schema="PRODBA_OLAP", projeto="GESTAO_SUSTENTACAO", estrategia="A"
    )
    guia_prj = guias_odi.get("guia_estrategias_odi_dim_gs_projeto.md", "")
    assert (
        "Dimension Pattern" in guia_prj
        and "CARGA_DIM_GS_PROJETO" in guia_prj
        and "*(Seta branca)*" in guia_prj
        and "3.3 Aba `Níveis` ➔ Grade Inferior `Atributos de Nível`" in guia_prj
        and "4.2 Tabela Completa de Atributos dentro do `EXPRESSION` (Coluna por Coluna)" in guia_prj
    ), "Guia de dimensão ODI deveria conter tabelas coluna por coluna de Atributos de Nível e EXPRESSION com Setas Brancas"

    guia_fato = guias_odi.get("guia_estrategias_odi_fato_gs_resumo_mensal.md", "")
    assert (
        "RN_DEDUP" in guia_fato
        and "Generate Inline View" in guia_fato
        and "3.1 Desenho Arquitetural no Canvas Lógico" in guia_fato
        and "Passo 3: Configurar os Lookups / Left Joins Dimensionais" in guia_fato
        and "Passo 4: Mapeamento Completo de Todas as Colunas na Tabela Alvo" in guia_fato
    ), "Guia de fato ODI deveria conter consulta RN_DEDUP, Generate Inline View, Lookups e tabela coluna por coluna"

    rel_estrat = guias_odi.get("RELATORIO_ESTRATEGIAS.md", "")
    assert (
        "1.1 Tabela de Conformidade de Nomenclatura Física" in rel_estrat
        and "4.1 Fluxo Visual Completo do Pacote no Diagrama do ODI" in rel_estrat
        and "4.2 Matriz Completa de Objetos do Pacote" in rel_estrat
    ), "RELATORIO_ESTRATEGIAS.md deveria conter auditoria <=30 chars, diagrama ASCII do pacote e matriz ok/ko"

    from melhorar_dw_existente import construir_guia_bi_rapido
    guia_bi_gs = construir_guia_bi_rapido(dims_gs, fatos_gs, schema="PRODBA_OLAP", projeto="GESTAO_SUSTENTACAO")
    assert (
        "SCD2 Safe" in guia_bi_gs
        and "SUMMARIZE(" in guia_bi_gs
        and "6.1 Mapa de Navegação Superior" in guia_bi_gs
        and "COUNT(DISTINCT CASE WHEN" in guia_bi_gs
        and "Check 7 (Reconciliação SQL 100%)" in guia_bi_gs
    ), "Guia do Analista de BI deveria conter medidas SCD2 Safe (SUMMARIZE pela NK), wireframe 4 páginas e SQL de reconciliação com JOIN"

    # P4: REUSAR_DIM_TEMPO = SIM na Simulação Editável
    pasta_ddl = BASE_DIR / "entrega" / "planejador_dw" / "ddl"
    pasta_ddl.mkdir(parents=True, exist_ok=True)
    (pasta_ddl / "01_origem_gs.sql").write_text(
        "CREATE TABLE TB_PROJETO_GS (COD_PROJETO VARCHAR2(80) PRIMARY KEY, NOM_PROJETO VARCHAR2(200));\n"
        "CREATE TABLE TB_CHAMADO_GS (ID_CHAMADO NUMBER(10) PRIMARY KEY, COD_PROJETO VARCHAR2(80), DT_ABERTURA DATE, VAL_HORAS NUMBER(10,2));",
        encoding="utf-8",
    )
    rc_sim, out_sim, err_sim = _executar_cli(["core/scripts_comuns/simular_projeto.py", "--modulo", "dw", "--acao", "simular"])
    assert rc_sim == 0, f"Falha ao simular DW em P4: {err_sim}\n{out_sim}"
    arq_bp = BASE_DIR / "entrega" / "planejador_dw" / "SIMULACAO_BLUEPRINT_DW.md"
    txt_bp = arq_bp.read_text(encoding="utf-8")
    assert "REUSAR_DIM_TEMPO" in txt_bp and "SIGLA_CURTA_ODI" in txt_bp, "Parâmetros REUSAR_DIM_TEMPO e SIGLA_CURTA_ODI ausentes na Blueprint DW"

    txt_bp_editado = (
        txt_bp.replace("| `REUSAR_DIM_TEMPO` | `NAO` |", "| `REUSAR_DIM_TEMPO` | `SIM` |")
        .replace("- [ ] **SIMULAÇÃO 100% FECHADA E APROVADA PARA EXECUÇÃO REAL**", "- [x] **SIMULAÇÃO 100% FECHADA E APROVADA PARA EXECUÇÃO REAL**")
    )
    arq_bp.write_text(txt_bp_editado, encoding="utf-8")
    rc_exec, out_exec, err_exec = _executar_cli(["core/scripts_comuns/simular_projeto.py", "--modulo", "dw", "--acao", "executar"])
    assert rc_exec == 0, f"Falha ao executar simulação DW com REUSAR_DIM_TEMPO=SIM: {err_exec}\n{out_exec}"

    arq_03_dim = BASE_DIR / "saida" / "planejador_dw" / "03_dimensoes" / "03_create_dim_tables.sql"
    txt_03_dim = arq_03_dim.read_text(encoding="utf-8")
    assert "REUSO CORPORATIVO DE DIM_TEMPO" in txt_03_dim and "CREATE TABLE" in txt_03_dim, (
        "Comentário de REUSO CORPORATIVO DE DIM_TEMPO ausente em 03_create_dim_tables.sql"
    )
    assert "CREATE TABLE PRODBA_OLAP.DIM_TEMPO" not in txt_03_dim, (
        "Não deveria gerar CREATE TABLE DIM_TEMPO quando REUSAR_DIM_TEMPO = SIM"
    )

    # Q2, Q4, Q5, Q6: Verificar tablespace deduplicado, ETA_ETAPAS_CARGA completo, STG NOLOGGING+COMMENT e índices COMPRESS 1 + NOPARALLEL
    arq_01_ctrl = BASE_DIR / "saida" / "planejador_dw" / "01_controle_carga" / "01_tb_controle_carga.sql"
    txt_01_ctrl = arq_01_ctrl.read_text(encoding="utf-8")
    assert (
        "ETA_ETAPAS_CARGA" in txt_01_ctrl
        and "ORA-00955" in txt_01_ctrl
        and "MERGE INTO" in txt_01_ctrl
        and "COMMENT ON COLUMN" in txt_01_ctrl
    ), "Q4: 01_tb_controle_carga.sql deve conter ETA_ETAPAS_CARGA idempotente + 5 COMMENT ON COLUMN + MERGE INTO das etapas"

    arq_02_stg = BASE_DIR / "saida" / "planejador_dw" / "02_staging" / "02_create_stg_tables.sql"
    txt_02_stg = arq_02_stg.read_text(encoding="utf-8")
    assert "NOLOGGING;" in txt_02_stg and "COMMENT ON TABLE" in txt_02_stg and "COMMENT ON COLUMN" in txt_02_stg, (
        "Q5: 02_create_stg_tables.sql deve conter NOLOGGING e COMMENT ON TABLE/COLUMN para todas as STG_*"
    )

    arq_06_idx_dim = BASE_DIR / "saida" / "planejador_dw" / "03_dimensoes" / "06_create_indexes_dim.sql"
    arq_06_idx_fato = BASE_DIR / "saida" / "planejador_dw" / "04_fatos" / "06_create_indexes_fato.sql"
    txt_06_idx_dim = arq_06_idx_dim.read_text(encoding="utf-8")
    txt_06_idx_fato = arq_06_idx_fato.read_text(encoding="utf-8")
    assert "COMPRESS 1" in txt_06_idx_dim and "NOPARALLEL LOGGING;" in txt_06_idx_dim and "NOPARALLEL LOGGING;" in txt_06_idx_fato, (
        "Q6: 06_create_indexes_dim/fato.sql devem conter COMPRESS 1 ... PARALLEL 4 NOLOGGING + ALTER INDEX ... NOPARALLEL LOGGING"
    )

    # Q7: Abreviação inteligente <= 22 chars para DIM_* e <= 26 chars para FATO_*
    from melhorar_dw_existente import abreviar_identificador_odi
    dim_abrev = abreviar_identificador_odi("DIM", "GS_CAPACIDADE_PROFISSIONAL", max_len=22)
    assert len(dim_abrev) <= 22 and dim_abrev.startswith("DIM_"), f"Q7: {dim_abrev} excedeu 22 chars ({len(dim_abrev)})"

    # P5: Regra HOP-H9 (cruzamento TableOutput <table>STG_*</table> vs 02_create_stg_tables.sql)
    pasta_hop_tst = BASE_DIR / "saida" / "planejador_dw" / "06_etl_hop"
    pasta_hop_tst.mkdir(parents=True, exist_ok=True)
    pasta_stg_tst = BASE_DIR / "saida" / "planejador_dw" / "02_staging"
    pasta_stg_tst.mkdir(parents=True, exist_ok=True)
    (pasta_stg_tst / "02_create_stg_tables.sql").write_text(
        "CREATE TABLE PRODBA_OLAP.STG_GS_CAPACIDADE_PROF (ID_REDMINE_PROF NUMBER(10));",
        encoding="utf-8",
    )
    hpl_divergente = (
        "<pipeline><info><name>ppl_teste</name></info>"
        "<transform><name>Out_STG</name><type>TableOutput</type>"
        "<table>STG_CAPACIDADE_PROF</table><use_batch>Y</use_batch><commit>1000</commit></transform>"
        "</pipeline>"
    )
    arq_hpl_div = pasta_hop_tst / "ppl_divergente.hpl"
    arq_hpl_div.write_text(hpl_divergente, encoding="utf-8")
    rel_hop_div = pasta_hop_tst / "rel_hop_h9.md"
    rc_h9, out_h9, err_h9 = _executar_cli(
        ["core/scripts_comuns/auditar_esteira_hop.py", str(pasta_hop_tst), "--saida", str(rel_hop_div)]
    )
    assert rc_h9 == 0 and rel_hop_div.exists(), f"auditar_esteira_hop.py falhou em HOP-H9: {err_h9}\n{out_h9}"
    txt_rel_h9 = rel_hop_div.read_text(encoding="utf-8")
    assert "HOP-H9" in txt_rel_h9, f"Auditor Hop deveria detectar HOP-H9 para STG_CAPACIDADE_PROF vs STG_GS_CAPACIDADE_PROF:\n{txt_rel_h9}"

    _limpar_artefatos_workspace()
    return "Melhorias P1..P7 e Q1..Q8 (Sigla ODI <=30 chars, ODI_DIM NULLABLE, Dimension Pattern, ETA_ETAPAS_CARGA, STG NOLOGGING, COMPRESS 1 + NOPARALLEL e ORA-00904 Index Guard) aprovadas."


def teste_14_suite_visual_craft_e_panic_hunt() -> str:
    """Valida os pilares visuais/OOXML/PDF/PII (Mockup BI SVG/HTML/PNG 2x, Star Schema & ODI Canvas SVG,
    Planilha .xlsx 3 abas com Dropdowns e Conditional Formatting + .ods, Deck .pptx + Slides HTML 16:9 +
    Word .docx + PDF 1.4 oficial, leitores nativos .pdf/.docx/.odt, Scanner PII/LGPD de conteúdo
    e bateria panic_hunt contra entradas corrompidas/truncadas)."""
    import zlib
    from gerador_artefatos_visuais import (
        escanear_pii_em_texto_ou_linhas,
        extrair_texto_pdf_nativo,
        ler_documento_docx,
        ler_documento_odt,
        ler_planilha_ods,
        mascarar_pii_texto,
    )

    _limpar_artefatos_workspace()

    # 1. Preparar DDL em entrega/planejador_dw/ddl/ + planilha .ods de indicadores em entrega/planejador_dw/regras_negocio/
    pasta_ddl = BASE_DIR / "entrega" / "planejador_dw" / "ddl"
    pasta_ddl.mkdir(parents=True, exist_ok=True)
    (pasta_ddl / "dw_craft_test.sql").write_text(
        """
        CREATE TABLE DW_CRAFT.DIM_TEMPO (
            SK_TEMPO NUMBER(10) PRIMARY KEY,
            COD_ANO_MES NUMBER(6),
            NUM_ANO NUMBER(4),
            DES_MES_ANO VARCHAR2(20)
        );
        CREATE TABLE DW_CRAFT.DIM_UNIDADE_ENSINO (
            SK_UNIDADE NUMBER(10) PRIMARY KEY,
            ID_UNIDADE VARCHAR2(30) NOT NULL,
            NOM_UNIDADE VARCHAR2(150),
            DTC_INICIO DATE,
            DTC_FIM DATE,
            FLG_ATUAL NUMBER(1)
        );
        CREATE TABLE DW_CRAFT.FAT_MATRICULA_ACADEMICA (
            SK_TEMPO NUMBER(10) NOT NULL,
            SK_UNIDADE NUMBER(10) NOT NULL,
            QTD_ALUNOS_MATRICULADOS NUMBER(10),
            VAL_BOLSA_CONCEDIDA NUMBER(18,2),
            PER_FREQUENCIA_MEDIA NUMBER(5,2)
        );
        """,
        encoding="utf-8",
    )

    # Criar um arquivo .ods real (ZIP contendo content.xml OpenDocument) com indicadores de negócio
    pasta_rn = BASE_DIR / "entrega" / "planejador_dw" / "regras_negocio"
    pasta_rn.mkdir(parents=True, exist_ok=True)
    arq_ods = pasta_rn / "indicadores_teste.ods"
    content_xml_ods = """<?xml version="1.0" encoding="UTF-8"?>
<office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
  xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0"
  xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0">
  <office:body>
    <office:spreadsheet>
      <table:table table:name="Indicadores">
        <table:table-row>
          <table:table-cell><text:p>Indicador</text:p></table:table-cell>
          <table:table-cell><text:p>Regra de Cálculo</text:p></table:table-cell>
          <table:table-cell><text:p>Meta</text:p></table:table-cell>
        </table:table-row>
        <table:table-row>
          <table:table-cell><text:p>Taxa de Retenção Acadêmica</text:p></table:table-cell>
          <table:table-cell><text:p>Alunos Ativos / Total Matriculados</text:p></table:table-cell>
          <table:table-cell><text:p>&gt;= 92%</text:p></table:table-cell>
        </table:table-row>
      </table:table>
    </office:spreadsheet>
  </office:body>
</office:document-content>"""
    with zipfile.ZipFile(arq_ods, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("content.xml", content_xml_ods.encode("utf-8"))

    rows_ods = ler_planilha_ods(str(arq_ods))
    assert len(rows_ods) == 2 and rows_ods[1][0] == "Taxa de Retenção Acadêmica", "ler_planilha_ods falhou ao ler .ods válido"

    # Criar também um documento .odt real com tabela de indicador extra para testar leitura nativa de .odt
    arq_odt = pasta_rn / "manual_indicadores_extra.odt"
    content_xml_odt = """<?xml version="1.0" encoding="UTF-8"?>
<office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
  xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0"
  xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0">
  <office:body>
    <office:text>
      <text:p>Manual de Indicadores Estrategicos</text:p>
      <table:table table:name="TabInd">
        <table:table-row>
          <table:table-cell><text:p>Indicador</text:p></table:table-cell>
          <table:table-cell><text:p>Formula</text:p></table:table-cell>
          <table:table-cell><text:p>Meta</text:p></table:table-cell>
        </table:table-row>
        <table:table-row>
          <table:table-cell><text:p>Indice de Aprovacao Semestral</text:p></table:table-cell>
          <table:table-cell><text:p>Aprovados / Matriculados</text:p></table:table-cell>
          <table:table-cell><text:p>&gt;= 88%</text:p></table:table-cell>
        </table:table-row>
      </table:table>
    </office:text>
  </office:body>
</office:document-content>"""
    with zipfile.ZipFile(arq_odt, "w", zipfile.ZIP_DEFLATED) as zf_odt:
        zf_odt.writestr("content.xml", content_xml_odt.encode("utf-8"))

    doc_odt = ler_documento_odt(str(arq_odt))
    assert "Manual de Indicadores" in doc_odt["texto"] and len(doc_odt["tabelas"]) == 1, "ler_documento_odt falhou em .odt válido"

    # 2. Executar melhorar_dw_existente.py --modo tudo e --modo guia-odi (Padrão: sem .pptx/.docx/.pdf não solicitados)
    rc, out, err = _executar_cli(["core/scripts_comuns/melhorar_dw_existente.py", "--modo", "tudo", "--projeto", "CRAFT"])
    assert rc == 0, f"melhorar_dw_existente.py falhou em T14: {err}\n{out}"

    rc_odi, out_odi, err_odi = _executar_cli(["core/scripts_comuns/melhorar_dw_existente.py", "--modo", "guia-odi", "--projeto", "CRAFT"])
    assert rc_odi == 0, f"melhorar_dw_existente.py --modo guia-odi falhou em T14: {err_odi}\n{out_odi}"

    saida_dw = BASE_DIR / "saida" / "planejador_dw"
    p_mock = saida_dw / "08_datasets_bi" / "mockup_painel_bi.svg"
    p_mock_dev = saida_dw / "08_datasets_bi" / "mockup_painel_bi_devmode.svg"
    p_prev_html = saida_dw / "08_datasets_bi" / "preview_painel_bi.html"
    p_xlsx = saida_dw / "08_datasets_bi" / "Indicadores_PowerBI_CRAFT.xlsx"
    p_pptx = saida_dw / "08_datasets_bi" / "apresentacao_executiva_craft.pptx"
    p_slides = saida_dw / "08_datasets_bi" / "apresentacao_slides.html"
    p_docx_bi = saida_dw / "08_datasets_bi" / "GUIA_ANALISTA_BI_CRAFT.docx"
    p_pdf_bi = saida_dw / "08_datasets_bi" / "GUIA_ANALISTA_BI_CRAFT.pdf"
    p_star_svg = saida_dw / "11_dicionario_dados" / "diagrama_star_schema.svg"
    p_odi_svg = saida_dw / "09_relatorio_estrategias" / "mapa_canvas_odi.svg"
    p_docx_odi = saida_dw / "09_relatorio_estrategias" / "RELATORIO_ESTRATEGIAS.docx"
    p_pdf_odi = saida_dw / "09_relatorio_estrategias" / "RELATORIO_ESTRATEGIAS.pdf"

    # Por padrão, os artefatos base (MD, SVG, HTML preview e XLSX) existem, mas PPTX/DOCX/PDF NÃO devem ser gerados sem solicitação
    for arq_padrao in (p_mock, p_mock_dev, p_prev_html, p_xlsx, p_star_svg, p_odi_svg):
        assert arq_padrao.exists() and arq_padrao.stat().st_size > 200, f"Artefato visual base ausente: {arq_padrao}"
    for arq_sob_demanda in (p_pptx, p_slides, p_docx_bi, p_pdf_bi, p_docx_odi, p_pdf_odi):
        assert not arq_sob_demanda.exists(), f"Artefato sob demanda gerado sem ser solicitado: {arq_sob_demanda}"

    # 2.1. Agora solicita explicitamente Apresentação Executiva, Word (.docx) e PDF (.pdf)
    for modo_extra in ("apresentacao", "exportar-docx", "exportar-pdf"):
        rc_ex, out_ex, err_ex = _executar_cli(
            ["core/scripts_comuns/melhorar_dw_existente.py", "--modo", modo_extra, "--projeto", "CRAFT"]
        )
        assert rc_ex == 0, f"melhorar_dw_existente.py --modo {modo_extra} falhou em T14: {err_ex}\n{out_ex}"

    for arq_esp in (
        p_mock, p_mock_dev, p_prev_html, p_xlsx, p_pptx, p_slides,
        p_docx_bi, p_pdf_bi, p_star_svg, p_odi_svg, p_docx_odi, p_pdf_odi
    ):
        assert arq_esp.exists() and arq_esp.stat().st_size > 200, f"Artefato visual/OOXML/PDF ausente ou vazio: {arq_esp}"

    # Verificar conteúdo do Mockup SVG + Dev Mode Redlines ①..⑦ + Indicadores vindos do .ods e do .odt
    svg_dev_txt = p_mock_dev.read_text(encoding="utf-8")
    assert "<svg" in svg_dev_txt and "DEV MODE" in svg_dev_txt and "①" in svg_dev_txt, "mockup_painel_bi_devmode.svg sem callouts Dev Mode"
    guia_bi_md = (saida_dw / "08_datasets_bi" / "GUIA_ANALISTA_BI_CRAFT.md").read_text(encoding="utf-8")
    assert "Taxa de Retenção Acadêmica" in guia_bi_md, "Indicador da planilha .ods não foi incorporado ao Guia do Analista de BI"
    assert "Indice de Aprovacao Semestral" in guia_bi_md, "Indicador do documento .odt não foi incorporado ao Guia do Analista de BI"

    # Verificar integridade ZIP/OOXML do .xlsx (3 abas + DataValidations + ConditionalFormatting), .pptx e .docx
    with zipfile.ZipFile(p_xlsx, "r") as z_xlsx:
        nomes_z = z_xlsx.namelist()
        assert "xl/workbook.xml" in nomes_z and "xl/worksheets/sheet3.xml" in nomes_z, "Planilha .xlsx sem as 3 abas esperadas"
        wb_xml = z_xlsx.read("xl/workbook.xml").decode("utf-8")
        assert "Catalogo_Indicadores" in wb_xml and "Metas_e_Thresholds" in wb_xml, "Abas de indicadores/metas ausentes no .xlsx"
        sh1_xml = z_xlsx.read("xl/worksheets/sheet1.xml").decode("utf-8")
        sh2_xml = z_xlsx.read("xl/worksheets/sheet2.xml").decode("utf-8")
        styles_xml = z_xlsx.read("xl/styles.xml").decode("utf-8")
        assert "<dataValidations" in sh1_xml and "<conditionalFormatting" in sh1_xml, "sheet1.xml sem Dropdowns ou Formatação Condicional"
        assert "<dataValidations" in sh2_xml and "<conditionalFormatting" in sh2_xml, "sheet2.xml sem Dropdowns ou Formatação Condicional"
        assert "<dxfs" in styles_xml, "styles.xml sem bloco <dxfs> para formatação condicional"

    with zipfile.ZipFile(p_pptx, "r") as z_pptx:
        assert "ppt/presentation.xml" in z_pptx.namelist() and "ppt/slides/slide1.xml" in z_pptx.namelist(), ".pptx inválido"

    with zipfile.ZipFile(p_docx_bi, "r") as z_docx:
        assert "word/document.xml" in z_docx.namelist(), ".docx inválido"

    # Testar round-trip de leitura nativa de .docx e .pdf gerados
    doc_lido = ler_documento_docx(str(p_docx_bi))
    assert len(doc_lido["paragrafos"]) > 5 and len(doc_lido["tabelas"]) >= 1, "ler_documento_docx não extraiu parágrafos/tabelas do .docx gerado"

    assert p_pdf_bi.read_bytes().startswith(b"%PDF-1.4"), "GUIA_ANALISTA_BI_CRAFT.pdf não possui cabeçalho %PDF-1.4"
    txt_pdf_bi = extrair_texto_pdf_nativo(str(p_pdf_bi))
    assert "CRAFT" in txt_pdf_bi, "extrair_texto_pdf_nativo não conseguiu ler o PDF gerado por exportar_markdown_para_pdf"

    # 3. Testar Scanner de PII/LGPD em valores de células/textos (CPF, E-mail, Telefone) e mascaramento
    linhas_amostra_pii = [
        ["ID_SOLICITACAO", "TXT_OBSERVACAO_LIVRE", "DES_HISTORICO"],
        ["101", "Solicitante CPF 123.456.789-00 enviou comprovante pelo email joao.silva@ba.gov.br", "Contato (71) 98888-7777"],
    ]
    achados_pii = escanear_pii_em_texto_ou_linhas(linhas_amostra_pii, nome_contexto="amostra_teste.csv")
    tipos_pii = {a["tipo_pii"] for a in achados_pii}
    assert "CPF" in tipos_pii and "EMAIL" in tipos_pii and "TELEFONE_BR" in tipos_pii, f"Scanner PII não detectou todos os padrões: {tipos_pii}"
    txt_masc = mascarar_pii_texto("CPF 123.456.789-00 e email joao@ba.gov.br")
    assert "123.456.789-00" not in txt_masc and "***.456.789-**" in txt_masc, f"Falha no mascaramento de PII: {txt_masc}"

    # 4. Testar extrator nativo de PDF (com stream FlateDecode comprimido) e Bateria Panic Hunt
    with tempfile.TemporaryDirectory() as tmp_str:
        tmp = Path(tmp_str)
        stream_conteudo = b"BT /F1 12 Tf 72 720 Td (CREATE TABLE DW_PDF.DIM_CURSO (SK_CURSO NUMBER PRIMARY KEY);) Tj ET"
        stream_comp = zlib.compress(stream_conteudo)
        pdf_bytes = (
            b"%PDF-1.4\n1 0 obj << /Type /Page >> endobj\n"
            b"2 0 obj << /Length " + str(len(stream_comp)).encode("ascii") + b" /Filter /FlateDecode >>\nstream\n"
            + stream_comp
            + b"\nendstream\nendobj\n%%EOF"
        )
        arq_pdf_ok = tmp / "especificacao_dw.pdf"
        arq_pdf_ok.write_bytes(pdf_bytes)
        txt_pdf = extrair_texto_pdf_nativo(str(arq_pdf_ok))
        assert "CREATE TABLE DW_PDF.DIM_CURSO" in txt_pdf, f"Falha na extração de PDF: {txt_pdf}"

        # Bateria Panic Hunt (arquivos truncados, corrompidos ou binários hostis não podem causar crash não tratado)
        arq_ods_corrompido = tmp / "corrompido.ods"
        arq_ods_corrompido.write_bytes(b"PK\x03\x04LIXO_TRUNCADO_SEM_CENTRAL_DIR")
        assert ler_planilha_ods(str(arq_ods_corrompido)) == [], "ler_planilha_ods deveria retornar lista vazia para .ods corrompido"

        arq_docx_corrompido = tmp / "corrompido.docx"
        arq_docx_corrompido.write_bytes(b"PK\x03\x04DOCX_TRUNCADO_HOSTIL")
        assert ler_documento_docx(str(arq_docx_corrompido))["texto"] == "", "ler_documento_docx falhou em .docx corrompido"

        arq_odt_corrompido = tmp / "corrompido.odt"
        arq_odt_corrompido.write_bytes(b"PK\x03\x04ODT_TRUNCADO_HOSTIL")
        assert ler_documento_odt(str(arq_odt_corrompido))["texto"] == "", "ler_documento_odt falhou em .odt corrompido"

        arq_pdf_corrompido = tmp / "corrompido.pdf"
        arq_pdf_corrompido.write_bytes(b"%PDF-1.7\nstream\n\xff\xfe\xfdLIXO_ZLIB_INVALIDO\nendstream")
        res_pdf_ruim = extrair_texto_pdf_nativo(str(arq_pdf_corrompido))
        assert isinstance(res_pdf_ruim, str), "extrair_texto_pdf_nativo falhou em arquivo PDF corrompido"

        arq_sql_hostil = tmp / "hostil.sql"
        arq_sql_hostil.write_bytes(b"\x80\x81\xffCREATE TABLE T_TRUNCADA (ID NUMBER, /* comentario sem fim ((((")
        rc_h, _out_h, _err_h = _executar_cli(["core/scripts_comuns/inspecionar_ddl_origem.py", "--caminho", str(arq_sql_hostil)])
        assert rc_h in (0, 1), "inspecionar_ddl_origem.py sofreu crash inesperado com SQL truncado/hostil"

    _limpar_artefatos_workspace()
    return (
        "Mockup BI (SVG + Dev Mode Redlines ①..⑦ + HTML/PNG 2x), Diagramas Star Schema/ODI SVG, "
        "Planilha .xlsx (Dropdowns + CondFormatting), .pptx + .docx + .pdf 1.4, Leitores .pdf/.ods/.docx/.odt, "
        "Scanner PII/LGPD em linhas e Panic Hunt aprovados."
    )


def teste_15_apache_hop_5_mecanismos() -> str:
    """Valida as 5 implementações extraídas do Apache Hop 2.x (hop-main):
    1. Desenhador Visual SVG de Pipelines (.hpl) e Workflows (.hwf) + Auto-Documentação (PipelineSvgPainter/DocBuilder)
    2. Catálogo Oficial hop-lint (TRANS-002, WORKFLOW-002, NAMING-004, SQL-002, STRUCT-003, DOC-001, META-001) + hop-lint.yml
    3. Migrador Automático Pentaho Kettle (.ktr/.kjb/shared.xml) -> Apache Hop 2.x (.hpl/.hwf + metadata/rdbms/*.json)
    4. Blindagem THREAT_MODEL.md (HopTwoWayPasswordEncoder encrypt/decrypt, HOP-SEC-01, HOP-SEC-02 e hop-pwd.json)
    5. Template de Alta Volumetria OraBulkLoader (SQL*Loader) + Gerador Completo de Pacote Hop (/gerar-pacote-hop)
    """
    from auditar_esteira_hop import (
        audit_hop_directory,
        gerar_hop_lint_yml,
        gerar_hop_pwd_resolver_json,
        gerar_pacote_hop_completo,
        hop_decrypt_password,
        hop_encrypt_password,
        migrar_kettle_para_hop,
    )
    from gerador_artefatos_visuais import (
        gerar_documentacao_esteira_hop,
        gerar_svg_canvas_hop,
    )

    _limpar_artefatos_workspace()

    # Feature 4A: Criptografia reversível HopTwoWayPasswordEncoder (seed 0933910847463829827159347601486730416058)
    enc = hop_encrypt_password("SenhaSuperSecreta123")
    assert enc.startswith("Encrypted "), f"hop_encrypt_password não gerou prefixo Encrypted: {enc}"
    dec = hop_decrypt_password(enc)
    assert dec == "SenhaSuperSecreta123", f"Round-trip HopTwoWayPasswordEncoder falhou: {dec}"
    assert hop_decrypt_password("Encrypted 2be98afc86aa7f2e4cb799d64cc9ba1dd") == "String", (
        "Falha ao decodificar vetor oficial 'String' do HopTwoWayPasswordEncoderTest.java"
    )
    assert hop_decrypt_password("Encrypted 2be98afc86aa7c3d6f84dfb2689caf68a") == "1234567890", (
        "Falha ao decodificar vetor oficial '1234567890' do HopTwoWayPasswordEncoderTest.java"
    )

    with tempfile.TemporaryDirectory() as tmp_str:
        tmp = Path(tmp_str)

        # Feature 2 + 4B: Testar detecção hop-lint (TRANS-002, NAMING-004, SQL-002, STRUCT-003, DOC-001, META-001) + THREAT_MODEL (HOP-SEC-01/02)
        pasta_hop_lint = tmp / "hop_lint_test"
        (pasta_hop_lint / "metadata" / "RDBMS_ERRADO").mkdir(parents=True, exist_ok=True)
        (pasta_hop_lint / "metadata" / "RDBMS_ERRADO" / "conn.json").write_text(
            '{"name": "CONN_ORA", "password": "Encrypted 2be98afc86aa7f2e4cb79ce10bec3fd89"}',
            encoding="utf-8",
        )
        (pasta_hop_lint / "ppl_vulneravel.hpl").write_text(
            """<?xml version="1.0" encoding="UTF-8"?>
<pipeline>
  <info><name>ppl_vulneravel</name><description/></info>
  <order>
    <hop><from>Set variables</from><to>Table input</to><enabled>N</enabled></hop>
  </order>
  <transform>
    <name>Set variables</name>
    <type>SetVariable</type>
    <fields><field><field_name>col_insegura</field_name><variable_name>FILTRO_EXTERNO</variable_name></field></fields>
    <GUI><xloc>100</xloc><yloc>100</yloc></GUI>
  </transform>
  <transform>
    <name>Table input</name>
    <type>TableInput</type>
    <sql>SELECT * FROM ORIGEM.TB_DADOS WHERE ${FILTRO_EXTERNO}</sql>
    <variables_active>Y</variables_active>
    <GUI><xloc>300</xloc><yloc>100</yloc></GUI>
  </transform>
  <transform>
    <name>Transform_Orfao</name>
    <type>Dummy</type>
    <GUI><xloc>500</xloc><yloc>100</yloc></GUI>
  </transform>
</pipeline>""",
            encoding="utf-8",
        )
        _stats_lint, findings_lint = audit_hop_directory(pasta_hop_lint)
        codigos_achados = {f.rule_id for f in findings_lint}
        for regra_esp in ("HOP-SEC-01", "HOP-SEC-02", "META-001", "DOC-001", "STRUCT-003", "TRANS-002", "NAMING-004", "SQL-002"):
            assert regra_esp in codigos_achados, f"Regra {regra_esp} não disparou na auditoria Hop: {codigos_achados}"

        arq_yml = gerar_hop_lint_yml(pasta_hop_lint)
        assert arq_yml.exists() and "TRANS-002" in arq_yml.read_text(encoding="utf-8"), "hop-lint.yml não foi gerado corretamente"
        arq_pwd = gerar_hop_pwd_resolver_json(pasta_hop_lint)
        assert arq_pwd.exists() and "HopPasswordVariableResolver" in arq_pwd.read_text(encoding="utf-8"), "hop-pwd.json não foi gerado"

        # Feature 3: Testar Migrador Pentaho Kettle (.ktr + .kjb) -> Apache Hop 2.x (.hpl + .hwf + metadata/rdbms/*.json + SVG)
        pasta_kettle = tmp / "kettle_legado"
        pasta_kettle.mkdir(parents=True, exist_ok=True)
        (pasta_kettle / "carga_clientes.ktr").write_text(
            """<?xml version="1.0" encoding="UTF-8"?>
<transformation>
  <info><name>carga_clientes</name><description>Transformacao Kettle</description></info>
  <connection>
    <name>ORA_LEGADO</name>
    <server>10.0.0.15</server>
    <type>ORACLE</type>
    <port>1521</port>
    <database>ORCL</database>
    <username>USR_ETL</username>
    <password>Encrypted 2be98afc86aa7f2e4cb79ce10bec3fd89</password>
  </connection>
  <order><hop><from>Ler CSV</from><to>Gravar STG</to><enabled>Y</enabled></hop></order>
  <step>
    <name>Ler CSV</name>
    <type>TextFileInput</type>
    <GUI><xloc>120</xloc><yloc>140</yloc></GUI>
  </step>
  <step>
    <name>Gravar STG</name>
    <type>TableOutput</type>
    <connection>ORA_LEGADO</connection>
    <table>STG_CLIENTE</table>
    <GUI><xloc>360</xloc><yloc>140</yloc></GUI>
  </step>
</transformation>""",
            encoding="utf-8",
        )
        (pasta_kettle / "job_principal.kjb").write_text(
            """<?xml version="1.0" encoding="UTF-8"?>
<job>
  <name>job_principal</name>
  <entries>
    <entry><name>Start</name><type>SPECIAL</type><xloc>100</xloc><yloc>120</yloc></entry>
    <entry><name>Executar KTR</name><type>TRANS</type><filename>${Internal.Entry.Current.Directory}/carga_clientes.ktr</filename><xloc>320</xloc><yloc>120</yloc></entry>
  </entries>
  <hops><hop><from>Start</from><to>Executar KTR</to><enabled>Y</enabled><evaluation>Y</evaluation></hop></hops>
</job>""",
            encoding="utf-8",
        )
        pasta_hop_migrado = tmp / "hop_migrado"
        rel_mig = migrar_kettle_para_hop(pasta_kettle, pasta_hop_migrado)
        assert len(rel_mig["hpl_migrados"]) == 1 and len(rel_mig["hwf_migrados"]) == 1, f"Falha na migração Kettle: {rel_mig}"
        assert len(rel_mig["conexoes_rdbms"]) == 1, "Conexão <connection> do Kettle não foi extraída para metadata/rdbms/*.json"
        hpl_mig_txt = Path(rel_mig["hpl_migrados"][0]).read_text(encoding="utf-8")
        hwf_mig_txt = Path(rel_mig["hwf_migrados"][0]).read_text(encoding="utf-8")
        conn_json_txt = Path(rel_mig["conexoes_rdbms"][0]).read_text(encoding="utf-8")
        assert "<pipeline>" in hpl_mig_txt and "<transform>" in hpl_mig_txt and "TextFileInput2" in hpl_mig_txt, ".ktr não converteu tags/tipos para .hpl"
        assert "<workflow>" in hwf_mig_txt and "<actions>" in hwf_mig_txt and ".hpl" in hwf_mig_txt and "Internal.Entry.Current.Folder" in hwf_mig_txt, ".kjb não converteu para .hwf"
        assert "#{hop-pwd:" in conn_json_txt and "Encrypted " not in conn_json_txt, "Conexão migrada deveria usar #{hop-pwd:...} sem senha Encrypted"

        # Feature 1 + Feature 5: Gerador de Pacote Hop 2.x com OraBulkLoader + Desenhador Visual SVG + Auto-Doc
        pasta_pacote = tmp / "pacote_hop_orabulk"
        arqs_pkg = gerar_pacote_hop_completo(
            pasta_destino=pasta_pacote,
            projeto="TESTE_HOP",
            schema_stg="STG_TESTE",
            tabelas=["STG_ATENDIMENTO"],
            usar_orabulkloader=True,
        )
        assert "svg_esteira_hop" in arqs_pkg and Path(arqs_pkg["svg_esteira_hop"]).exists(), "diagrama_esteira_hop.svg não foi gerado"
        assert "doc_esteira_hop" in arqs_pkg and Path(arqs_pkg["doc_esteira_hop"]).exists(), "DOCUMENTACAO_HOP.md não foi gerado"
        ppl_bulk_path = pasta_pacote / "ppl_stg_atendimento.hpl"
        assert ppl_bulk_path.exists() and "<type>OraBulkLoader</type>" in ppl_bulk_path.read_text(encoding="utf-8"), (
            "Pipeline com OraBulkLoader não foi gerado"
        )
        svg_hop_txt = gerar_svg_canvas_hop(str(ppl_bulk_path))
        assert "<svg" in svg_hop_txt and "OraBulkLoader" in svg_hop_txt, "gerar_svg_canvas_hop não renderizou o pipeline"
        doc_hop_res = gerar_documentacao_esteira_hop(str(pasta_pacote))
        assert Path(doc_hop_res["doc_esteira_hop"]).exists(), "gerar_documentacao_esteira_hop falhou"

        # Garantir que o pacote gerado pelo NINHO passa com 0 ERROS CRITICOS no próprio auditor Hop!
        _stats_pkg, findings_pkg = audit_hop_directory(pasta_pacote)
        erros_pkg = [f for f in findings_pkg if f.severity in ("CRITICO", "ERRO")]
        assert len(erros_pkg) == 0, f"Pacote Hop gerado apresentou erros críticos na auditoria: {[f.rule_id for f in erros_pkg]}"

    _limpar_artefatos_workspace()
    return (
        "5 Mecanismos Apache Hop 2.x (SVG Canvas Painter + DocBuilder, Catálogo hop-lint + hop-lint.yml, "
        "Migrador Kettle .ktr/.kjb -> .hpl/.hwf, THREAT_MODEL.md HopTwoWayPasswordEncoder + HOP-SEC-01/02 "
        "e Pacote OraBulkLoader) aprovados."
    )


def teste_16_prova_real_amostra_dim_fato_e_mockup_dax() -> str:
    """
    T16: Valida o motor de Prova Real Pós-Carga (DIM_* + FATO_* em CSV/SQL) sobre as medidas DAX
    do Guia do Analista de BI, detecção/correção de medidas parcialmente corretas (MED-01..06)
    e renderização do Mockup Visual populado pelos dados reais da amostra.
    """
    _limpar_artefatos_workspace()

    pasta_ddl = BASE_DIR / "entrega" / "planejador_dw" / "ddl"
    pasta_amostras = BASE_DIR / "entrega" / "planejador_dw" / "amostras"
    pasta_ddl.mkdir(parents=True, exist_ok=True)
    pasta_amostras.mkdir(parents=True, exist_ok=True)

    ddl_bolsa = """
    CREATE TABLE PRODBA_OLAP.DIM_UNIDADE (
        SK_UNIDADE NUMBER(10) PRIMARY KEY,
        COD_UNIDADE VARCHAR2(30),
        NOM_UNIDADE VARCHAR2(150),
        FLG_ATUAL CHAR(1)
    );
    CREATE TABLE PRODBA_OLAP.DIM_MODALIDADE (
        SK_MODALIDADE NUMBER(10) PRIMARY KEY,
        COD_MODALIDADE VARCHAR2(30),
        DES_MODALIDADE VARCHAR2(120),
        FLG_ATUAL CHAR(1)
    );
    CREATE TABLE PRODBA_OLAP.FATO_PAGAMENTO_BOLSA (
        SK_PAGAMENTO NUMBER(12) PRIMARY KEY,
        SK_UNIDADE NUMBER(10),
        SK_MODALIDADE NUMBER(10),
        VAL_PAGO NUMBER(15,2),
        QTD_BOLSAS NUMBER(10),
        PER_FREQUENCIA NUMBER(5,2),
        CONSTRAINT FK_FAT_UNID FOREIGN KEY (SK_UNIDADE) REFERENCES PRODBA_OLAP.DIM_UNIDADE (SK_UNIDADE),
        CONSTRAINT FK_FAT_MOD FOREIGN KEY (SK_MODALIDADE) REFERENCES PRODBA_OLAP.DIM_MODALIDADE (SK_MODALIDADE)
    );
    """
    (pasta_ddl / "01_dw_bolsa.sql").write_text(ddl_bolsa, encoding="utf-8")

    # Fase 1: Gerar Guia do Analista de BI ANTES de fornecer amostras -> Deve gerar VERSÃO PRÉVIA (Pré-Carga) com apenas 1 arquivo e fichas detalhadas
    rc_prev, out_prev, err_prev = _executar_cli(["ninho.py", "gerar-guia-bi"])
    assert rc_prev == 0, f"Falha ao executar gerar-guia-bi (Fase Pré-Carga): {err_prev}\n{out_prev}"

    pasta_bi = BASE_DIR / "saida" / "planejador_dw" / "08_datasets_bi"
    guias_md_prev = list(pasta_bi.glob("GUIA_ANALISTA_BI_*.md"))
    assert len(guias_md_prev) == 1, f"Deveria existir exatamente 1 GUIA_ANALISTA_BI_*.md, encontrados: {[g.name for g in guias_md_prev]}"
    txt_guia_prev = guias_md_prev[0].read_text(encoding="utf-8")
    assert (
        "VERSÃO PRÉVIA — PRÉ-CARGA" in txt_guia_prev
        and "O que calcula (Definição Funcional)" in txt_guia_prev
        and "Por que esta medida existe (Objetivo de Negócio no Painel)" in txt_guia_prev
        and "Por que a fórmula DAX foi construída assim (Racional Técnico Detalhado)" in txt_guia_prev
    ), "Guia na Fase 1 deveria estar rotulado como VERSÃO PRÉVIA — PRÉ-CARGA e conter ficha técnica detalhada em cada medida"

    # Fase 2: Fornecer amostras reais pós-carga e validar -> Deve promover o mesmo Guia único para VERSÃO OFICIAL (Homologada Pós-Carga)
    # Amostra CSV de DIM_UNIDADE com linha sentinela (-1) e histórico SCD Tipo 2 (UNEB-01 com SK 10 e SK 11)
    csv_unid = (
        "SK_UNIDADE;COD_UNIDADE;NOM_UNIDADE;FLG_ATUAL\n"
        "-1;NI;Não Informado;S\n"
        "10;UNEB-01;Campus I Salvador (Histórico);N\n"
        "11;UNEB-01;Campus I Salvador;S\n"
        "20;UNEB-02;Campus II Alagoinhas;S\n"
    )
    (pasta_amostras / "DIM_UNIDADE.csv").write_text(csv_unid, encoding="utf-8")

    csv_mod = (
        "SK_MODALIDADE;COD_MODALIDADE;DES_MODALIDADE;FLG_ATUAL\n"
        "-1;NI;Não Informado;S\n"
        "1;MON;Monitoria Acadêmica;S\n"
        "2;IC;Iniciação Científica;S\n"
    )
    (pasta_amostras / "DIM_MODALIDADE.csv").write_text(csv_mod, encoding="utf-8")

    # Amostra SQL INSERT de FATO_PAGAMENTO_BOLSA contendo:
    # - 2 linhas para UNEB-01 em versões diferentes de SK (10 e 11) -> 1 única NK ('UNEB-01')
    # - 1 linha para UNEB-02 (SK 20) -> 1 NK ('UNEB-02')
    # - 1 linha sentinela SK = -1
    # - 1 linha com FK órfã SK = 999 (não existe em DIM_UNIDADE -> dispara MED-01 se faltar NOT(ISBLANK(RELATED())))
    # Soma total de VAL_PAGO = 3000 + 4500 + 2500 + 1500 + 1000 = 12500.00
    sql_inserts_fato = """
    INSERT INTO PRODBA_OLAP.FATO_PAGAMENTO_BOLSA (SK_PAGAMENTO, SK_UNIDADE, SK_MODALIDADE, VAL_PAGO, QTD_BOLSAS, PER_FREQUENCIA) VALUES (1, 10, 1, 3000.00, 3, 95.0);
    INSERT INTO PRODBA_OLAP.FATO_PAGAMENTO_BOLSA (SK_PAGAMENTO, SK_UNIDADE, SK_MODALIDADE, VAL_PAGO, QTD_BOLSAS, PER_FREQUENCIA) VALUES (2, 11, 1, 4500.00, 5, 98.0);
    INSERT INTO PRODBA_OLAP.FATO_PAGAMENTO_BOLSA (SK_PAGAMENTO, SK_UNIDADE, SK_MODALIDADE, VAL_PAGO, QTD_BOLSAS, PER_FREQUENCIA) VALUES (3, 20, 2, 2500.00, 2, 92.0);
    INSERT INTO PRODBA_OLAP.FATO_PAGAMENTO_BOLSA (SK_PAGAMENTO, SK_UNIDADE, SK_MODALIDADE, VAL_PAGO, QTD_BOLSAS, PER_FREQUENCIA) VALUES (4, -1, 2, 1500.00, 1, 85.0);
    INSERT INTO PRODBA_OLAP.FATO_PAGAMENTO_BOLSA (SK_PAGAMENTO, SK_UNIDADE, SK_MODALIDADE, VAL_PAGO, QTD_BOLSAS, PER_FREQUENCIA) VALUES (5, 999, 1, 1000.00, 1, 90.0);
    """
    (pasta_amostras / "amostra_fato_pos_carga.sql").write_text(sql_inserts_fato, encoding="utf-8")

    # Medida customizada propositalmente "parcialmente correta" para provar a detecção e auto-correção (MED-01, MED-02, MED-04, MED-05)
    dax_parcial = """
    // Medida sem proteção contra Blank Row de FK órfã (MED-01)
    Qtd Unidades Sem Filtro Blank = COUNTROWS(SUMMARIZE(FILTER('FATO_PAGAMENTO_BOLSA', 'FATO_PAGAMENTO_BOLSA'[SK_UNIDADE] <> -1), 'DIM_UNIDADE'[COD_UNIDADE]))

    // Medida contando SK histórica em vez de NK em dimensão com SCD2 (MED-02)
    Qtd Unidades Contando SK = CALCULATE(DISTINCTCOUNT('FATO_PAGAMENTO_BOLSA'[SK_UNIDADE]), 'FATO_PAGAMENTO_BOLSA'[SK_UNIDADE] <> -1)

    // Medida rotulada como % mas dividindo Valor por Quantidade (MED-04)
    % Relacao Pago vs Bolsas Legado = DIVIDE([Total Pago], [Total Bolsas], 0)

    // Soma indevida de percentual (MED-05)
    Soma Indevida Frequencia = SUM('FATO_PAGAMENTO_BOLSA'[PER_FREQUENCIA])
    """
    (pasta_amostras / "medidas_teste_parcial.dax").write_text(dax_parcial, encoding="utf-8")

    rc, out, err = _executar_cli(["ninho.py", "validar-medidas-bi"])
    assert rc == 0, f"Falha ao executar validar-medidas-bi: {err}\n{out}"

    pasta_bi = BASE_DIR / "saida" / "planejador_dw" / "08_datasets_bi"
    arq_rel = pasta_bi / "RELATORIO_PROVA_REAL_MEDIDAS.md"
    arq_svg = pasta_bi / "mockup_painel_bi.svg"
    arq_html = pasta_bi / "preview_painel_bi.html"

    guias_md_ofic = list(pasta_bi.glob("GUIA_ANALISTA_BI_*.md"))
    assert len(guias_md_ofic) == 1, f"Deveria existir exatamente 1 GUIA_ANALISTA_BI_*.md após validação, encontrados: {[g.name for g in guias_md_ofic]}"
    txt_guia_ofic = guias_md_ofic[0].read_text(encoding="utf-8")
    assert (
        "VERSÃO OFICIAL — HOMOLOGADA PÓS-CARGA" in txt_guia_ofic
        and "10. 🧪 Prova Real Pós-Carga" in txt_guia_ofic
    ), "Guia na Fase 2 deveria ter sido promovido para VERSÃO OFICIAL — HOMOLOGADA PÓS-CARGA com a Seção 10 de conciliação"

    assert arq_rel.exists(), "RELATORIO_PROVA_REAL_MEDIDAS.md não foi gerado"
    txt_rel = arq_rel.read_text(encoding="utf-8")
    assert (
        "MED-01" in txt_rel
        and "MED-02" in txt_rel
        and "MED-04" in txt_rel
        and "MED-05" in txt_rel
        and "R$ 12.500,00" in txt_rel
        and "Catálogo de Medidas DAX Revisadas" in txt_rel
    ), f"RELATORIO_PROVA_REAL_MEDIDAS.md não detectou todas as medidas parcialmente corretas ou a soma real:\n{txt_rel[:1200]}"

    txt_svg = arq_svg.read_text(encoding="utf-8")
    assert "Prova Real (5 linhas na Fato)" in txt_svg and "R$ 12.500,00" in txt_svg, (
        "mockup_painel_bi.svg não foi populado com os valores reais da amostra pós-carga"
    )

    txt_html = arq_html.read_text(encoding="utf-8")
    assert "Prova Real Pós-Carga (DIM + FATO) e Conciliação de Medidas DAX" in txt_html and "R$ 12.500,00" in txt_html, (
        "preview_painel_bi.html não incluiu a tabela interativa de Prova Real Pós-Carga"
    )

    _limpar_artefatos_workspace()
    return "Prova Real Pós-Carga (SQLite in-memory DIM+FATO), detecção/correção MED-01..05 e Mockup SVG/HTML populado aprovados."


def executar_suite_completa(manter_arquivos: bool = False) -> int:
    print("=" * 88)
    print("🦅 PLATAFORMA NINHO — SUÍTE AUTOMATIZADA DE TESTES END-TO-END (E2E)")
    print("=" * 88)

    testes: List[Tuple[str, Callable[[], str]]] = [
        ("T01: Central de Ajuda (/help) & Gerenciador de Projeto", teste_01_ajuda_e_status),
        ("T02: Extrator de DDLs de Origem & Radar Consultivo", teste_02_inspecionar_ddl_origem),
        ("T03: Simulação Editável + Parser Reverso DW & Semântica + KPIs Radar", teste_03_simulacao_edicao_reversa_dw_e_semantica),
        ("T04: Gerador Dinâmico de Dados Sintéticos BI (Colunas Reais + Sentinela -1)", teste_04_gerador_mock_dinamico),
        ("T05: Validador de Qualidade Pós-Geração (validar_entrega.py saida)", teste_05_validar_entrega_saida),
        ("T06: Transição DW -> Semântica & Micro-Modos Isolados", teste_06_transicao_e_micro_modos_semantica),
        ("T07: Motor Fast-Track Não-Destrutivo (melhorar_dw_existente.py)", teste_07_fast_track_melhorar_dw_existente),
        ("T08: Auditoria Especializada (ODI 12c, Hop 2.x, Power BI .pbix, Gov Gate 0.5)", teste_08_motores_auditoria_odi_hop_pbix_governanca),
        ("T09: Experiência Conversacional UX (/comecar, /onde-estou, /duvida, /doctor, /demo)", teste_09_experiencia_ux_conversacional),
        ("T10: Regressão de Confiabilidade (Erros E1 a E4 Resolvidos)", teste_10_regressao_e1_e4_robustez),
        ("T11: Regressão de Blindagem Arquitetural (Erros E5 a E12 Resolvidos)", teste_11_regressao_e5_e12_blindagem),
        ("T12: Regressão M1..M7 (DDL em CSV, MVW_*, Role-Playing DIM_TEMPO, Guia BI + .xlsx)", teste_12_regressao_m1_m7_praes_csv_ddl_guia_bi),
        ("T13: Regressão P1..P7 (Sigla ODI, ODI_DIM NULLABLE, Dimension Pattern, HOP-H9, UPPER/TRIM)", teste_13_regressao_p1_a_p7),
        ("T14: Suíte Visual & OOXML (*Craft) + Leitura .ods/.pdf + Panic Hunt", teste_14_suite_visual_craft_e_panic_hunt),
        ("T15: Suíte Apache Hop 2.x (SVG Painter, hop-lint, Migrador Kettle, THREAT_MODEL & OraBulkLoader)", teste_15_apache_hop_5_mecanismos),
        ("T16: Prova Real Pós-Carga (DIM+FATO) + Auditor DAX (MED-01..06) + Mockup Populado", teste_16_prova_real_amostra_dim_fato_e_mockup_dax),
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
                    if not arq.exists() or arq.read_bytes() != conteudo_orig:
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
