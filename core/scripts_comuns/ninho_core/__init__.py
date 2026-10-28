"""
Utilitários e motores compartilhados do NINHO.

- `console`, `paths`, `catalogo`: saída padronizada, pastas canônicas e fichas do projeto.
- `xml_seguro`, `zip_seguro`, `leitores`, `lgpd`: leitura segura de insumos do cliente e LGPD.
- `dw_modelo`, `dw_patches`, `odi`, `guia_bi`: motores do Planejador de DW (Fast-Track).
- `visual_comum`, `diagramas`, `mockup_bi`, `prova_dax`, `office`, `pdf`: artefatos visuais e documentos.
- `hop_gerador`: pacote Apache Hop e migração Kettle.

Diagnóstico: `NINHO_LOG_LEVEL=DEBUG` mostra no stderr as exceções tratadas silenciosamente
(arquivos de cliente com formato inesperado, dependências opcionais ausentes etc.).
"""

import logging
import os
import sys

_nivel = os.environ.get("NINHO_LOG_LEVEL", "").strip().upper()
if _nivel and not logging.getLogger("ninho").handlers:
    _handler = logging.StreamHandler(sys.stderr)
    _handler.setFormatter(logging.Formatter("[%(levelname)s] %(name)s: %(message)s"))
    logging.getLogger("ninho").addHandler(_handler)
    logging.getLogger("ninho").setLevel(getattr(logging, _nivel, logging.WARNING))
