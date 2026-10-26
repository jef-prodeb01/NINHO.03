# 🧪 Amostras Pós-Carga (`DIM_*` e `FATO_*`) — Prova Real de Medidas DAX e Mockup BI

Deposite nesta pasta amostras reais ou homologadas da sua carga das tabelas **`DIM_*`** e **`FATO_*`** para testar se os números e as medidas DAX do **Guia do Analista de BI** fazem sentido no **Mockup Visual do Painel**.

## Formatos Suportados (Zero Dependências Externas)

1. **Arquivos `.csv` ou `.tsv` (Separador `;`, `,` ou `\t`):**
   - Nomeie cada arquivo com o nome da tabela (ex: `DIM_UNIDADE.csv`, `DIM_PROGRAMA.csv`, `FATO_ATENDIMENTO.csv`).
2. **Scripts `.sql` com `INSERT INTO`:**
   - Scripts contendo comandos `INSERT INTO [SCHEMA.]DIM_... (...) VALUES (...);` e `INSERT INTO [SCHEMA.]FATO_... (...) VALUES (...);` (podem estar nesta pasta ou junto ao DDL em `entrega/planejador_dw/ddl/`).
3. **Planilhas `.xlsx` ou `.ods` Multi-Abas:**
   - Uma planilha onde cada aba tem o nome da tabela (`DIM_*`, `FATO_*`).
4. **Medidas Customizadas `.dax` ou `.txt` (Opcional):**
   - Caso queira testar medidas DAX adicionais ou alteradas manualmente, coloque um arquivo `.dax` nesta pasta (ou edite diretamente os blocos ` ```dax ` do `GUIA_ANALISTA_BI_<PROJETO>.md`).

## Como Executar a Prova Real + Mockup Populado

No chat da IDE:
```text
/validar-medidas-bi
```
Ou via terminal:
```bash
python ninho.py validar-medidas-bi
```

### O que o Motor Faz Automaticamente
- Cria um Star Schema relacional em memória (`SQLite`) a partir dos seus DDLs de `DIM_*` e `FATO_*` e carrega as amostras pós-carga.
- Avalia todas as medidas DAX do Guia do Analista de BI contra os dados reais da amostra.
- Audita as **6 Heurísticas de Medidas Parcialmente Corretas (`MED-01` a `MED-06`)**:
  - `MED-01`: `SUMMARIZE(FILTER('FATO', FK <> -1), 'DIM'[NK])` sem filtro `NOT(ISBLANK(RELATED('DIM'[NK])))` (evita linha `(Blank)` fantasma em FKs órfãs).
  - `MED-02`: Dupla contagem SCD Tipo 2 (`DISTINCTCOUNT` na `SK` em vez da `NK` quando há histórico).
  - `MED-03`: Medidas de Indicadores/Metas sem `CALCULATE` para filtros obrigatórios ou usando contagem de linhas em vez de soma monetária.
  - `MED-04`: Razão `DIVIDE(Valor, Quantidade)` batizada como `%` (formatação percentual indevida sobre ticket médio).
  - `MED-05`: Soma indevida (`SUM`) sobre coluna de percentual/taxa (`PER_*` / `PRC_*`).
  - `MED-06`: Divisão direta com `/` sem proteção contra divisão por zero (`DIVIDE(..., 0)`).
- Emite o laudo **`saida/planejador_dw/08_datasets_bi/RELATORIO_PROVA_REAL_MEDIDAS.md`** com a expressão DAX corrigida e alimenta os visuais do **`mockup_painel_bi.svg`** e **`preview_painel_bi.html`** com os números reais da sua carga.
