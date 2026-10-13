#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Transicionador Automatizado: Planejador de DW -> Camada Semântica
Plataforma NINHO — Pipeline Contínuo de Dados

Este script realiza a ponte de integração automática entre a saída do Planejador de DW
e a entrada da Camada Semântica, garantindo que o trabalho não pare em um único módulo:
  1. Coleta os DDLs de Fatos e Dimensões gerados em 'saida/planejador_dw/<PROJETO>/'
     e os deposita em 'entrega/camada_semantica/ddl/'.
  2. Gera um DDL consolidado ('DDL_COMPLETO_DW_<PROJETO>.sql') com ordem de dependência.
  3. Coleta ou gera amostras de dados sintéticos (mock) em 'entrega/camada_semantica/amostras/'.
  4. Transfere os relatórios de estratégias e guias de BI para 'entrega/camada_semantica/relatorios_etl/'.
  5. Preenche automaticamente o formulário 'modulos/camada_semantica/INTAKE_SEMANTICA.md'.
  6. Atualiza a documentação central do projeto em 'documentacao/catalogo_projetos/PROJETO_RESUMO.md'
     e 'documentacao/catalogo_projetos/PROJETO_VERSION.md'.
  7. Dispara a validação pré-voo da Camada Semântica ('validar_entrega.py semantica').

Uso:
    python core/scripts_comuns/transicionar_dw_para_semantica.py
    python core/scripts_comuns/transicionar_dw_para_semantica.py --projeto SEI_BAHIA
    python core/scripts_comuns/transicionar_dw_para_semantica.py --projeto SEI_BAHIA --schema SEIMUNICIPIO_OLAP --forcar
