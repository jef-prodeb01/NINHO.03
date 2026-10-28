"""Testes da esteira de Governança: Gate 0.5, classificação LGPD e geração MongoDB/AWS."""

import json

import pytest

import gerar_artefatos_governanca as esteira
import inspecionar_insumos_governanca as gate

openpyxl = pytest.importorskip("openpyxl")

INTAKE_COMPLETO = """
- **Sigla do Órgão / Cliente (`SIGLA_ORGAO`):** `SAEB`
- **Unidade / Coordenação / Sistema (`UNIDADE`):** `RH`
- **Tema de Negócio (`TEMA`):** `SERVIDOR`
- **Versão do Esquema (`VERSAO`):** `V1`
- **Código Canônico do Dataset (`SIGLA_ORGAO_UNIDADE_TEMA_VERSAO`):** `SAEB_RH_SERVIDOR_V1`
- **Data Owner (Gestor de Negócio no Órgão):** `Maria Souza — Diretora de RH`
- **Data Steward (Responsável Técnico na Origem):** `Carlos Lima`
- [x] **MongoDB Lakehouse & Camada Semântica:**
- [x] **Amazon SageMaker Unified Studio / SageMaker Catalog (ex-DataZone) & AWS Glue Data Catalog:**
- [x] **Apache Hop (.hpl / .hwf):** Transporte de arquivos.
"""

DICIONARIO = [
    ("Nome do Campo", "Descrição", "Tipo", "Anonimizar?", "Sensibilidade", "Sensível?", "Obrigatório?", "Chave?"),
    ("MATRICULA", "Matrícula funcional do servidor", "NUMBER(10)", "N", "Confidencial", "S", "S", "S"),
    ("CPF", "CPF do servidor", "VARCHAR2(11)", "S", "Confidencial", "S", "S", "N"),
    ("VAL_SALARIO", "Salário bruto mensal", "NUMBER(18,2)", "S", "Confidencial", "S", "N", "N"),
    ("COD_UNIDADE", "Código da unidade de lotação", "NUMBER(6)", "N", "Interno", "N", "N", "N"),
]

AMOSTRA_OK = "MATRICULA;CPF;VAL_SALARIO;COD_UNIDADE\n1001;12345678901;5500.00;10\n1002;98765432100;6100.50;11\n"


def _planilha(caminho, dicionario=DICIONARIO):
    wb = openpyxl.Workbook()
    ins = wb.active
    ins.title = "Dados - Insumos"
    for linha in (
        ("Objeto", "Descrição"),
        ("Nome da base / sistema de origem", "SIGRH"),
        ("Tipo de origem (ex: banco, API, File System)", "Banco de dados Oracle"),
        ("Nome da tabela ou dataset", "TB_SERVIDOR"),
        ("Criticidade dos dados (alta, média, baixa)", "Alta"),
        ("Frequência esperada de atualização", "Diária"),
    ):
        ins.append(linha)
    dic = wb.create_sheet("Dicionário de Dados")
    for linha in dicionario:
        dic.append(linha)
    wb.save(caminho)


@pytest.fixture
def projeto(tmp_path):
    insumos = tmp_path / "insumos"
    insumos.mkdir()
    _planilha(insumos / "insumos.xlsx")
    (insumos / "amostra.csv").write_text(AMOSTRA_OK, encoding="utf-8")
    intake = tmp_path / "INTAKE_GOVERNANCA.md"
    intake.write_text(INTAKE_COMPLETO, encoding="utf-8")
    return insumos, intake, tmp_path / "saida"


@pytest.mark.parametrize(
    "campo,tipo,esperado",
    [
        ("CPF", "NUMBER(11)", ("num_cpf", "string")),
        ("MATRICULA", "NUMBER(10)", ("num_matricula", "string")),
        ("ID_SERVIDOR", "NUMBER(12)", ("ide_servidor", "string")),
        ("VAL_SALARIO", "NUMBER(18,2)", ("val_salario", "decimal")),
        ("QTD_DEPENDENTES", "NUMBER(12)", ("qtd_dependentes", "long")),
        ("DATA_NASCIMENTO", "DATE", ("dtc_nascimento", "date")),
    ],
)
def test_nomenclatura_e_tipo_bson_seguem_padrao_prodeb(campo, tipo, esperado):
    assert gate.inferir_prefixo_e_nome_mongo(campo, "", tipo) == esperado


def test_classificacao_lgpd_em_4_niveis():
    assert gate.classificar_campo_lgpd({"campo_origem": "COD_CID", "descricao": "CID da doença"})["des_nivel_sensibilidade"] == "RESTRITO"
    assert gate.classificar_campo_lgpd({"campo_origem": "CPF"})["des_nivel_sensibilidade"] == "CONFIDENCIAL"
    assert gate.classificar_campo_lgpd({"campo_origem": "COD_UNIDADE"})["des_nivel_sensibilidade"] == "INTERNO"
    publico = gate.classificar_campo_lgpd({"campo_origem": "SIG_ORGAO", "sensibilidade_cliente": "Público"})
    assert publico["des_nivel_sensibilidade"] == "PUBLICO"


