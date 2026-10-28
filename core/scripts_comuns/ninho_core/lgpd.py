"""
Proteção de dados pessoais (LGPD): mascaramento de PII e scanner de CPF, CNPJ, e-mail,
telefone e cartão (Luhn) no conteúdo de amostras, textos e documentos.

Extraído de gerador_artefatos_visuais.py (que mantém uma fachada de reimportação).
Usado pelo Gate 0.5 da Governança, mockups e relatórios.
"""

import re
from typing import List


def _validar_luhn(digitos: str) -> bool:
    """Valida número de cartão de crédito pelo algoritmo de Luhn."""
    nums = [int(c) for c in digitos if c.isdigit()]
    if len(nums) < 13 or len(nums) > 19 or len(set(nums)) == 1:
        return False
    soma = 0
    paridade = len(nums) % 2
    for idx, d in enumerate(nums):
        if idx % 2 == paridade:
            d *= 2
            if d > 9:
                d -= 9
        soma += d
    return (soma % 10) == 0


def mascarar_pii_texto(texto: str) -> str:
    """
    Mascara dados pessoais (CPF, CNPJ, E-mail, Telefone BR e Cartão de Crédito)
    em um texto ou célula de amostra, inspirado em `pdfcraft/crates/redact`.
    """
    if not texto:
        return ""
    res = str(texto)
    # CPF formatado: 123.456.789-00 -> ***.456.789-**
    res = re.sub(r"\b(\d{3})\.(\d{3})\.(\d{3})-(\d{2})\b", r"**_.\2.\3-**".replace("_", "*"), res)
    # CNPJ formatado: 12.345.678/0001-99 -> **.345.678/0001-**
    res = re.sub(r"\b(\d{2})\.(\d{3})\.(\d{3})/(\d{4})-(\d{2})\b", r"**.\2.\3/\4-**", res)
    # E-mail: joao.silva@ba.gov.br -> jo***@ba.gov.br
    res = re.sub(
        r"\b([A-Za-z0-9._%+-]{1,2})[A-Za-z0-9._%+-]*@([A-Za-z0-9.-]+\.[A-Za-z]{2,})\b",
        r"\1***@\2",
        res,
    )
    # Telefone BR: (71) 98888-7777 -> (71) *****-7777
    res = re.sub(
        r"(\(?\d{2}\)?\s?)(?:9\d{4}|\d{4})([-\s]\d{4})\b",
        r"\1*****\2",
        res,
    )
    # Cartão de Crédito: 4532 1111 2222 3333 -> **** **** **** 3333
    res = re.sub(
        r"\b(?:\d{4}[-\s]){3}(\d{4})\b",
        r"**** **** **** \1",
        res,
    )
    return res


def escanear_pii_em_texto_ou_linhas(
    dados,
    nome_contexto: str = "",
    max_ocorrencias: int = 25,
) -> List[dict]:
    """
    Inspeciona o conteúdo real das linhas/células ou texto livre em busca de PII
    escondido (CPF, CNPJ, E-mail, Telefone/Celular BR, Cartão de Crédito), mesmo
    quando o nome da coluna parece inócuo (ex: `TXT_OBSERVACAO`, `DES_HISTORICO`).
    Retorna lista de achados com valor mascarado (`***.456.789-**`) e enquadramento LGPD.
    """
    padroes = [
        (
            "CPF",
            re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b"),
            "RESTRITO_LGPD_PII",
            "Art. 5º, I e Art. 7º da LGPD (Lei 13.709/2018) — Identificador Pessoal Direto",
        ),
        (
            "EMAIL",
            re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
            "RESTRITO_LGPD_PII",
            "Art. 5º, I da LGPD — Endereço Eletrônico Pessoal/Funcional",
        ),
        (
            "TELEFONE_BR",
            re.compile(r"(?:\+55\s?)?(?:\(\d{2}\)\s?|\b\d{2}\s)(?:9\d{4}|\d{4})[-\s]\d{4}\b"),
            "RESTRITO_LGPD_PII",
            "Art. 5º, I da LGPD — Telefone / Celular de Contato Individual",
        ),
        (
            "CNPJ",
            re.compile(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b"),
            "INTERNO_GOVERNO",
            "Cadastro Nacional de Pessoa Jurídica (Verificar se MEI / Empresário Individual)",
        ),
        (
            "CARTAO_CREDITO",
            re.compile(r"\b(?:\d{4}[-\s]){3}\d{4}\b"),
            "SENSIVEL_FINANCEIRO",
            "Dado Financeiro / Cartão de Pagamento (PCI-DSS & LGPD)",
        ),
    ]

    achados: List[dict] = []

    def _analisar_celula(valor_str: str, nome_col: str, num_linha: int) -> None:
        if not valor_str or len(achados) >= max_ocorrencias:
            return
        for tipo_pii, rgx, classif, base_legal in padroes:
            m = rgx.search(valor_str)
            if m:
                trecho = m.group(0)
                if tipo_pii == "CARTAO_CREDITO" and not _validar_luhn(trecho):
                    continue
                achados.append({
                    "tipo_pii": tipo_pii,
                    "coluna": nome_col or nome_contexto or "TEXTO_LIVRE",
                    "linha": num_linha,
                    "valor_mascarado": mascarar_pii_texto(trecho),
                    "amostra_mascarada": mascarar_pii_texto(valor_str[:90]),
                    "classificacao_sugerida": classif,
                    "base_legal_sugerida": base_legal,
                })
                if len(achados) >= max_ocorrencias:
                    return

    if isinstance(dados, str):
        for idx_l, ln in enumerate(dados.splitlines(), start=1):
            _analisar_celula(ln, nome_contexto or "DOCUMENTO", idx_l)
    elif isinstance(dados, list) and dados:
        if isinstance(dados[0], dict):
            for idx_l, row_dict in enumerate(dados, start=2):
                for col_k, val_v in row_dict.items():
                    _analisar_celula(str(val_v or ""), str(col_k or ""), idx_l)
        elif isinstance(dados[0], (list, tuple)):
            cabecalho = [str(c).strip() for c in dados[0]]
            for idx_l, row_list in enumerate(dados[1:], start=2):
                for idx_c, val_v in enumerate(row_list):
                    col_k = cabecalho[idx_c] if idx_c < len(cabecalho) and cabecalho[idx_c] else f"COL_{idx_c + 1}"
                    _analisar_celula(str(val_v or ""), col_k, idx_l)

    return achados