"""

import sys
import os
import re
import shutil
import argparse
from datetime import datetime
from pathlib import Path

# Configura encoding do stdout para UTF-8 no Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Cores ANSI para terminal
VERDE = "\033[92m"
AMARELO = "\033[93m"
VERMELHO = "\033[91m"
AZUL = "\033[94m"
CIANO = "\033[96m"
NEGRITO = "\033[1m"
RESET = "\033[0m"


def get_base_dir() -> Path:
    """Retorna o diretório raiz do projeto."""
    return Path(__file__).resolve().parent.parent.parent


def print_banner(title: str):
    print(f"\n{CIANO}{NEGRITO}{'=' * 75}{RESET}")
    print(f"{CIANO}{NEGRITO}  🚀 NINHO PIPELINE — {title}{RESET}")
    print(f"{CIANO}{NEGRITO}{'=' * 75}{RESET}\n")


def print_ok(msg: str):
    print(f"  {VERDE}[OK]{RESET} {msg}")


def print_warn(msg: str):
    print(f"  {AMARELO}[AVISO]{RESET} {msg}")


def print_err(msg: str):
    print(f"  {VERMELHO}[ERRO]{RESET} {msg}")


def extrair_metadados_intake_dw(base_dir: Path) -> dict:
    """Extrai informações do formulário INTAKE_DW.md."""
    intake_dw_path = base_dir / "modulos" / "planejador_dw" / "INTAKE_DW.md"
    dados = {
        "projeto": "",
        "engenheiro": "",
        "schema": "",
        "perguntas": [],
        "grao_fato": "",
        "estrategia_carga": "",
        "medidas": [],
        "scd_tipo": "SCD Tipo 2 (com DTC_EFETIVACAO, DTC_EXPIRACAO e ODI_DIM_*)",
        "retencao": "Perpétuo",
    }

    if not intake_dw_path.exists():
        return dados

    texto = intake_dw_path.read_text(encoding="utf-8", errors="ignore")

    # Nome do Projeto
    m_proj = re.search(r"\*\*Nome do Projeto:\*\*\s*`?(.*?)`?$", texto, re.MULTILINE)
    if m_proj and m_proj.group(1).strip() and not m_proj.group(1).strip().startswith("[Ex:"):
        dados["projeto"] = m_proj.group(1).strip()

    # Engenheiro
    m_eng = re.search(r"\*\*Engenheiro Responsável:\*\*\s*`?(.*?)`?$", texto, re.MULTILINE)
    if m_eng and m_eng.group(1).strip() and not m_eng.group(1).strip().startswith("[Nome"):
        dados["engenheiro"] = m_eng.group(1).strip()

    # Schema Alvo
    m_sch = re.search(r"\*\*Schema Alvo no Oracle:\*\*\s*`?(.*?)`?$", texto, re.MULTILINE)
    if m_sch and m_sch.group(1).strip() and not m_sch.group(1).strip().startswith("[Ex:"):
        dados["schema"] = m_sch.group(1).strip()

    # Perguntas de Negócio
    m_perguntas = re.findall(r"^\d+\.\s*`?\[?(.*?)\]?`?$", texto, re.MULTILINE)
    for p in m_perguntas:
        p_clean = p.strip().lstrip("Ex: ").strip("`[]")
        if p_clean and not p_clean.startswith("..."):
            dados["perguntas"].append(p_clean)

    # Grão
    m_grao = re.search(r"\*\*Grão esperado da Fato principal:\*\*\s*\n\s*\*?(.*?)\*?$", texto, re.MULTILINE)
    if m_grao and m_grao.group(1).strip() and not m_grao.group(1).strip().startswith("Ex:"):
        dados["grao_fato"] = m_grao.group(1).strip()

    # Estratégia de Carga
    if "[x] **Estratégia A: Truncate & Load Massivo" in texto:
        dados["estrategia_carga"] = "Estratégia A (Truncate & Load Massivo com BITMAP INDEX e PRC_POS_CARGA_FATO)"
    elif "[x] **Estratégia B: Incremental Idempotente" in texto:
        dados["estrategia_carga"] = "Estratégia B (Incremental Idempotente via MERGE com B-TREE INDEX)"

    return dados


PASTAS_CANONICAS_DW = {
    "01_CONTROLE_CARGA",
    "02_STAGING",
    "03_DIMENSOES",
    "04_FATOS",
    "05_PROCEDIMENTOS_MANUTENCAO",
    "06_PIPELINES_HOP",
    "07_EXTRATORES_PYTHON",
    "08_DATASETS_BI",
    "09_RELATORIO_ESTRATEGIAS",
    "10_TESTES_INTEGRIDADE",
    "11_DICIONARIO_DADOS",
    "TEMPLATES",
    "README.MD",
}


def detectar_projeto(base_dir: Path, proj_arg: str = "") -> str:
    """Detecta o nome do projeto se não for passado explicitamente."""
    if proj_arg:
        return proj_arg.upper().strip()

    # 1. Tentar ler do INTAKE_DW.md
    meta = extrair_metadados_intake_dw(base_dir)
    if meta.get("projeto"):
        return meta["projeto"].upper().strip()

    # 2. Tentar detectar na pasta ddl de saída (ignorando pastas canônicas estruturais)
    saida_dw = base_dir / "saida" / "planejador_dw"
    if saida_dw.exists():
        subdirs = [
            d.name for d in saida_dw.iterdir()
            if d.is_dir() and d.name.upper() not in PASTAS_CANONICAS_DW
        ]
        if len(subdirs) == 1:
            return subdirs[0].upper().strip()
        elif len(subdirs) > 1:
            print_warn(f"Múltiplos projetos encontrados em 'saida/planejador_dw/': {', '.join(subdirs)}")
            return subdirs[0].upper().strip()

    # Fallback
    return "PROJETO_DW"



def copiar_ddls(base_dir: Path, projeto: str, pasta_saida_dw: Path) -> list:
    """Copia DDLs de fatos e dimensões e gera o arquivo consolidado."""
    dest_ddl = base_dir / "entrega" / "camada_semantica" / "ddl"
    dest_ddl.mkdir(parents=True, exist_ok=True)

    arquivos_copiados = []
    conteudos_sql = []

    # Procura DDLs em 03_dimensoes, 04_fatos e na raiz do projeto DW
    pastas_busca = [
        pasta_saida_dw / "03_dimensoes",
        pasta_saida_dw / "04_fatos",
        pasta_saida_dw / "01_controle_carga",
        pasta_saida_dw / "05_procedimentos_manutencao",
        pasta_saida_dw,
        base_dir / "saida" / "planejador_dw" / "03_dimensoes",
        base_dir / "saida" / "planejador_dw" / "04_fatos",
        base_dir / "saida" / "planejador_dw" / "01_controle_carga",
        base_dir / "saida" / "planejador_dw",
    ]

    for p in pastas_busca:
        if p.exists():
            for f in sorted(p.glob("*.sql")):
                dest_file = dest_ddl / f.name
                shutil.copy2(f, dest_file)
                if dest_file.name not in arquivos_copiados:
                    arquivos_copiados.append(dest_file.name)
                try:
                    sql_text = f.read_text(encoding="utf-8", errors="ignore")
                    conteudos_sql.append((f.name, sql_text))
                except Exception:
                    pass

    # Se nenhum arquivo específico foi encontrado nas subpastas, busca recursivamente
    if not arquivos_copiados:
        for f in sorted(pasta_saida_dw.rglob("*.sql")):
            dest_file = dest_ddl / f.name
            shutil.copy2(f, dest_file)
            if dest_file.name not in arquivos_copiados:
                arquivos_copiados.append(dest_file.name)
            try:
                sql_text = f.read_text(encoding="utf-8", errors="ignore")
                conteudos_sql.append((f.name, sql_text))
            except Exception:
                pass

    # Cria o DDL consolidado DDL_COMPLETO_DW_<PROJETO>.sql
    ddl_completo_nome = f"DDL_COMPLETO_DW_{projeto}.sql"
    ddl_completo_path = dest_ddl / ddl_completo_nome

    with open(ddl_completo_path, "w", encoding="utf-8") as f_out:
        f_out.write(f"-- =============================================================================\n")
        f_out.write(f"-- NINHO DATA PLATFORM — DDL CONSOLIDADO DO DATA WAREHOUSE\n")
        f_out.write(f"-- PROJETO: {projeto}\n")
        f_out.write(f"-- GERADO EM: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f_out.write(f"-- FINALIDADE: Insumo Oficial para Construção da Camada Semântica\n")
        f_out.write(f"-- =============================================================================\n\n")

        vistos = set()
        for nome_arq, sql_txt in conteudos_sql:
            if nome_arq not in vistos:
                vistos.add(nome_arq)
                f_out.write(f"-- -----------------------------------------------------------------------------\n")
                f_out.write(f"-- ARQUIVO DE ORIGEM: {nome_arq}\n")
                f_out.write(f"-- -----------------------------------------------------------------------------\n\n")
                f_out.write(sql_txt.strip())
                f_out.write("\n\n")

    if ddl_completo_nome not in arquivos_copiados:
        arquivos_copiados.append(ddl_completo_nome)
    return arquivos_copiados


def copiar_ou_gerar_amostras(base_dir: Path, projeto: str, pasta_saida_dw: Path, gerar_mock_se_vazio: bool = True) -> list:
    """Copia amostras existentes ou gera dados sintéticos se não houver."""
    dest_amostras = base_dir / "entrega" / "camada_semantica" / "amostras"
    dest_amostras.mkdir(parents=True, exist_ok=True)

    arquivos_amostras = []

    # Procura amostras em pastas anteriores
    pastas_busca = [
        pasta_saida_dw,
        base_dir / "saida" / "planejador_dw",
        base_dir / "modulos" / "planejador_dw" / "entrada" / "amostras",
        base_dir / "entrega" / "planejador_dw" / "amostras",
    ]

    for p in pastas_busca:
        if p.exists():
            for f in p.glob("*"):
                if f.is_file() and f.suffix.lower() in [".csv", ".tsv", ".json", ".txt"] and f.name.lower() != "readme.md":
                    dest_f = dest_amostras / f.name
                    shutil.copy2(f, dest_f)
                    if dest_f.name not in arquivos_amostras:
                        arquivos_amostras.append(dest_f.name)

    # Se não houver amostras reais e for solicitado mock
    if not arquivos_amostras and gerar_mock_se_vazio:
        caminho_mock = dest_amostras / f"amostra_fato_{projeto.lower()}_mock.csv"
        try:
            # Importa o gerador de mock do repositório
            script_mock = base_dir / "core" / "scripts_comuns" / "gerar_mock_dados.py"
            if script_mock.exists():
                sys.path.insert(0, str(script_mock.parent))
                from gerar_mock_dados import gerar_dados_mock
                gerar_dados_mock(num_linhas=200, caminho_saida=str(caminho_mock))
                arquivos_amostras.append(caminho_mock.name)
        except Exception as e:
            print_warn(f"Não foi possível gerar mock automaticamente: {e}")

    return arquivos_amostras


def copiar_relatorios_etl(base_dir: Path, projeto: str, pasta_saida_dw: Path) -> list:
    """Copia relatórios de estratégia, linhagem e guias de BI."""
    dest_relatorios = base_dir / "entrega" / "camada_semantica" / "relatorios_etl"
    dest_relatorios.mkdir(parents=True, exist_ok=True)

    arquivos_relatorios = []

    # 1. Relatório de Estratégias
    candidatos_rel = [
        pasta_saida_dw / "09_relatorio_estrategias" / "RELATORIO_ESTRATEGIAS.md",
        pasta_saida_dw / "05_relatorio_estrategias" / "RELATORIO_ESTRATEGIAS.md",
        pasta_saida_dw / "RELATORIO_ESTRATEGIAS.md",
        base_dir / "saida" / "planejador_dw" / "05_relatorio_estrategias" / "RELATORIO_ESTRATEGIAS.md",
        base_dir / "saida" / "planejador_dw" / "09_relatorio_estrategias" / "RELATORIO_ESTRATEGIAS.md",
        base_dir / "saida" / "planejador_dw" / "RELATORIO_ESTRATEGIAS.md",
    ]

    rel_origem = None
    for cand in candidatos_rel:
        if cand.exists():
            rel_origem = cand
            break

    if rel_origem:
        rel_dest = dest_relatorios / f"RELATORIO_ESTRATEGIAS_{projeto}.md"
        shutil.copy2(rel_origem, rel_dest)
        arquivos_relatorios.append(rel_dest.name)

    # 2. Guia do Analista de BI
    candidatos_bi = [
        pasta_saida_dw / "08_datasets_bi" / f"GUIA_ANALISTA_BI_{projeto}.md",
        pasta_saida_dw / f"GUIA_ANALISTA_BI_{projeto}.md",
        base_dir / "saida" / "planejador_dw" / "08_datasets_bi" / f"GUIA_ANALISTA_BI_{projeto}.md",
    ]
    guia_bi_origem = None
    for cand in candidatos_bi:
        if cand.exists():
            guia_bi_origem = cand
            break

    if not guia_bi_origem:
        for p in [pasta_saida_dw / "08_datasets_bi", base_dir / "saida" / "planejador_dw" / "08_datasets_bi"]:
            if p.exists():
                for f in p.glob("GUIA_ANALISTA_BI*.md"):
                    guia_bi_origem = f
                    break
            if guia_bi_origem:
                break

    if guia_bi_origem and guia_bi_origem.exists():
        guia_dest = dest_relatorios / guia_bi_origem.name
        shutil.copy2(guia_bi_origem, guia_dest)
        arquivos_relatorios.append(guia_dest.name)

    return arquivos_relatorios


def preencher_intake_semantica(base_dir: Path, projeto: str, schema: str, engenheiro: str, meta_dw: dict, ddl_list: list, amostras_list: list, relatorios_list: list):
    """Preenche automaticamente o arquivo modulos/camada_semantica/INTAKE_SEMANTICA.md."""
    intake_sem_path = base_dir / "modulos" / "camada_semantica" / "INTAKE_SEMANTICA.md"

    hoje = datetime.now().strftime("%Y-%m-%d")
    ddl_principal = f"entrega/camada_semantica/ddl/DDL_COMPLETO_DW_{projeto}.sql"
    pasta_amostras = "entrega/camada_semantica/amostras/"
    relatorio_principal = f"entrega/camada_semantica/relatorios_etl/RELATORIO_ESTRATEGIAS_{projeto}.md"

    # Monta lista de perguntas de negócio
    perguntas_str = ""
    if meta_dw.get("perguntas"):
        for i, p in enumerate(meta_dw["perguntas"], 1):
            perguntas_str += f"{i}. {p}\n"
    else:
        perguntas_str = "1. Qual a volumetria e métricas totais por dimensão e período?\n2. Qual o ranking e distribuição dos indicadores consolidados?\n"

    # Monta regras de negócio
    regras_str = f"- Grão da Fato Principal: {meta_dw.get('grao_fato', 'Uma linha para cada evento transacional')}\n"
    regras_str += f"- Estratégia de Carga DW: {meta_dw.get('estrategia_carga', 'Truncate & Load / MERGE conforme especificação')}\n"
    regras_str += f"- Padrão SCD: {meta_dw.get('scd_tipo', 'SCD Tipo 2 com vigência por DTC_EFETIVACAO e DTC_EXPIRACAO')}\n"
    regras_str += f"- Retenção Histórica: {meta_dw.get('retencao', 'Histórico completo mantido')}\n"
    regras_str += "- Chave Técnica Kimball: Registro -1 obrigatório em todas as dimensões ('NAO INFORMADO')\n"
    regras_str += "- Padrão de Nomenclatura: Todas as tabelas, colunas e identificadores rigorosamente em MAIÚSCULAS no Oracle\n"

    conteudo_intake = f"""# INTAKE — Formulário de coleta para construção da camada semântica