def test_cliente_nao_rebaixa_campo_pessoal():
    classif = gate.classificar_campo_lgpd({"campo_origem": "CPF", "sensivel_cliente": "N", "sensibilidade_cliente": "Público"})
    assert classif["des_nivel_sensibilidade"] == "CONFIDENCIAL"
    assert classif["divergente_do_cliente"] is True


def test_leitor_xlsx_sem_openpyxl_preserva_posicao_das_celulas(tmp_path):
    arq = tmp_path / "p.xlsx"
    wb = openpyxl.Workbook()
    wb.active.title = "Dicionário de Dados"
    wb.active["A1"], wb.active["C1"], wb.active["B3"] = "CAMPO", "TIPO", 42
    wb.save(arq)
    aba = gate._carregar_xlsx_sem_openpyxl(arq)["Dicionário de Dados"]
    assert aba.cell(1, 1).value == "CAMPO"
    assert aba.cell(1, 2).value is None
    assert aba.cell(1, 3).value == "TIPO"
    assert aba.cell(3, 2).value == "42"


def test_esteira_completa_gera_mongo_e_aws(projeto):
    insumos, intake, saida = projeto
    resultado = esteira.executar(insumos, intake, saida)
    assert resultado["status"] == "GERADO", resultado

    mongo = saida / "schemas_mongo"
    for nome in ("01_schema_tb_dataset.js", "04_schema_tb_auditoria_eventos.js",
                 "05_regras_barreira_quarentena_saeb_rh_servidor_v1.js",
                 "06_documento_tb_dataset_saeb_rh_servidor_v1.js", "07_colecao_trusted_saeb_rh_servidor_v1.js",
                 "08_evento_auditoria_saeb_rh_servidor_v1.js"):
        assert (mongo / nome).exists(), nome

    trusted = (mongo / "07_colecao_trusted_saeb_rh_servidor_v1.js").read_text(encoding="utf-8")
    assert '"additionalProperties": false' in trusted
    assert "uk_trusted_saeb_rh_servidor_v1_chave_negocio" in trusted
    assert "pseudonimizado" in trusted  # CPF e salário marcados para anonimizar

    documento = (mongo / "06_documento_tb_dataset_saeb_rh_servidor_v1.js").read_text(encoding="utf-8")
    assert '"des_criticidade": "ALTA"' in documento
    assert '"tip_fonte": "BANCO_DADOS"' in documento
    assert '"des_ferramenta_transporte": "APACHE_HOP"' in documento

    tabela = json.loads((saida / "aws_sagemaker_catalog" / "glue_table_saeb_rh_servidor_v1.json").read_text(encoding="utf-8"))
    tipos = {c["Name"]: c["Type"] for c in tabela["TableInput"]["StorageDescriptor"]["Columns"]}
    assert tipos["val_salario"] == "decimal(18,2)"
    assert "finalidade do dataset" in resultado["pendencias"]

    relatorio = (saida / "relatorio_governanca_saeb_rh_servidor_v1.md").read_text(encoding="utf-8")
    assert "`CNC_SERVIDOR_PUBLICO`" in relatorio and "`CNC_CIDADAO`" in relatorio


def test_coluna_nao_documentada_devolve_ao_cliente(projeto):
    insumos, intake, saida = projeto
    (insumos / "amostra.csv").write_text(AMOSTRA_OK.replace("COD_UNIDADE", "COLUNA_NOVA"), encoding="utf-8")
    resultado = esteira.executar(insumos, intake, saida)
    assert resultado["status"] == "DEVOLVIDO_AO_CLIENTE"
    relatorio = (saida / "relatorio_devolucao_cliente_SAEB.md").read_text(encoding="utf-8")
    assert "COLUNA_NOVA" in relatorio and "não está catalogada" in relatorio
    assert not (saida / "schemas_mongo").exists()


def test_pii_em_coluna_declarada_nao_sensivel_bloqueia(projeto):
    insumos, intake, saida = projeto
    dicionario = list(DICIONARIO)
    dicionario[4] = ("COD_UNIDADE", "Código da unidade", "VARCHAR2(20)", "N", "Interno", "N", "N", "N")
    _planilha(insumos / "insumos.xlsx", dicionario)
    (insumos / "amostra.csv").write_text(
        "MATRICULA;CPF;VAL_SALARIO;COD_UNIDADE\n1001;12345678901;5500.00;123.456.789-00\n", encoding="utf-8"
    )
    resultado = esteira.executar(insumos, intake, saida)
    assert resultado["status"] == "DEVOLVIDO_AO_CLIENTE"
    assert "retificar" in (saida / "relatorio_devolucao_cliente_SAEB.md").read_text(encoding="utf-8")


def test_intake_sem_codigo_gera_so_matriz_e_relatorio(projeto):
    insumos, intake, saida = projeto
    intake.write_text("- [x] **MongoDB Lakehouse:**\n", encoding="utf-8")
    resultado = esteira.executar(insumos, intake, saida)
    assert resultado["status"] == "GATE_0_PENDENTE" and resultado["codigo_saida"] == 2
    assert (saida / "matriz_de_para_lgpd_sem_codigo.csv").exists()
    assert not (saida / "schemas_mongo").exists()
