# Resumo Executivo: Engenharia Reversa de Regras Visuais do Power BI

> **Arquivo de Origem:** `{NOME_ARQUIVO_PBIX}`  
> **Data da Extração:** {DATA}  
> **Projeto:** {NOME_PROJETO}  

---

## 1. 🏗️ Visão Geral da Estrutura do Relatório

- **Tabelas Originais Identificadas:**
  - `{TABELA_DESNORMALIZADA_ORIGINAL}`: Tabela plana contendo todos os eventos, atributos e descrições.
- **Páginas / Abas do Relatório:**
  - Página 1: `{NOME_PAGINA_1}`
  - Página 2: `{NOME_PAGINA_2}`

---

## 2. 🔑 Regras de Negócio e Filtros Implícitos Mapeados

| Indicador no Dashboard | Filtro DAX / Visual Identificado | Regra de Negócio Correspondente | Destino no DW (Dimensão/Fato) |
| :--- | :--- | :--- | :--- |
| **Exemplo: Processos Criados** | `id_tarefa = 1` | Evento de criação do processo | `DIM_TAREFA` ou Flag na `FATO_ANDAMENTO` |
| **Exemplo: Finalizados** | `status_codigo IN ('CONC', 'FIM')` | Processos concluídos | `DIM_STATUS` |

---

## 3. 📄 Inventário de Visuais por Página

### Página: {NOME_PAGINA_1}
- **Filtros de Nível de Página:** `{CAMPO} = '{VALOR}'`
- **Segmentações de Dados (Slicers):** `{CAMPO_ANO}`, `{CAMPO_MES}`, `{CAMPO_UNIDADE}`

#### Visuais Principais:
1. **Cartão: {TITULO_CARTAO}**
   - *Métrica:* `{MEDIDA_DAX_OU_CAMPO}`
   - *Filtros Locais:* `{FILTRO_APLICADO}`
2. **Gráfico: {TITULO_GRAFICO}**
   - *Tipo:* `{TIPO_VISUAL}` (ex: clusteredColumnChart)
   - *Eixo / Categoria:* `{CAMPO_EIXO}`
   - *Valores:* `{CAMPO_VALOR_OU_AGREGACAO}`

