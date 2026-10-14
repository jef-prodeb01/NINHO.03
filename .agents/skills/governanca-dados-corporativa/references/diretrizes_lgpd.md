# Diretrizes Corporativas de Conformidade LGPD, LAI e Responsabilidade na Origem

## 1. Classificação de Dados em 4 Níveis

| Nível | Categoria | Descrição | Exemplos Governamentais | Tratamento Técnico no Transporte (MongoDB ➔ AWS) |
| :---: | :---: | :--- | :--- | :--- |
| **1** | `PÚBLICO` | Dados de transparência ativa que não identificam pessoas físicas. | Nomes e códigos de órgãos, códigos de serviços da carta, estatísticas agregadas. | Livre acesso |
| **2** | `INTERNO` | Dados operacionais corporativos de circulação restrita à administração pública. | Códigos internos de unidades, lotação administrativa, status de etapas de processos sem PII. | Acesso autenticado RBAC |
| **3** | `CONFIDENCIAL` *(Dado Pessoal - Art. 5º, I, LGPD)* | Dado relativo a pessoa física identificada ou identificável. | Nome, Sobrenome, CPF, RG, CNH, Placa/Chassi vinculado a proprietário, E-mail, Telefone, Endereço residencial, Matrícula, Salário/Remuneração individual. | Mascaramento / Pseudonimização (SHA-256) para consumo analítico amplo |
| **4** | `RESTRITO` *(Dado Pessoal Sensível - Art. 5º, II e Art. 11, LGPD)* | Dados sobre origem racial/étnica, convicção religiosa, saúde/deficiência, vida sexual, biometria ou dados de menores/óbitos sob sigilo. | `possuiDeficiencia`, `deficiencia.codigo` (CID), restrições médicas de CNH (`h100t_cdrestr*`), raça/etnia, biometria facial, nome social (quando associado a vulnerabilidade). | Criptografia em repouso + Anonimização obrigatória no transporte analítico + Termo de Compartilhamento (`TC_*`) |

---

## 2. Bases Legais Típicas no Setor Público (LGPD)

Para órgãos estaduais/municipais (como SAEB, DETRAN, PLANSERV, SUPREV, SESAB, SEFAZ), todo campo com `ind_dado_pessoal: true` ou `ind_dado_sensivel: true` em `tb_dataset` deve declarar explicitamente sua base legal:
- **Dados Pessoais (Art. 7º, II e III da LGPD):** *"Cumprimento de obrigação legal ou regulatória pelo controlador"* ou *"Pela administração pública, para o tratamento e uso compartilhado de dados necessários à execução de políticas públicas previstas em leis e regulamentos"*.
- **Dados Pessoais Sensíveis (Art. 11, II, 'a', 'b', 'e', 'g' da LGPD):** *"Execução de políticas públicas"*, *"Tutela da saúde"* (ex: PLANSERV/SESAB) ou *"Garantia da prevenção à fraude e à segurança do titular"* (ex: Biometria BA.GOV.BR / DETRAN).

---

## 3. Regra de Bloqueio e Devolução ao Cliente por Falhas de Preenchimento ou Dados Vazios

> 🛑 **RESPONSABILIDADE INTRANSFERÍVEL DO CLIENTE (ÓRGÃO ORIGEM):**
> A equipe de Engenharia e Governança atua exclusivamente no **transporte para o MongoDB e publicação no Amazon SageMaker Catalog (AWS)**. Não é papel da engenharia corrigir dados vazios nem adivinhar classificações LGPD omitidas pelo cliente.

1. **Colunas sem Classificação na Planilha de Insumos:**
   - Se o cliente enviar a aba `Dicionário de Dados` com células em branco nas colunas `Anonimizar? (S/N)`, `Sensibilidade (Público, Interno, Confidencial)` ou `Sensível? (S/N)` (como visto em casos reais onde colunas de salário ou referência vieram vazias), **bloqueie e devolva a planilha ao cliente** listando exatamente as colunas sem preenchimento.
2. **Incoerências de Classificação LGPD pelo Cliente:**
   - Se o cliente marcar `CPF`, `Nome`, `Endereço`, `Restrição Médica`, `Deficiência` ou `Salário` com classificação incoerente (ex: marcar `Sensibilidade = Público` em um campo de restrição médica ou CPF), aponte a divergência no **Relatório de Devolução / Alinhamento com o Cliente** para retificação formal do *Data Owner*.
3. **Registros com Campos Obrigatórios Vazios nas Amostras/Fontes:**
   - Se os arquivos de dados enviados pelo cliente contiverem registros vazios, chaves nulas ou colunas deslocadas, devolva o lote ao cliente para saneamento no sistema de origem antes do transporte para o MongoDB/AWS.

---

## 4. Padrões de Mascaramento e Pseudonimização (MongoDB / Views / Oracle)

Para colunas com `ind_anonimizar: true`:
- **No Transporte para Consumo Analítico (Hop / ODI / Python ➔ MongoDB / SageMaker):**
  - **Hash Determinístico (Permitindo Join sem revelar identidade):** `SHA-256(num_cpf + SALT_CORPORATIVO)` gravado em `cod_hash_identificador`.
  - **Máscara Parcial de CPF:** `123.***.***-45` (`SUBSTR(CPF, 1, 3) || '.***.***-' || SUBSTR(CPF, 10, 2)`).
  - **Máscara de E-mail:** `jo****@dominio.gov.br`.
  - **Generalização de Endereço:** Manter apenas `des_endereco_bairro`, `des_endereco_cidade`, `sig_uf` e `num_cep` parcial, suprimindo logradouro e complemento em visões analíticas não-nominais.