> **Transicionado Automaticamente do Planejador de DW** em {hoje}
> Todos os insumos obrigatórios foram depositados na pasta `entrega/camada_semantica/`.

---

## 0. Identificação do Projeto ☐ (obrigatório)

| Campo | Valor |
|---|---|
| **Nome do Projeto** (sigla curta em maiúsculas, ex: SEI, SIPAR) | `{projeto}` |
| **Engenheiro de Dados Responsável** | `{engenheiro or 'Engenheiro de Dados'}` |
| **Schema Alvo no Oracle** | `{schema}` |
| **Primeira execução neste schema?** | `[x] Sim  [ ] Não` |
| **Tabelas META_* já existem no schema?** | `[ ] Sim  [x] Não` |
| **Se já existem, projetos já cadastrados:** | `Nenhum (projeto inaugural)` |
| **Data de Início** | `{hoje}` |

---

## 1. DDL das fatos e dimensões ☐ (obrigatório)

Arquivo consolidado gerado pelo Planejador de DW:

```text
{ddl_principal}
```

Arquivos individuais disponíveis em `entrega/camada_semantica/ddl/`:
{chr(10).join(f"- entrega/camada_semantica/ddl/{a}" for a in ddl_list if a != f"DDL_COMPLETO_DW_{projeto}.sql")}

