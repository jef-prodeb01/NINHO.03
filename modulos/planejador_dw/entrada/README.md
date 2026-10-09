# Diretório de Insumos de Entrada (Entrada do Planejador de DW)

Este diretório é o ponto de contato do **Engenheiro de Dados** para fornecer os insumos brutos do projeto que será planejado e modelado pelo **Planejador de DW**.  
*(Nota: Você pode depositar seus arquivos aqui ou na pasta central da plataforma em [`entrega/planejador_dw/`](../../../entrega/planejador_dw/)).*

---

## 📂 Estrutura de Pastas

| Subpasta | Conteúdo Esperado | Formatos Aceitos | Objetivo para a IA |
| :--- | :--- | :--- | :--- |
| `ddl/` | Scripts DDL das tabelas das fontes relacionais (OLTP). | `.sql`, `.txt` | Analisar tipos de dados, chaves primárias, índices e relacionamentos originais. |
| `amostras/` | Amostras representativas de dados reais (10 a 50 linhas). | `.csv`, `.tsv`, `.sql`, `.json` | Entender a cardinalidade, padrões de preenchimento, formatos de datas e valores nulos. |
| `arquivos_ftp/` | Arquivos brutos recebidos via FTP, SFTP ou compartilhamento de rede. | `.csv`, `.xlsx`, `.xls`, `.txt` | Projetar pipelines do **Apache Hop** (`.hpl`) e tabelas de staging correspondentes. |
| `api_specs/` | Especificações OpenAPI/Swagger ou exemplos reais de payload JSON de APIs REST. | `.json`, `.yaml`, `.yml` | Projetar extratores **Python** com paginação, flatten de estruturas aninhadas e carga. |

---

## 🚀 Como Iniciar um Novo Projeto

1. Preencha o arquivo [`INTAKE_DW.md`](../INTAKE_DW.md) na raiz do módulo `modulos/planejador_dw/`.
2. Deposite os arquivos técnicos nas subpastas apropriadas acima.
3. Invoque o agente de planejamento de DW ou use a biblioteca de prompts disponível em [`documentacao/guias/GUIA_ENGENHEIRO_DW.md`](../../../documentacao/guias/GUIA_ENGENHEIRO_DW.md).
4. O agente analisará os insumos, formulará o Documento de Entendimento Dimensional e, após sua aprovação, gerará os entregáveis em `saida/planejador_dw/<NOME_PROJETO>/`.

