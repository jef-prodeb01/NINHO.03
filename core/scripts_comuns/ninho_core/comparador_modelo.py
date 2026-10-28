"""
/comparar-modelo — diff entre o DW em produção e o modelo novo, gerando ALTERs incrementais.

Regras de segurança (DW vivo):
  - colunas/tabelas novas e alargamento de tipo saem como comandos ativos;
  - estreitamento de tipo, troca de tipo e remoções saem COMENTADOS (exigem análise do DBA);
  - coluna nova NOT NULL entra como NULL + backfill + MODIFY NOT NULL (evita ORA-01758).
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class Diferencas:
    tabelas_novas: List[str] = field(default_factory=list)
    tabelas_removidas: List[str] = field(default_factory=list)
    colunas_novas: List[Tuple[str, str]] = field(default_factory=list)
    colunas_removidas: List[Tuple[str, str]] = field(default_factory=list)
    tipos_alterados: List[Tuple[str, str, str, str, bool]] = field(default_factory=list)  # tab, col, de, para, seguro

    @property
    def vazio(self) -> bool:
        return not any((self.tabelas_novas, self.tabelas_removidas, self.colunas_novas, self.colunas_removidas, self.tipos_alterados))


def _norm_tipo(tipo: str) -> str:
    t = re.sub(r"\s+", "", (tipo or "").upper())
    t = re.sub(r"(\d+)(BYTE|CHAR)\)", r"\1)", t)
    t = re.sub(r"(NOTNULL|NULL|DEFAULT.*)$", "", t)
    return t.replace("NUMBER(38,0)", "NUMBER(38)").replace("INTEGER", "NUMBER(38)")


def _dimensoes(tipo: str) -> Tuple[str, Optional[int], Optional[int]]:
    m = re.match(r"([A-Z0-9]+)(?:\((\d+)(?:,(\d+))?\))?", tipo)
    if not m:
        return tipo, None, None
    return m.group(1), int(m.group(2)) if m.group(2) else None, int(m.group(3)) if m.group(3) else None


def alargamento_seguro(de: str, para: str) -> bool:
    """True quando a mudança só amplia o tipo (VARCHAR2 maior, NUMBER com mais dígitos e mesma escala)."""
    b1, p1, s1 = _dimensoes(de)
    b2, p2, s2 = _dimensoes(para)
    if b1 != b2:
        return False
    if b1 in ("VARCHAR2", "NVARCHAR2", "CHAR", "RAW"):
        return p1 is not None and p2 is not None and p2 >= p1
    if b1 == "NUMBER":
        if p2 is None:
            return True
        return p1 is not None and (s1 or 0) == (s2 or 0) and p2 >= p1
    return False


def _por_nome(tabelas: list) -> dict:
    return {t["nome_tabela"].upper(): {c["nome_dw"].upper(): c for c in t["colunas"]} for t in tabelas}


def comparar(atual: list, novo: list) -> Diferencas:
    a, n = _por_nome(atual), _por_nome(novo)
    dif = Diferencas()
    dif.tabelas_novas = sorted(set(n) - set(a))
    dif.tabelas_removidas = sorted(set(a) - set(n))
    for tab in sorted(set(a) & set(n)):
        for col in n[tab]:
            if col not in a[tab]:
                dif.colunas_novas.append((tab, col))
            else:
                de, para = _norm_tipo(a[tab][col].get("tipo_oracle", "")), _norm_tipo(n[tab][col].get("tipo_oracle", ""))
                if de and para and de != para:
                    dif.tipos_alterados.append((tab, col, de, para, alargamento_seguro(de, para)))
        dif.colunas_removidas.extend((tab, col) for col in a[tab] if col not in n[tab])
    return dif


def _obrigatoria(col: dict) -> bool:
    return col.get("obrigatorio") in (True, "NOT NULL") or "NOT NULL" in str(col.get("tipo_oracle", "")).upper()


def gerar_script_alter(dif: Diferencas, novo: list, schema: str) -> str:
    cols_novo = _por_nome(novo)
    tipo_de = {t["nome_tabela"].upper(): t for t in novo}
    linhas = [
        "-- =============================================================================",
        f"-- NINHO — ALTERs incrementais (DW em produção -> modelo novo) | SCHEMA: {schema}",
        f"-- Tabelas novas: {len(dif.tabelas_novas)} | Colunas novas: {len(dif.colunas_novas)} | "
        f"Tipos alterados: {len(dif.tipos_alterados)} | Remoções (comentadas): {len(dif.colunas_removidas) + len(dif.tabelas_removidas)}",
        "-- Revise antes de executar. Remoções e estreitamentos NUNCA são automáticos.",
        "-- =============================================================================",
        "",
    ]
    if dif.vazio:
        linhas.append("-- Nenhuma diferença estrutural encontrada.")
        return "\n".join(linhas) + "\n"
    for tab in dif.tabelas_novas:
        cols = tipo_de[tab]["colunas"]
        linhas.append(f"-- [NOVA TABELA] {tab}")
        linhas.append(f"CREATE TABLE {schema}.{tab} (")
        linhas.extend(
            f"    {c['nome_dw']} {_norm_tipo(c.get('tipo_oracle', ''))}{' NOT NULL' if _obrigatoria(c) else ''}{',' if i < len(cols) - 1 else ''}"
            for i, c in enumerate(cols)
        )
        linhas.extend([");", ""])
    for tab, col in dif.colunas_novas:
        c = cols_novo[tab][col]
        tipo = _norm_tipo(c.get("tipo_oracle", ""))
        linhas.append(f"ALTER TABLE {schema}.{tab} ADD ({col} {tipo});")
        if _obrigatoria(c):
            linhas.append(f"-- {col} é NOT NULL no modelo novo: preencha as linhas existentes e só então aplique:")
            linhas.append(f"-- UPDATE {schema}.{tab} SET {col} = <valor_padrao> WHERE {col} IS NULL;")
            linhas.append(f"-- ALTER TABLE {schema}.{tab} MODIFY ({col} NOT NULL);")
    if dif.colunas_novas:
        linhas.append("")
    for tab, col, de, para, seguro in dif.tipos_alterados:
        if seguro:
            linhas.append(f"ALTER TABLE {schema}.{tab} MODIFY ({col} {para});  -- alargamento: {de} -> {para}")
        else:
            linhas.append(f"-- [REVISAR] {tab}.{col}: {de} -> {para} reduz ou troca o tipo (risco ORA-01441/ORA-01439 e perda de dados).")
            linhas.append(f"-- ALTER TABLE {schema}.{tab} MODIFY ({col} {para});")
    if dif.tipos_alterados:
        linhas.append("")
    for tab, col in dif.colunas_removidas:
        linhas.append(f"-- [REMOÇÃO — avaliar impacto em views/ODI/BI] ALTER TABLE {schema}.{tab} SET UNUSED ({col});")
    for tab in dif.tabelas_removidas:
        linhas.append(f"-- [TABELA AUSENTE NO MODELO NOVO — avaliar] DROP TABLE {schema}.{tab} PURGE;")
    return "\n".join(linhas) + "\n"
