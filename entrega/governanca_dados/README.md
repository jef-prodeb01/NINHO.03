# Insumos para Governança de Dados (`entrega/governanca_dados/`)

Deposite nesta pasta os insumos recebidos do órgão cliente antes de acionar a esteira de governança:

1. **Planilha Padrão PRODEB (`.xlsx`):**
   - Deve conter obrigatoriamente as abas **`Dados - Insumos`** e **`Dicionário de Dados`** 100% preenchidas pelo Data Owner / Data Steward do órgão.
   - Caso o cliente ainda não possua o modelo em branco, envie o arquivo [`modulos/governanca_dados/templates/Template_Insumos_Governanca_Dados.xlsx`](../../modulos/governanca_dados/templates/Template_Insumos_Governanca_Dados.xlsx).
2. **Amostras de Dados (`.csv` ou `.xlsx`):**
   - Arquivos de amostra exportados do sistema de origem (ex.: SAP RH Bahia, Planserv, Detran, BA.GOV.BR).
3. **Políticas ou Decretos Específicos de LGPD / LAI (`.md`, `.pdf`, `.docx`):**
   - Documentos complementares de sigilo ou retenção do órgão.

---

## 🛑 Auditoria Obrigatória de Entrada (Gate 0.5 — Devolução ao Cliente)

Antes de iniciar qualquer modelagem no MongoDB ou publicação no AWS SageMaker Catalog, execute:

```bash
python core/scripts_comuns/inspecionar_insumos_governanca.py
```

> ⚠️ **Regra Inegociável:** A responsabilidade pela veracidade e completude dos dados na origem é exclusiva do cliente. Se o script detectar campos obrigatórios vazios, textos evasivos (*"ver com sap"*, *"a definir"*), ausência de classificação LGPD ou registros em branco/colunas fantasmas (`;;;`) no CSV, **devolva imediatamente o Relatório de Auditoria ao cliente para correção na fonte**.
