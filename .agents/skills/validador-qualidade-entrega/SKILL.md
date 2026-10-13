---
name: validador-qualidade-entrega
description: >-
  Executa a auditoria e validação de prontidão de insumos (pré-voo) e testes de integridade
  dos artefatos de DW, Semântica e Governança usando os scripts automatizados.
---

# Skill: Validador de Qualidade da Entrega

Esta skill guia o uso das ferramentas automatizadas de validação de insumos (*Pre-flight Check*), testes de integridade em banco e handoff contínuo entre etapas.

## 1. Verificador Pré-Voo Automatizado (`validar_entrega.py`)

Antes de iniciar qualquer planejamento ou geração com a IA, o engenheiro ou a própria IA deve executar o validador para auditar a completude dos formulários e integridade dos DDLs:

```bash
# Validar apenas o módulo de DW
python core/scripts_comuns/validar_entrega.py dw

# Validar a Camada Semântica
python core/scripts_comuns/validar_entrega.py semantica

# Validar Governança de Dados
python core/scripts_comuns/validar_entrega.py governanca

# Validar todos os módulos simultaneamente
python core/scripts_comuns/validar_entrega.py all
```

### Critérios Auditados:
- **Campos Obrigatórios:** Nome do projeto, schema alvo e tablespaces.
- **Pilha Tecnológica:** Seção 1 preenchida com as tecnologias de esteira.
- **Detecção de Documentação de Entrega:** Se perguntas e regras foram depositadas em arquivos na pasta `entrega/<modulo>/`, o validador aceita e aprova.
- **Conformidade de DDL:** Alerta sobre identificadores minúsculos ou com aspas antes de rodar no Oracle.

---

## 2. Transição Contínua DW -> Semântica (`transicionar_dw_para_semantica.py`)

Ao concluir a geração do DW no Oracle, execute o script de transição automática:

```bash
python core/scripts_comuns/transicionar_dw_para_semantica.py --projeto <NOME_PROJETO>
```

### O que o script faz automaticamente:
1. Copia os DDLs de dimensões e fatos gerados para `entrega/camada_semantica/ddl/`.
2. Gera amostras sintéticas em `entrega/camada_semantica/amostras/`.
3. Preenche automaticamente o `INTAKE_SEMANTICA.md` com as informações do DW.
4. Inicializa o catálogo do projeto em `documentacao/catalogo_projetos/`.
5. Valida a prontidão com `python core/scripts_comuns/validar_entrega.py semantica`.

