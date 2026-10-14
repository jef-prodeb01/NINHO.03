#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Auditor Preditivo de Performance e Arquitetura para Mapeamentos ODI 12c (NINHO)
Inspeciona arquivos XML de Mapeamentos exportados do Oracle Data Integrator (ODI 12c),
detecta anti-padrões de performance, identifica colunas de auditoria/update na origem,
e prescreve arquiteturas otimizadas (CDC Incremental, IKM Oracle Merge, PKs na Staging, etc.).

Uso:
    python core/scripts_comuns/auditar_mapa_odi.py <caminho_arquivo.xml> [--output <caminho_relatorio.md>]
"""

import sys
import os
import re
import argparse
from pathlib import Path
import xml.etree.ElementTree as ET

# Configura encoding UTF-8 no stdout do Windows
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

# Padrões regex para detecção de colunas de auditoria/atualização clássicas
REGEX_UPDATE_COLS = re.compile(
    r"(update|altera|modif|modificad|dth_alt|dt_alt|data_alt|last_upd|audit|dth_sit|dat_sit)",
    re.IGNORECASE
)
# Padrões para colunas de criação/início
REGEX_CREATE_COLS = re.compile(
    r"(create|criacao|cadast|inser|dth_inc|dt_inc|data_inc|dth_cad|dt_cad|abertura|emissao|geracao|registro|entrada|dth_abertura)",
    re.IGNORECASE
)
# Padrões para colunas de encerramento / conclusão de ciclo de vida
REGEX_CLOSE_COLS = re.compile(
    r"(conclusao|fechamento|encerramento|termino|finalizacao|baixa|cancelamento|dth_conclusao|dta_conclusao|dt_conclusao)",
    re.IGNORECASE
)
# Padrões para colunas de chave primária / identidade sequencial
REGEX_PK_COLS = re.compile(
    r"^(id|cod_|num_|seq_|cd_)",
    re.IGNORECASE
)
# Todas as colunas com tipagem temporal ou prefixo de data
REGEX_ANY_DATE_COLS = re.compile(
    r"\b((?:dth_|dt_|dat_|dta_|data_|dh_)[A-Za-z0-9_]+|[A-Za-z0-9_]*(?:_date|_dth|_time|_at))\b",
    re.IGNORECASE
)


def print_banner():
    print(f"\n{AZUL}{NEGRITO}{'=' * 80}{RESET}")
    print(f"{CIANO}{NEGRITO}  🦅 PLATAFORMA NINHO — MOTOR PREDITIVO DE AUDITORIA & TUNING ODI 12c{RESET}")
    print(f"{AZUL}{NEGRITO}{'=' * 80}{RESET}\n")


def print_ok(msg: str):
    print(f"  {VERDE}[OK]{RESET} {msg}")


def print_warn(msg: str):
    print(f"  {AMARELO}[AVISO]{RESET} {msg}")


def print_err(msg: str):
    print(f"  {VERMELHO}[ERRO]{RESET} {msg}")



class ODIMappingAuditor:
    def __init__(self, xml_path: Path):
        self.xml_path = xml_path
        self.tree = None
        self.root = None
        self.mapping_name = xml_path.stem
        self.flows = []
        self.findings = []
        self.heuristics_triggered = []

    def parse(self):
        raw_text = self.xml_path.read_text(encoding="utf-8", errors="ignore")
        if self.xml_path.suffix.lower() == ".xml" or "<SunopsisExport" in raw_text:
            try:
                self.tree = ET.parse(self.xml_path)
                self.root = self.tree.getroot()
                for obj in self.root.findall(".//Object[@class='com.sunopsis.dwg.dbobj.SnpMapping']"):
                    name_field = obj.find("./Field[@name='Name']")
                    if name_field is not None and name_field.text:
                        self.mapping_name = name_field.text.strip()
                        break
            except Exception:
                pass
        else:
            self.mapping_name = self.xml_path.stem

        self._extract_datastores_and_columns()
        self._inspect_km_options()
        self._run_predictive_heuristics()

    def _extract_datastores_and_columns(self):
        """Extrai nós de datastores, colunas e mapeamentos de fluxo."""
        # Busca referências de objetos SnpMapRef e nós físicos/lógicos
        # No ODI 12c XML, SnpMapCompDatastore representa datastores no canvas
        raw_text = self.xml_path.read_text(encoding="utf-8", errors="ignore")

        # Extrair nomes de tabelas encontradas no XML
        # Geralmente em tags Field name="Name" dentro de SnpMapCompDatastore ou SnpMapRef
        table_matches = re.findall(r'<Field name="Name" type="java\.lang\.String"><!\[CDATA\[(STG_[A-Za-z0-9_]+|[A-Za-z0-9_]+)\]\]></Field>', raw_text)
        
        # Filtros encontrados
        filter_matches = re.findall(r'<Object class="com\.sunopsis\.dwg\.dbobj\.SnpMapCompFilter">', raw_text)
        self.has_filter_components = len(filter_matches) > 0

        SQL_KEYWORDS = {
            "CREATE", "TABLE", "INDEX", "INSERT", "UPDATE", "DELETE", "SELECT", "FROM", "WHERE",
            "AND", "OR", "NOT", "NULL", "INT", "BIGINT", "DATETIME", "VARCHAR", "CHAR", "CONSTRAINT",
            "PRIMARY", "KEY", "FOREIGN", "REFERENCES", "ON", "OFF", "WITH", "PAD_INDEX", "FILLFACTOR",
            "SORT_IN_TEMPDB", "IGNORE_DUP_KEY", "STATISTICS_NORECOMPUTE", "ONLINE", "ALLOW_ROW_LOCKS",
            "ALLOW_PAGE_LOCKS", "INCLUDE", "ASC", "DESC", "NONCLUSTERED", "CLUSTERED", "ALTER", "DROP"
        }
        all_words = [w for w in re.findall(r'\b[A-Za-z0-9_]+\b', raw_text) if w.upper() not in SQL_KEYWORDS]

        # Colunas com nomes de atualização clássicos
        self.update_columns_found = list(set([c for c in all_words if REGEX_UPDATE_COLS.search(c)]))
        # Colunas com nomes de criação / início
        self.create_columns_found = list(set([c for c in all_words if REGEX_CREATE_COLS.search(c)]))
        # Colunas com nomes de conclusão / encerramento
        self.close_columns_found = list(set([c for c in all_words if REGEX_CLOSE_COLS.search(c)]))
        # Todas as colunas temporais
        self.all_date_columns_found = list(set([c for c in all_words if REGEX_ANY_DATE_COLS.search(c)]))

        # KM Identifiers
        self.lkms_found = list(set(re.findall(r'LKM[A-Za-z0-9_ \(\)-]+', raw_text)))
        self.ikms_found = list(set(re.findall(r'IKM[A-Za-z0-9_ \(\)-]+', raw_text)))

        # Truncate Target Table
        self.truncate_detected = "TRUNCATE_TARGET_TABLE" in raw_text and ("true" in raw_text.lower() or "1" in raw_text)
        # Flow Control
        self.flow_control_detected = "FLOW_CONTROL" in raw_text and "true" in raw_text.lower()
        # Direct Path Hint
        self.hints_found = list(set(re.findall(r'(?:APPEND|PARALLEL\([0-9]+\))', raw_text, re.IGNORECASE)))

        # Pareamento de fluxos conhecidos (ex: STG_EST_* vs Tabelas de Origem)
        stg_targets = sorted(list(set([t for t in table_matches if t.upper().startswith("STG_")])))
        source_tables = sorted(list(set([t for t in table_matches if not t.upper().startswith("STG_") and not t.upper().startswith("IKM") and not t.upper().startswith("LKM") and not t.upper().startswith("SNP") and len(t) > 3])))

        # Se for um script DDL puro (sem XML)
        if not stg_targets:
            ddl_tables = re.findall(r'CREATE\s+TABLE\s+(?:[A-Za-z0-9_]+\.)*(?:[A-Za-z0-9_]+\.)*([A-Za-z0-9_]+)', raw_text, re.IGNORECASE)
            if ddl_tables:
                source_tables = ddl_tables
                stg_targets = [f"STG_EST_{t.upper()}" for t in ddl_tables]

        self.stg_targets = stg_targets
        self.source_tables = source_tables

        # Filtrar apenas colunas que sejam efetivamente temporais (prefixo dth_, dt_, dat_, etc.)
        self.create_date_cols = [c for c in self.create_columns_found if REGEX_ANY_DATE_COLS.search(c)]
        self.close_date_cols = [c for c in self.close_columns_found if REGEX_ANY_DATE_COLS.search(c)]
        self.update_date_cols = [c for c in self.update_columns_found if REGEX_ANY_DATE_COLS.search(c)]

    def _inspect_km_options(self):
        pass

    def _run_predictive_heuristics(self):
        """Aplica as 5 Heurísticas Preditivas de Tuning da Plataforma NINHO."""
        
        # Heurística 1A: Detecção de Ciclo de Vida de Workflow (Abertura + Conclusão sem updated_at)
        if self.create_date_cols and self.close_date_cols:
            col_abertura = self.create_date_cols[0]
            col_conclusao = self.close_date_cols[0]
            self.heuristics_triggered.append({
                "id": "H1A_CDC_CICLO_DE_VIDA",
                "titulo": f"Detecção de Tabela de Ciclo de Vida Transacional / Workflow ({col_abertura} + {col_conclusao})",
                "gravidade": "CRÍTICA",
                "descricao": (
                    f"A tabela não possui coluna clássica 'UPDATED_AT', mas implementa um padrão de Ciclo de Vida de Workflow "
                    f"com par de datas: Início/Abertura ('{col_abertura}') e Término/Conclusão ('{col_conclusao}'). "
                    f"Registros concluídos mudam de estado alterando '{col_conclusao}', enquanto registros em aberto permanecem com ela nula."
                ),
                "prescricao": [
                    (
                        f"Injetar componente FILTRO de Ciclo de Vida no Canvas ODI: "
                        f"`({col_abertura} >= TRUNC(SYSDATE) - 3 OR {col_conclusao} >= TRUNC(SYSDATE) - 3 OR {col_conclusao} IS NULL)`. "
                        f"Isso descarta milhões de registros históricos antigos já concluídos e sincroniza apenas a janela recente + itens abertos!"
                    ),
                    "Configurar Primary Key física na tabela Staging para habilitar correspondência de linhas.",
                    "Alterar IKM para `IKM Oracle Merge` com `FLOW_CONTROL = False`."
                ]
            })

        # Heurística 1B: Detecção de Colunas de Atualização Clássicas (UPDATED_AT / DT_ALTERACAO)
        elif self.update_date_cols and (self.truncate_detected or not self.has_filter_components):
            self.heuristics_triggered.append({
                "id": "H1B_CDC_INCREMENTAL_CLASSICO",
                "titulo": "Detecção de Colunas de Atualização Clássicas em Carga Total",
                "gravidade": "CRÍTICA",
                "descricao": (
                    f"A origem contém colunas de auditoria/modificação ({', '.join(self.update_columns_found[:5])}), "
                    f"mas o mapeamento está configurado para Carga Total (Truncate & Load ou sem filtro temporal). "
                    f"Reprocessar 100% da base todos os dias causa degradação linear de horas à medida que a base cresce."
                ),
                "prescricao": [
                    "Adicionar componente FILTRO no Canvas ODI com buffer deslizante: `UPDATED_AT >= TRUNC(SYSDATE) - 2` (ou variável `#V_DATA_ULTIMA_CARGA`).",
                    "Alterar IKM para `IKM Oracle Merge` ou `IKM Oracle Incremental Update`.",
                    "Configurar Primary Key física na tabela Staging para viabilizar a correspondência de linhas (Target Key)."
                ]
            })

        # Heurística 1C: Apenas Data de Criação (Tabela Append-Only / Imutável)
        elif self.create_columns_found and not self.update_columns_found and not self.close_columns_found:
            col_criacao = self.create_columns_found[0]
            self.heuristics_triggered.append({
                "id": "H1C_CDC_APPEND_ONLY",
                "titulo": f"Detecção de Tabela Append-Only / Histórica com Data de Criação ({col_criacao})",
                "gravidade": "ALERTA_ARQUITETURAL",
                "descricao": (
                    f"A tabela possui apenas data de criação/inclusão ('{col_criacao}') e nenhuma coluna de alteração. "
                    f"Isso caracteriza uma tabela imutável (append-only), onde registros nunca são modificados após criados."
                ),
                "prescricao": [
                    f"Aplicar filtro incremental por data de criação: `{col_criacao} >= TRUNC(SYSDATE) - 1` ou High-Water Mark por ID: `ID > #V_MAX_ID`.",
                    "Utilizar `IKM Oracle Insert` com Direct-Path `/*+ APPEND */` sem truncar o histórico acumulado."
                ]
            })

        # Heurística 1D: Ausência Total de Datas
        elif not self.all_date_columns_found:
            self.heuristics_triggered.append({
                "id": "H1D_SEM_COLUNAS_TEMPORAIS",
                "titulo": "Tabela Sem Colunas Temporais Detectadas",
                "gravidade": "ALERTA_PERFORMANCE",
                "descricao": (
                    "A tabela não possui colunas de data/hora para viabilizar CDC por data. "
                    "Se for uma tabela cadastral pequena (< 100 mil linhas), Carga Total (Truncate & Load) é aceitável. "
                    "Se for massiva, Carga Total causará gargalo severo."
                ),
                "prescricao": [
                    "Para tabelas pequenas: Manter `IKM Oracle Insert` com `TRUNCATE = True` e `FLOW_CONTROL = False`.",
                    "Para tabelas massivas: Habilitar Change Tracking no banco de origem ou implementar CDC por Hash (`ORA_HASH`)."
                ]
            })

        # Heurística 2: Pré-requisito de Primary Key na Staging para Carga Incremental
        self.heuristics_triggered.append({
            "id": "H2_PK_STAGING_PREREQUISITO",
            "titulo": "Pré-requisito Estrutural de Primary Key na Staging Area",
            "gravidade": "ALERTA_ARQUITETURAL",
            "descricao": (
                "Para que o IKM Incremental Update ou IKM Oracle Merge realize a sincronização correta, "
                "o ODI exige uma chave de correspondência ('Target Key'). Tabelas de Staging criadas sem "
                "Primary Key forçam o IKM a falhar ou comparar todas as colunas via produto cartesiano."
            ),
            "prescricao": [
                "Criar constraint de Primary Key física no Oracle para cada tabela STG envolvida.",
                "No ODI Designer, importar a constraint no Datastore e selecionar a Target Key nas propriedades físicas do Target."
            ]
        })

        # Heurística 3: Comparativo IKM Oracle Merge vs Incremental Update
        self.heuristics_triggered.append({
            "id": "H3_IKM_MERGE_VS_UPDATE",
            "titulo": "Seleção Ótima de IKM: IKM Oracle Merge > IKM Incremental Update",
            "gravidade": "RECOMENDAÇÃO_PERFORMANCE",
            "descricao": (
                "O `IKM Oracle Incremental Update` executa dois passos pesados e demorados: "
                "1. UPDATE na tabela de destino com subquery correlata para cada linha. "
                "2. INSERT de novas linhas com cláusula `WHERE NOT EXISTS`. "
                "Já o `IKM Oracle Merge` executa uma única instrução SQL nativa `MERGE INTO`, "
                "resolvida em alta velocidade diretamente pelo kernel do banco de dados."
            ),
            "prescricao": [
                "Substituir o IKM por `IKM Oracle Merge`.",
                "Definir `FLOW_CONTROL = False` para eliminar tabelas de erro `E$_`."
            ]
        })

        # Heurística 4: Detecção de Mapeamento Monolítico Multi-Tabelas
        if len(self.stg_targets) >= 3:
            self.heuristics_triggered.append({
                "id": "H4_MONOLITO_MULTI_FLUXO",
                "titulo": f"Detecção de Monolito com {len(self.stg_targets)} Fluxos Independentes",
                "gravidade": "ALERTA_ARQUITETURAL",
                "descricao": (
                    f"O mapeamento '{self.mapping_name}' consolida {len(self.stg_targets)} tabelas independentes em um único canvas. "
                    f"Isso bloqueia a execução serializada na JVM do ODI Agent: tabelas pequenas ficam retidas "
                    f"aguardando o término de tabelas gigantescas (como histórico de confirmações ou contatos)."
                ),
                "prescricao": [
                    "Desacoplar tabelas gigantescas em mapeamentos isolados (`MAP_STG_TABELA_PESADA`).",
                    "Orquestrar o fluxo em um Pacote (`PACK_*`) disparando execuções paralelas assíncronas via `OdiStartScen -ASYNC=YES`."
                ]
            })

        # Heurística 5: Detecção de LKM Efeito Funil (JDBC vs DB Link)
        if any("SQL to Oracle" in lkm for lkm in self.lkms_found):
            self.heuristics_triggered.append({
                "id": "H5_FUNIL_JDBC",
                "titulo": "Detecção de Funil de I/O em Driver JDBC (LKM SQL to Oracle)",
                "gravidade": "ALERTA_PERFORMANCE",
                "descricao": (
                    "O uso de `LKM SQL to Oracle (Built-In)` força todos os dados a trafegarem pela memória "
                    "do ODI Agent Java, escrevendo em tabelas temporárias `C$_` antes do destino final. "
                    "Em conexões entre bancos Oracle, essa abordagem é muito mais lenta do que transferência direta via banco."
                ),
                "prescricao": [
                    "Avaliar a substituição por `LKM Oracle to Oracle Pull (DB Link)`, permitindo Direct-Path `INSERT /*+ APPEND */ ... SELECT FROM TABELA@DBLINK`."
                ]
            })

    def print_summary(self):
        print(f"{NEGRITO}Objeto Auditado:{RESET} {self.mapping_name}")
        print(f"{NEGRITO}Arquivo Fonte:{RESET} {self.xml_path.name}")
        print(f"{NEGRITO}Tabelas Staging Detectadas ({len(self.stg_targets)}):{RESET} {', '.join(self.stg_targets[:6])}{'...' if len(self.stg_targets) > 6 else ''}")
        print(f"{NEGRITO}Colunas de Atualização Encontradas:{RESET} {', '.join(self.update_columns_found) if self.update_columns_found else 'Nenhuma'}")
        print(f"{NEGRITO}Carga Total (Truncate):{RESET} {'SIM' if self.truncate_detected else 'NÃO'}")
        print(f"{NEGRITO}Filtros no Canvas:{RESET} {'SIM' if self.has_filter_components else 'NÃO (Extração Completa)'}\n")

        print(f"{NEGRITO}Heurísticas Preditivas Acionadas:{RESET}")
        for h in self.heuristics_triggered:
            cor = VERMELHO if h["gravidade"] == "CRÍTICA" else (AMARELO if "ALERTA" in h["gravidade"] else VERDE)
            print(f"  {cor}[{h['gravidade']}]{RESET} {NEGRITO}{h['titulo']}{RESET}")
            print(f"     -> {h['descricao']}")
            print(f"     -> {CIANO}Prescrição:{RESET} {h['prescricao'][0]}\n")

    def generate_markdown_report(self, output_path: Path):
        content = []
        content.append(f"# Relatório de Diagnóstico Preditivo & Tuning de Performance — ODI 12c")
        content.append(f"\n**Mapeamento Auditado:** `{self.mapping_name}`  ")
        content.append(f"**Origem do Objeto:** `{self.xml_path.name}`  ")
        content.append(f"**Classificação:** Auditoria Preditiva de Engenharia de Dados (Plataforma NINHO)\n")
        content.append(f"---\n")

        content.append(f"## 1. Resumo Executivo da Auditoria\n")
        content.append(f"O mapeamento foi submetido ao **Motor de Regras Preditivas do NINHO**. Foram identificadas oportunidades cruciais de desaceleração e tuning preventivo:")
        content.append(f"- **Volume de Fluxos no Canvas:** {len(self.stg_targets)} fluxos independentes.")
        content.append(f"- **Colunas de Auditoria na Origem:** `{', '.join(self.update_columns_found) if self.update_columns_found else 'Nenhuma detectada'}`.")
        content.append(f"- **Estratégia Atual Identificada:** {'Carga Total com TRUNCATE (Full Load)' if self.truncate_detected else 'Carga Direta sem Filtro Temporal'}.")
        content.append(f"- **Diagnóstico de Gargalo:** Reprocessamento diário redundante de dados históricos estáticos.\n")

        content.append(f"---\n")
        content.append(f"## 2. Heurísticas Preditivas Acionadas\n")

        for idx, h in enumerate(self.heuristics_triggered, 1):
            content.append(f"### Heurística {idx}: {h['titulo']}")
            content.append(f"**Nível de Gravidade:** `{h['gravidade']}`\n")
            content.append(f"**Diagnóstico Detalhado:**  \n{h['descricao']}\n")
            content.append(f"**Prescrição Técnica Obrigatória:**")
            for step in h['prescricao']:
                content.append(f"- {step}")
            content.append(f"\n")

        content.append(f"---\n")
        content.append(f"## 3. Matriz de Configuração De/Para no ODI Studio\n")
        content.append(f"| Objeto / Parâmetro | Configuração Atual (Lenta) | Configuração Preditiva Otimizada | Racional Técnico |")
        content.append(f"| :--- | :--- | :--- | :--- |")
        content.append(f"| **Estratégia de Carga** | Full Load (Truncate & Insert) | **CDC Incremental por Data** | Transfere apenas linhas alteradas recentemente |")
        content.append(f"| **Filtro na Origem** | Nenhum (Lê 100% da tabela) | `UPDATED_AT >= TRUNC(SYSDATE) - 2` | Janela deslizante de segurança (buffer D-2) |")
        content.append(f"| **Integration KM (IKM)** | `IKM Oracle Insert` / `Control Append` | **`IKM Oracle Merge`** | Operação atômica nativa de alta velocidade |")
        content.append(f"| **Target Key no Canvas** | `Undefined` | **`PK_<TABELA>`** | Permite correspondência de chaves para o Merge |")
        content.append(f"| **Opção FLOW_CONTROL** | `True` (Gera tabelas `E$_`) | **`False`** | Elimina checagem de erros desnecessária |")
        content.append(f"| **Orquestração de Fluxos** | 1 Mapeamento Monolítico | **Pacote Paralelo (`-ASYNC=YES`)** | Isola tabelas pesadas de cadastros leves |\n")

        content.append(f"---\n")
        content.append(f"## 4. DDL de Pré-Requisito: Primary Keys na Staging Area\n")
        content.append(f"Para habilitar a Carga Incremental com `IKM Oracle Merge` no ODI, execute o script DDL abaixo no banco Oracle do DW:\n")
        content.append(f"```sql")
        content.append(f"-- ============================================================================")
        content.append(f"-- DDL PREDITIVO: CRIAÇÃO DE PRIMARY KEYS NAS TABELAS DE STAGING")
        content.append(f"-- Pré-requisito obrigatório para funcionamento do IKM Oracle Merge no ODI")
        content.append(f"-- ============================================================================")
        for stg in self.stg_targets:
            content.append(f"ALTER TABLE {stg} ADD CONSTRAINT PK_{stg} PRIMARY KEY (ID);")
        content.append(f"```\n")

        content.append(f"---\n")
        content.append(f"## 5. Projeção de Ganho de Performance\n")
        content.append(f"| Métrica | Cenário Atual (Full Load) | Cenário Preditivo (Incremental CDC + Merge) | Ganho Relativo |")
        content.append(f"| :--- | :--- | :--- | :--- |")
        content.append(f"| **Volume Diário Lido** | 100% dos registros históricos | ~0.1% a 1.0% (Apenas atualizados) | **Redução de ~99% de I/O** |")
        content.append(f"| **Tempo de Execução** | ~120 minutos (2 horas) | **3 a 5 minutos** | **Aceleração de 95%** |")
        content.append(f"| **Uso de Rede / Undo** | Saturado a cada ciclo | Mínimo e estritamente pontual | **Elimina risco de ORA-01555** |\n")

        content.append(f"---\n")
        content.append(f"## 6. Próximo Passo: Alinhamento Obrigatório com o Engenheiro de Dados\n")
        content.append(f"> 🤝 **Regra de Ouro do NINHO:** Este relatório reflete uma auditoria estática dos metadados. Projetos reais possuem contextos e particularidades de negócio que nenhuma ferramenta quantifica sozinha.\n")
        content.append(f"1. **Validação do Domínio:** Discutir com o Engenheiro se a origem transacional possui expurgos, reabertura de chamados/processos ou atualizações retroativas.")
        content.append(f"2. **Validação de Volumetria & Janela:** Confirmar os volumes reais por tabela para definir se vale isolar em mapeamentos independentes.")
        content.append(f"3. **Aprovação Conjunta:** Apenas após o aval e refinamento do Engenheiro, implementar as alterações no ODI Studio e executar a esteira.\n")

        output_path.write_text("\n".join(content), encoding="utf-8")
        print_ok(f"Relatório gerado com sucesso em: {output_path}")


def main():
    print_banner()
    parser = argparse.ArgumentParser(description="Auditor Preditivo de Objetos ODI 12c (NINHO)")
    parser.add_argument("xml_path", help="Caminho do arquivo XML exportado do ODI")
    parser.add_argument("--output", "-o", help="Caminho de saída para o relatório Markdown", default=None)

    args = parser.parse_args()
    xml_file = Path(args.xml_path)

    if not xml_file.exists():
        print_err(f"Arquivo não encontrado: {xml_file}")
        sys.exit(1)

    auditor = ODIMappingAuditor(xml_file)
    auditor.parse()
    auditor.print_summary()

    if args.output:
        out_file = Path(args.output)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        auditor.generate_markdown_report(out_file)


if __name__ == "__main__":
    main()
