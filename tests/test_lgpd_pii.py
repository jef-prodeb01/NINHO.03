"""Testes do mascaramento de dados pessoais (LGPD) usado em amostras, mockups e relatórios."""

from ninho_core.lgpd import escanear_pii_em_texto_ou_linhas, mascarar_pii_texto


def test_scanner_encontra_cpf_em_coluna_inocente():
    achados = escanear_pii_em_texto_ou_linhas([["TXT_OBSERVACAO"], ["cliente 123.456.789-00 ligou"]])
    assert achados and achados[0]["tipo_pii"] == "CPF" and achados[0]["coluna"] == "TXT_OBSERVACAO"
    assert "123.456.789-00" not in achados[0]["valor_mascarado"]


def test_cpf_formatado_e_mascarado():
    resultado = mascarar_pii_texto("Titular 123.456.789-00")
    assert "123.456.789-00" not in resultado
    assert "456.789" in resultado


def test_cnpj_formatado_e_mascarado():
    resultado = mascarar_pii_texto("Fornecedor 12.345.678/0001-99")
    assert "12.345.678/0001-99" not in resultado


def test_email_e_mascarado_preservando_dominio():
    resultado = mascarar_pii_texto("contato: joao.silva@ba.gov.br")
    assert "joao.silva@" not in resultado
    assert "@ba.gov.br" in resultado


def test_texto_sem_pii_fica_intacto():
    assert mascarar_pii_texto("Secretaria da Fazenda") == "Secretaria da Fazenda"
    assert mascarar_pii_texto("") == ""
