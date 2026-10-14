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

# Auditar pós-geração a pasta saida/ contra as 4 Regras de Ouro
python core/scripts_comuns/validar_entrega.py saida

# Validar todos os módulos e a pasta saida/ simultaneamente
python core/scripts_comuns/validar_entrega.py all
```

### Critérios Auditados (Pré-Voo e Pós-Geração):
- **Campos Obrigatórios:** Nome do projeto, schema alvo e tablespaces.
- **Pilha Tecnológica:** Seção 1 preenchida com as tecnologias de esteira.
- **Detecção de Documentação de Entrega:** Se perguntas e regras foram depositadas em arquivos na pasta `entrega/<modulo>/`, o validador aceita e aprova.
- **Auditoria Pós-Geração (`saida`):** Verifica ausência de subpastas não-canônicas com nome de projeto dentro de `saida/`, proibição de `BITMAP INDEX` em dimensões, presença de linha sentinela `-1`, geração condicional estrita (ex: proíbe Hop/ODI/Python se desmarcados no Intake) e presença do comentário `-- Grão:` nas views da Camada Semântica.

---

## 2. Inspetor Determinístico de DDLs de Origem (`inspecionar_ddl_origem.py`)

Extrai de forma determinística 100% das colunas, PKs, FKs, índices e diagnostica colunas de CDC incremental dos arquivos `.sql` em `entrega/planejador_dw/ddl/`:

```bash
python core/scripts_comuns/inspecionar_ddl_origem.py
```

---

## 3. Transição Contínua DW -> Semântica (`transicionar_dw_para_semantica.py`)

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

---

## 4. Empacotamento e Reset de Workspace (`gerenciar_projeto.py`)

Permite exportar a entrega completa do projeto (`.zip`) e limpar as pastas `saida/` e `entrega/` preservando os `.gitkeep` e `README.md`:

```bash
python core/scripts_comuns/gerenciar_projeto.py --status
python core/scripts_comuns/gerenciar_projeto.py --exportar ../entregas_clientes --projeto <SIGLA>
python core/scripts_comuns/gerenciar_projeto.py --resetar --confirmar
```