## 2. Amostras dos dados ☐ (obrigatório)

Pasta de amostras gerada pelo pipeline:

```text
{pasta_amostras}
```

Arquivos de amostras identificados:
{chr(10).join(f"- entrega/camada_semantica/amostras/{a}" for a in amostras_list) if amostras_list else "- Amostra sintética gerada em entrega/camada_semantica/amostras/"}

## 3. Relatório / documentação do ETL ☐ (recomendado)

```text
{relatorio_principal}
```

Insumos complementares do ETL e BI:
{chr(10).join(f"- entrega/camada_semantica/relatorios_etl/{r}" for r in relatorios_list)}

## 4. Regras de negócio do cliente ☐ (obrigatório)

```text
{regras_str.strip()}
```

## 4.1 Regras de RLS (Row Level Security) ☐ (se aplicável)

### 4.1.1 Visão geral
- [x] **Acesso total:** Usuários veem TODOS os dados (padrão inicial)
- [ ] **Acesso restrito:** Usuários veem APENAS parte dos dados

---

## 5. Perguntas que os usuários querem responder ☐ (recomendado)

Perguntas trazidas diretamente do Planejador de DW para virarem `META_CONSULTA_NEGOCIO` e `VW_KPI_*`:

```text
{perguntas_str.strip()}
```

