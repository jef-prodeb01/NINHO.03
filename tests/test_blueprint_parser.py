"""Parser reverso da Blueprint: tolerante a edições manuais e nunca descarta linhas em silêncio."""

from simular_projeto import celulas_linha_tabela, linha_marcada_blueprint


def test_crases_sao_opcionais():
    com = celulas_linha_tabela("| [x] | `ID` | `NUM_ID` | `NUMBER(10)` | `NK` | `-` | Comentário |")
    sem = celulas_linha_tabela("| [x] | ID | NUM_ID | NUMBER(10) | NK | - | Comentário |")
    assert com == sem == ["[x]", "ID", "NUM_ID", "NUMBER(10)", "NK", "-", "Comentário"]


def test_pipe_dentro_de_codigo_sql_e_preservado():
    celulas = celulas_linha_tabela("| [x] | `COD` | Nome | `A || ' - ' || B` | `VW` | `TEXTO` |")
    assert celulas[3] == "A || ' - ' || B"
    assert len(celulas) == 6


def test_pipe_no_comentario_final_nao_descarta_linha():
    lida = linha_marcada_blueprint("| [x] | `ID` | `NUM_ID` | `NUMBER` | `NK` | `-` | Código | chave natural |", 7, "teste")
    assert lida is not None and lida[1][-1] == "Código | chave natural"


def test_linha_incompleta_gera_aviso(capsys):
    assert linha_marcada_blueprint("| [x] | `ID` | `NUM_ID` |", 7, "Colunas de DIM_X") is None
    assert "linha ignorada" in capsys.readouterr().out


def test_linha_desmarcada_e_lida_como_inativa():
    ativo, celulas = linha_marcada_blueprint("| [ ] | A | B | C | D | E |", 6, "teste")
    assert ativo is False and celulas == ["A", "B", "C", "D", "E"]
