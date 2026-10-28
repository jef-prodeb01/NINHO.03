"""
/estimar-volumetria — calculadora DBA de tamanho de tabelas, índices, crescimento e particionamento.

Estimativa por tipo Oracle (bytes médios por linha), bloco de 8 KB com PCTFREE 10, overhead de linha
e de índices; crescimento composto mensal para 1, 3 e 5 anos. É estimativa de planejamento: os
volumes informados (ou as premissas padrão) aparecem no relatório.
"""

import math
import re
from dataclasses import dataclass
from typing import Dict, List

BLOCO_BYTES = 8192
PCTFREE = 0.10
OVERHEAD_BLOCO = 100
LIMIAR_PARTICIONAMENTO = 20_000_000
LINHAS_PADRAO = {"FATO": 1_000_000, "DIM": 10_000, "STG": 1_000_000, "OUTRA": 100_000}


@dataclass
class EstimativaTabela:
    tabela: str
    categoria: str
    linhas_hoje: int
    bytes_linha: int
    mb_tabela: float
    mb_indices: float
    linhas_5_anos: int
    gb_5_anos: float
    particionar: bool
    premissa_padrao: bool


def bytes_coluna(tipo: str) -> int:
    t = (tipo or "").upper().replace(" ", "")
    m = re.search(r"\((\d+)", t)
    n = int(m.group(1)) if m else None
    if t.startswith(("VARCHAR2", "NVARCHAR2", "VARCHAR")):
        return max(1, int((n or 100) * 0.5)) + 1      # ocupação média de 50% do tamanho declarado
    if t.startswith(("CHAR", "NCHAR")):
        return (n or 1) + 1
    if t.startswith("NUMBER"):
        return (math.ceil((n or 22) / 2) + 1) if n else 8
    if t.startswith("DATE"):
        return 8
    if t.startswith("TIMESTAMP"):
        return 12
    if t.startswith(("CLOB", "BLOB", "NCLOB")):
        return 120                                    # localizador LOB in-line
    return 10


def categoria(nome: str) -> str:
    n = nome.upper()
    for prefixo, cat in (("FATO_", "FATO"), ("FAT_", "FATO"), ("DIM_", "DIM"), ("STG_", "STG"), ("ODI_DIM_", "STG")):
        if n.startswith(prefixo):
            return cat
    return "OUTRA"


def estimar(tabelas: List[dict], linhas: Dict[str, int], crescimento_mensal: float = 0.02) -> List[EstimativaTabela]:
    estimativas = []
    for t in tabelas:
        nome = t["nome_tabela"].upper()
        cat = categoria(nome)
        qtd = linhas.get(nome)
        padrao = qtd is None
        qtd = LINHAS_PADRAO[cat] if padrao else qtd
        bytes_linha = 3 + sum(bytes_coluna(c.get("tipo_oracle", "")) + 1 for c in t["colunas"])
        por_bloco = max(1, int((BLOCO_BYTES * (1 - PCTFREE) - OVERHEAD_BLOCO) // bytes_linha))
        mb = math.ceil(qtd / por_bloco) * BLOCO_BYTES / 1024 ** 2
        fator_indice = 0.35 if cat == "FATO" else 0.20
        crescimento = (1 + crescimento_mensal) ** 60 if cat in ("FATO", "STG") else (1 + crescimento_mensal / 4) ** 60
        linhas_5 = int(qtd * crescimento)
        gb_5 = mb * (1 + fator_indice) * crescimento / 1024
        estimativas.append(EstimativaTabela(
            tabela=nome, categoria=cat, linhas_hoje=qtd, bytes_linha=bytes_linha, mb_tabela=round(mb, 1),
            mb_indices=round(mb * fator_indice, 1), linhas_5_anos=linhas_5, gb_5_anos=round(gb_5, 2),
            particionar=cat == "FATO" and linhas_5 > LIMIAR_PARTICIONAMENTO, premissa_padrao=padrao,
        ))
    return estimativas


def _br(valor: float, casas: int = 0) -> str:
    return f"{valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def relatorio_markdown(est: List[EstimativaTabela], projeto: str, crescimento_mensal: float) -> str:
    total_hoje = sum(e.mb_tabela + e.mb_indices for e in est) / 1024
    total_5 = sum(e.gb_5_anos for e in est)
    linhas = [
        f"# Volumetria e Dimensionamento — {projeto}",
        "",
        f"Estimativa de **{_br(total_hoje, 2)} GB** hoje (dados + índices) e **{_br(total_5, 2)} GB** em 5 anos, "
        f"com crescimento de {_br(crescimento_mensal * 100, 1)}% ao mês nas Fatos/Staging (dimensões a 1/4 desse ritmo). "
        f"Bloco de {BLOCO_BYTES // 1024} KB, PCTFREE {int(PCTFREE * 100)}%.",
        "",
        "| Tabela | Tipo | Linhas hoje | Bytes/linha | Tabela (MB) | Índices (MB) | Linhas em 5 anos | Total em 5 anos (GB) | Particionar? |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | :---: |",
    ]
    for e in sorted(est, key=lambda x: -x.gb_5_anos):
        marca = "*" if e.premissa_padrao else ""
        linhas.append(
            f"| `{e.tabela}` | {e.categoria} | {_br(e.linhas_hoje)}{marca} | {e.bytes_linha} | {_br(e.mb_tabela, 1)} | {_br(e.mb_indices, 1)} | "
            f"{_br(e.linhas_5_anos)} | {_br(e.gb_5_anos, 2)} | {'**Sim**' if e.particionar else 'Não'} |"
        )
    linhas += ["", "\\* volume padrão (premissa). Informe o real com `--linhas TABELA=N`.", ""]
    candidatas = [e.tabela for e in est if e.particionar]
    if candidatas:
        linhas.append(
            f"**Particionamento recomendado** (acima de {_br(LIMIAR_PARTICIONAMENTO)} linhas em 5 anos): {', '.join(candidatas)}. "
            "Use o bloco comentado `PARTITION BY RANGE ... INTERVAL` gerado em `04_create_fato_tables.sql`."
        )
    return "\n".join(linhas) + "\n"


def script_tablespaces(est: List[EstimativaTabela], ts_dados: str, ts_indices: str) -> str:
    dados_5 = sum(e.gb_5_anos / (1 + (0.35 if e.categoria == "FATO" else 0.20)) for e in est)
    indices_5 = sum(e.gb_5_anos for e in est) - dados_5
    inicial_d = max(1, math.ceil(sum(e.mb_tabela for e in est) * 1.3 / 1024))
    inicial_i = max(1, math.ceil(sum(e.mb_indices for e in est) * 1.3 / 1024))
    return (
        "-- NINHO — dimensionamento de tablespaces (estimativa /estimar-volumetria; ajuste com o DBA)\n"
        f"-- Projeção 5 anos: dados ~{dados_5:.1f} GB | índices ~{indices_5:.1f} GB\n"
        f"CREATE TABLESPACE {ts_dados} DATAFILE '{ts_dados.lower()}01.dbf' SIZE {inicial_d}G AUTOEXTEND ON NEXT 1G MAXSIZE {max(inicial_d, math.ceil(dados_5 * 1.2))}G;\n"
        f"CREATE TABLESPACE {ts_indices} DATAFILE '{ts_indices.lower()}01.dbf' SIZE {inicial_i}G AUTOEXTEND ON NEXT 512M MAXSIZE {max(inicial_i, math.ceil(indices_5 * 1.2))}G;\n"
    )