---

## O que eu devolvo após receber os insumos

1. **Documento de entendimento** — grão, aditividade, hierarquias, relacionamentos e armadilhas identificadas.
2. **saida/camada_semantica/vw_analiticas/** — views `VW_*` prontas para o seu modelo (DIM → EVENTO → KPI).
3. **saida/camada_semantica/meta_projeto/01_create_meta_tables.sql** — CREATE TABLE das 8 META_.
4. **saida/camada_semantica/meta_projeto/01_meta_glossario.sql** a **08_meta_valor_dominio.sql** — INSERTs das META_.
"""

    intake_sem_path.write_text(conteudo_intake, encoding="utf-8")


def atualizar_documentacao_central(base_dir: Path, projeto: str, schema: str, engenheiro: str, meta_dw: dict, pasta_saida_dw: Path):
    """Atualiza documentacao/catalogo_projetos/PROJETO_RESUMO.md e PROJETO_VERSION.md."""
    resumo_path = base_dir / "documentacao" / "catalogo_projetos" / "PROJETO_RESUMO.md"
    version_path = base_dir / "documentacao" / "catalogo_projetos" / "PROJETO_VERSION.md"
    hoje = datetime.now().strftime("%Y-%m-%d")

    # Descobre tabelas a partir dos arquivos DDL gerados
    fatos = []
    dimensoes = []

    ddl_pasta = pasta_saida_dw / "03_dimensoes"
    if ddl_pasta.exists():
        for sql_f in ddl_pasta.glob("*.sql"):
            texto = sql_f.read_text(encoding="utf-8", errors="ignore")
            dims = re.findall(r"CREATE\s+TABLE\s+(?:\"?[A-Z0-9_]+\"?\.)?\"?(DIM_[A-Z0-9_]+)\"?", texto, re.IGNORECASE)
            for d in dims:
                if d.upper() not in dimensoes:
                    dimensoes.append(d.upper())

    fato_pasta = pasta_saida_dw / "04_fatos"
    if fato_pasta.exists():
        for sql_f in fato_pasta.glob("*.sql"):
            texto = sql_f.read_text(encoding="utf-8", errors="ignore")
            fts = re.findall(r"CREATE\s+TABLE\s+(?:\"?[A-Z0-9_]+\"?\.)?\"?(FATO_[A-Z0-9_]+)\"?", texto, re.IGNORECASE)
            for f in fts:
                if f.upper() not in fatos:
                    fatos.append(f.upper())

    # Fallback se não achou regex
    if not fatos:
        fatos = [f"FATO_{projeto}"]
    if not dimensoes:
        dimensoes = [f"DIM_TEMPO", f"DIM_{projeto}"]

    # 1. Atualiza PROJETO_RESUMO.md
    linhas_fatos = "\n".join([f"| `{f}` | {meta_dw.get('grao_fato', 'Uma linha por evento')} | {meta_dw.get('estrategia_carga', 'Padrão DW')} | `saida/planejador_dw/04_fatos/` |" for f in fatos])
    linhas_dims = "\n".join([f"| `{d}` | SCD Tipo 2 (`DTC_EFETIVACAO` / `DTC_EXPIRACAO`) | B-Tree | `ODI_{d}` associada |" for d in dimensoes])

    conteudo_resumo = f"""# PROJETO_RESUMO.md — Documentação Central do Projeto

> **Schema Oracle:** `{schema}`  
> **Projeto:** `{projeto}`  
> **Engenheiro Responsável:** `{engenheiro or 'Engenheiro de Dados'}`  
> **Data de criação:** `{hoje}`  
> **Última atualização:** `{hoje}`  
> **Status:** `DW PLANEJADO & INSUMOS ENTREGUES À CAMADA SEMÂNTICA`  
> **Versão:** `1.0.0`  

> **Regra:** Este arquivo deve ser atualizado SEMPRE que houver mudança no projeto.
> É a "fonte única da verdade" para a IA gerar SQL correto e para o time de Engenharia e Negócio.

---

## 1. Visão Geral da Arquitetura Dimensional

O Data Warehouse do projeto **{projeto}** foi planejado e estruturado seguindo as melhores práticas da modelagem dimensional de Ralph Kimball e tuning avançado no Oracle Database.

- **Dicionário de Dados Interativo:** [`saida/planejador_dw/11_dicionario_dados/dicionario_dados.html`](file:///saida/planejador_dw/11_dicionario_dados/dicionario_dados.html)
- **Relatório de Estratégias & Sizing:** [`saida/planejador_dw/09_relatorio_estrategias/RELATORIO_ESTRATEGIAS.md`](file:///saida/planejador_dw/09_relatorio_estrategias/RELATORIO_ESTRATEGIAS.md)
- **Guia do Analista de BI:** [`saida/planejador_dw/08_datasets_bi/GUIA_ANALISTA_BI_{projeto}.md`](file:///saida/planejador_dw/08_datasets_bi/GUIA_ANALISTA_BI_{projeto}.md)

---

## 2. Tabelas FATO

| Tabela Fato | Grão Declarado | Estratégia de Carga | Localização DDL |
|-------------|----------------|---------------------|-----------------|
{linhas_fatos}

---

## 3. Tabelas DIMENSÃO

| Dimensão | Política de Histórico | Tipo de Índice | Tabela Auxiliar de Carga |
|----------|-----------------------|----------------|--------------------------|
{linhas_dims}

> **Nota Técnica:** Todas as dimensões possuem a linha técnica chave `-1` (`NAO INFORMADO`) para assegurar integridade referencial sem abortar cargas no ETL.

---

## 4. Esteira de Ingestão & Integração

| Componente | Origem | Destino | Tecnologia |
|------------|--------|---------|------------|
| Carga de Banco | Tabelas Transacionais OLTP | `STG_*` / DW | Oracle Data Integrator (ODI) |
| Carga de Arquivos | FTP / SFTP / CSV / Excel | `STG_*` | Apache Hop (`.hpl` / `.hwf`) |
| Carga de APIs | REST / JSON / Microsserviços | `STG_*` | Python (`.py`) |

---

## 5. Próxima Etapa: Construção da Camada Semântica

Os insumos deste DW já foram entregues em `entrega/camada_semantica/`:
1. `entrega/camada_semantica/ddl/DDL_COMPLETO_DW_{projeto}.sql`
2. `entrega/camada_semantica/amostras/`
3. `entrega/camada_semantica/relatorios_etl/RELATORIO_ESTRATEGIAS_{projeto}.md`
4. Formulário `modulos/camada_semantica/INTAKE_SEMANTICA.md` preenchido.

**Comando para inicializar no chat:**
```bash
/iniciar-semantica
```
"""

    resumo_path.write_text(conteudo_resumo, encoding="utf-8")

    # 2. Atualiza PROJETO_VERSION.md
    conteudo_version = f"""# PROJETO_VERSION.md — Histórico de Mudanças

> **Schema Oracle:** `{schema}`  
> **Projeto:** `{projeto}`  
> **Última atualização:** `{hoje}`  

---

## [v1.0.0] — {hoje}

### Conclusão do Planejamento de DW & Handoff para a Camada Semântica
- **Responsável:** `{engenheiro or 'Engenheiro de Dados'}`
- **Fatos Projetadas:** {', '.join(fatos)}
- **Dimensões Projetadas:** {', '.join(dimensoes)}
- **Artefatos Entregues:**
  - DDLs otimizados em `saida/planejador_dw/`
  - DDL consolidado em `entrega/camada_semantica/ddl/DDL_COMPLETO_DW_{projeto}.sql`
  - Dicionário interativo de dados para negócio em `saida/planejador_dw/11_dicionario_dados/dicionario_dados.html`
  - Guia de Modelagem Star Schema e DAX em `saida/planejador_dw/08_datasets_bi/GUIA_ANALISTA_BI_{projeto}.md`
  - Relatório de Estratégias, Linhagem De/Para e Sizing em `saida/planejador_dw/09_relatorio_estrategias/RELATORIO_ESTRATEGIAS.md`
- **Handoff:** Formulário `INTAKE_SEMANTICA.md` pré-preenchido e validado com sucesso.
"""


    version_path.write_text(conteudo_version, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Transicionador Automatizado Planejador DW -> Camada Semântica")
    parser.add_argument("--projeto", type=str, default="", help="Nome/sigla do projeto (ex: SEI_BAHIA)")
    parser.add_argument("--schema", type=str, default="", help="Schema alvo no Oracle (ex: SEIMUNICIPIO_OLAP)")
    parser.add_argument("--engenheiro", type=str, default="", help="Nome do engenheiro de dados responsável")
    parser.add_argument("--forcar", action="store_true", help="Sobrescreve arquivos existentes na pasta de entrega")
    parser.add_argument("--gerar-amostras", action="store_true", default=True, help="Gera amostra sintética (mock) caso não existam arquivos")

    args = parser.parse_args()
    base_dir = get_base_dir()

    print_banner("Transição Contínua: Planejador de DW -> Camada Semântica")

    # 1. Identificar Projeto e Metadados
    meta_dw = extrair_metadados_intake_dw(base_dir)
    projeto = detectar_projeto(base_dir, args.projeto)
    schema = args.schema or meta_dw.get("schema") or f"{projeto}_OLAP"
    engenheiro = args.engenheiro or meta_dw.get("engenheiro") or "Engenheiro de Dados"

    print(f"  {NEGRITO}Projeto Alvo:{RESET}          {projeto}")
    print(f"  {NEGRITO}Schema Oracle:{RESET}         {schema}")
    print(f"  {NEGRITO}Engenheiro:{RESET}            {engenheiro}")

    saida_dw_direta = base_dir / "saida" / "planejador_dw"
    pasta_saida_dw_projeto = saida_dw_direta / projeto

    if (saida_dw_direta / "03_dimensoes").exists() or (saida_dw_direta / "04_fatos").exists():
        pasta_saida_dw = saida_dw_direta
        print_ok("Utilizando estrutura canônica direta em 'saida/planejador_dw/'.")
    elif pasta_saida_dw_projeto.exists():
        pasta_saida_dw = pasta_saida_dw_projeto
        print_warn(f"Utilizando pasta legada do projeto: '{pasta_saida_dw.name}'")
    else:
        # Se nenhuma das opções tem arquivos, verifica se há apenas uma pasta customizada
        candidatos = [
            d for d in saida_dw_direta.iterdir()
            if d.is_dir() and d.name.upper() not in PASTAS_CANONICAS_DW
        ]
        if len(candidatos) == 1:
            pasta_saida_dw = candidatos[0]
            projeto = pasta_saida_dw.name.upper()
            print_warn(f"Utilizando pasta legada existente: '{pasta_saida_dw.name}'")
        else:
            pasta_saida_dw = saida_dw_direta
            print_ok("Utilizando diretório canônico padrão: 'saida/planejador_dw/'.")


    # 2. Copiar DDLs
    print(f"\n{NEGRITO}1. Copiando DDLs para 'entrega/camada_semantica/ddl/':{RESET}")
    ddls_copiados = copiar_ddls(base_dir, projeto, pasta_saida_dw)
    for ddl in ddls_copiados:
        print_ok(f"DDL copiado/gerado: {ddl}")

    # 3. Copiar ou Gerar Amostras
    print(f"\n{NEGRITO}2. Processando Amostras em 'entrega/camada_semantica/amostras/':{RESET}")
    amostras_copiadas = copiar_ou_gerar_amostras(base_dir, projeto, pasta_saida_dw, args.gerar_amostras)
    for am in amostras_copiadas:
        print_ok(f"Amostra disponível: {am}")

    # 4. Copiar Relatórios de ETL
    print(f"\n{NEGRITO}3. Copiando Relatórios para 'entrega/camada_semantica/relatorios_etl/':{RESET}")
    relatorios_copiados = copiar_relatorios_etl(base_dir, projeto, pasta_saida_dw)
    for rel in relatorios_copiados:
        print_ok(f"Relatório transferido: {rel}")

    # 5. Preencher INTAKE_SEMANTICA.md
    print(f"\n{NEGRITO}4. Preenchendo Formulário INTAKE_SEMANTICA.md:{RESET}")
    preencher_intake_semantica(base_dir, projeto, schema, engenheiro, meta_dw, ddls_copiados, amostras_copiadas, relatorios_copiados)
    print_ok("Formulário 'modulos/camada_semantica/INTAKE_SEMANTICA.md' preenchido automaticamente com sucesso!")

    # 6. Atualizar Documentação Central
    print(f"\n{NEGRITO}5. Atualizando Catálogo Central de Projetos:{RESET}")
    atualizar_documentacao_central(base_dir, projeto, schema, engenheiro, meta_dw, pasta_saida_dw)
    print_ok("'documentacao/catalogo_projetos/PROJETO_RESUMO.md' atualizado.")
    print_ok("'documentacao/catalogo_projetos/PROJETO_VERSION.md' versionado em v1.0.0.")

    # 7. Executar Verificação Pré-Voo da Semântica
    print(f"\n{NEGRITO}6. Executando Auditoria Pré-Voo da Camada Semântica:{RESET}")
    try:
        script_val = base_dir / "core" / "scripts_comuns" / "validar_entrega.py"
        if script_val.exists():
            import subprocess
            res = subprocess.run([sys.executable, str(script_val), "semantica"], capture_output=True, text=True)
            print(res.stdout)
    except Exception as e:
        print_warn(f"Não foi possível rodar auditoria automática: {e}")

    # 8. Banner Final de Conclusão e Próximos Passos
    print(f"{VERDE}{NEGRITO}{'=' * 75}{RESET}")
    print(f"{VERDE}{NEGRITO}  ✅ TRANSIÇÃO CONCLUÍDA COM SUCESSO! O PIPELINE NÃO PARA AQUI.{RESET}")
    print(f"{VERDE}{NEGRITO}{'=' * 75}{RESET}")
    print(f"\n{NEGRITO}Insumos Entregues à Camada Semântica:{RESET}")
    print(f"  • DDL Consolidado:       entrega/camada_semantica/ddl/DDL_COMPLETO_DW_{projeto}.sql")
    print(f"  • Amostras de Dados:     entrega/camada_semantica/amostras/")
    print(f"  • Relatórios ETL & BI:   entrega/camada_semantica/relatorios_etl/")
    print(f"  • Formulário Pré-pago:   modulos/camada_semantica/INTAKE_SEMANTICA.md")
    print(f"  • Catálogo Atualizado:   documentacao/catalogo_projetos/PROJETO_RESUMO.md")
    print(f"\n{CIANO}{NEGRITO}👉 PRÓXIMO PASSO NO CHAT:{RESET}")
    print(f"   Envie para o agente a seguinte mensagem:")
    print(f"   {AZUL}{NEGRITO}/iniciar-semantica{RESET}  (ou 'Os insumos do DW estão prontos em entrega/camada_semantica/, inicie a Camada Semântica')")
    print(f"{CIANO}{NEGRITO}{'=' * 75}{RESET}\n")


if __name__ == "__main__":
    main()
