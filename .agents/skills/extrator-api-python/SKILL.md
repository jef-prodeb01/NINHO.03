---
name: extrator-api-python
description: >-
  Gera extratores e pré-processadores em Python para ingestão de APIs REST (OAuth2 client_credentials,
  Bearer token, paginação, consolidação multi-endpoint em memória, escrita atômica .tmp) e higienização
  determinística de arquivos CSV/Excel com quarentena de rejeitados, integrados ao Oracle ou ao Apache Hop.
  Use quando a opção Extratores Python estiver marcada no INTAKE_DW.md.
---

# Skill: Extrator de APIs REST & Pré-Processador Determinístico em Python

Esta skill orienta a geração de scripts Python de nível corporativo para **duas modalidades de engenharia de ingestão**:
1. **Modalidade A — Extrator Direto API REST $\rightarrow$ Oracle Staging (`oracledb` Bulk Insert)**
2. **Modalidade B — Extrator/Higienizador Híbrido Python + Apache Hop (Padrão `COST_MGMT` e `Indicadores_servico`)**

> 🛑 **REGRA DE ATIVAÇÃO CONDICIONAL:**  
> Esta skill **NUNCA** deve gerar arquivos se o Engenheiro de Dados não tiver marcado `[x] Extratores Python / Ingestão de APIs` na Seção 1 do `INTAKE_DW.md`.  
> Se desmarcado, a pasta `saida/planejador_dw/07_extratores_python/` DEVE permanecer intacta contendo apenas seu `.gitkeep`.

---

## 🏗️ 1. Padrões de Engenharia Obrigatórios

Ao ser acionada, os scripts gerados devem ser salvos diretamente em:
`saida/planejador_dw/07_extratores_python/`

### 1.1 Requisitos para Consumo de APIs REST (Modalidades A e B)
1. **Autenticação OAuth2 (`client_credentials`) ou Bearer Token:**
   - Suporte a geração dinâmica de token via `POST` (`grant_type=client_credentials`, `client_id`, `client_secret`) ou header `Authorization: Bearer <token>`.
   - Credenciais recebidas via `os.getenv()` ou argumentos CLI `--api-user` / `--api-pass` injetados pelo **Hop Variable Resolver (`#{hop-pwd:ENV_API_PASS}`)** — **NUNCA hardcoded** (`HOP-H1`).
2. **Resiliência HTTP e Paginação Segura:**
   - Usar `requests.Session()` com `urllib3.util.Retry` (`total=5`, `backoff_factor=1`, `status_forcelist=[429, 500, 502, 503, 504]`).
   - Paginar por `limit`/`offset` ou `links.next`, com guarda de segurança (`MAX_PAGINATION_PAGES = 1000`) contra loops infinitos.
3. **Enriquecimento Multi-Endpoint em Memória (Padrão `COST_MGMT`):**
   - Quando uma tabela Staging consolida métricas de múltiplos endpoints (ex: `costs`, `compute`, `memory`, `volumes`), indexar os dados em memória por chave composta normalizada (ex: `(usage_date, cluster_uuid, project)`) antes da persistência.
4. **Escrita Atômica via Arquivo `.tmp` + Contrato de Saída para o Hop:**
   - Ao gerar CSV para consumo subsequente pelo Apache Hop, gravar primeiro em `<arquivo>.csv.tmp` e ao final executar `temp_path.replace(output_path)`. Isso garante que o Hop nunca leia um arquivo parcial ou corrompido em caso de queda de rede.
   - Emitir no `stdout` a linha de protocolo estruturada:
     `STATUS:SUCCESS|rows=<N>|output=<caminho>` (ou `STATUS:ERROR|reason=<msg>` com `sys.exit(1)`).

### 1.2 Requisitos para Higienização e Deduplicação de Arquivos em Python (Padrão `Indicadores_servico`)
Quando os arquivos brutos vindos de FTP possuem problemas severos de codificação, cabeçalhos sujos ou duplicatas:
1. **Sanitização de Encoding e Cabeçalhos:**
   - Tentar leitura resiliente (`utf-8-sig` para remover BOM `\ufeff`, com fallback automático para `cp1252`/`latin-1`).
   - Normalizar nomes de colunas (`strip()`, remoção de aspas e caracteres invisíveis) e validar contra o contrato de colunas esperadas (`colunas_obrigatorias`).
2. **Deduplicação Determinística e Normalização Numérica/Data:**
   - Converter números no formato brasileiro (`1.234,56` $\rightarrow$ `1234.56`) e testar múltiplos formatos de data (`%d/%m/%Y %H:%M:%S`, `%Y-%m-%d %H:%M:%S`, `%d/%m/%Y`).
   - Deduplicar registros pela chave natural (ex: `ID_CHAMADO`) mantendo sempre o registro com maior data de atualização/fechamento (`DATA_FECHAMENTO`).
3. **Segregação de Quarentena (`_TRATADO.csv` vs `_REJEITADOS.csv`):**
   - Arquivos aprovados geram `<INDICADOR>_TRATADO.csv` para carga no Hop (`CSVInput` $\rightarrow$ `SelectValues` $\rightarrow$ `InsertUpdate`).
   - Arquivos com quebra de contrato geram `<INDICADOR>_REJEITADOS.csv` detalhando `ARQUIVO | STATUS | MOTIVO_REJEICAO` e encerram com `sys.exit(1)` para acionar a trilha de erro do workflow Hop.

---

## 📂 2. Template Base

### 1.3 Requisitos para Extrator Python v2.1 com Janela Móvel e Auto-Controle de Carga Inicial (Padrão `COPSD` / `GLPI`)
Quando o extrator Python alimenta a camada Staging para fatos mensais/periódicas com reprocessamento retroativo:
1. **3 Modos de Operação (`MODO_CARGA`: `AUTO`, `INICIAL`, `DIARIO`):**
   - `INICIAL`: extrai a série histórica desde `DATA_INICIO_HISTORICO` e cria o marcador de estado `.carga_inicial_concluida` ao concluir com sucesso.
   - `DIARIO`: extrai os últimos `MESES_RETROATIVOS + 1` meses fechados mais o mês vigente (`M-3 .. M_vigente`) para capturar reclassificações tardias.
   - `AUTO` (padrão): verifica a existência de `.carga_inicial_concluida`; se ausente, roda `INICIAL`, caso contrário roda `DIARIO`.
2. **Decodificador Nativo de Senha do Apache Hop (`Encrypted <hex>`):**
   - Incluir função `decrypt_hop_password(val)` compatível com o algoritmo XOR/BigInteger do Hop (`SEED = 0x0933910847463829827159347601486730416058`) para aceitar variáveis `Encrypted 2be98...` diretamente do `config_env.json`.
3. **Filtro Determinístico por Lista de Entidades Alvo e Escrita Atômica UTF-8-SIG (`;`):**
   - Filtrar registros pela lista de unidades/grupos alvo normalizada (`unicodedata.normalize('NFKD')`) e gravar CSV com separador `;`, encoding `utf-8-sig` via arquivo temporário `.tmp` + `os.replace()`.

## 📂 2. Template Base

Consulte o modelo de referência em [template_extrator_api.py](./templates/template_extrator_api.py).
