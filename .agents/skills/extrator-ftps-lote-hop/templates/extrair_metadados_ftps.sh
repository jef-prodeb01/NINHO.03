#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# Script: extrair_metadados_ftps.sh
# Finalidade: Descoberta, metadados de arquivos (.xlsx/.csv) no FTPS e geracao de CSV.
# ==============================================================================

AMBIENTE="${HOP_ENVIRONMENT_NAME:-PRD}"
PROJETO="${HOP_PROJECT_NAME:-PROJETO}"

FTP_HOST="${ENV_FTP_HOST:-}"
FTP_PORT="${ENV_FTP_PORT:-21}"
FTP_USER="${ENV_FTP_USER:-}"
FTP_PASS="${ENV_FTP_PASS:-}"
FTP_DIR="${ENV_FTP_REMT_DIR:-/}"

[[ "${FTP_DIR}" != /* ]] && FTP_DIR="/${FTP_DIR}"
[[ "${FTP_DIR}" != */ ]] && FTP_DIR="${FTP_DIR}/"

REMOTE_URL="ftp://${FTP_HOST}:${FTP_PORT}${FTP_DIR}"
CSV_DIR="${ENV_DIR_DEST:-./entrada}"
CSV_OUTPUT="${CSV_DIR}/arquivos_ftps_${PROJETO}.csv"

LOG_DIR="${PROJECT_HOME:-.}/logs"
LOG_FILE="${LOG_DIR}/extrair_metadados_${PROJETO}_$(date '+%Y%m%d_%H%M%S').log"
mkdir -p "${LOG_DIR}" "${CSV_DIR}"
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "=============================================================================="
echo "Iniciando Varredura FTPS: ${REMOTE_URL} [Ambiente: ${AMBIENTE}]"
echo "Data/Hora: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=============================================================================="

echo "NOME_PROJETO;NOME_ARQUIVO;DATA_MODIFICACAO;TAMANHO_BYTES;STATUS_CARGA" > "${CSV_OUTPUT}"

curl -s --ssl-reqd --insecure \
     -u "${FTP_USER}:${FTP_PASS}" \
     --list-only "${REMOTE_URL}" | while read -r file; do
    if [[ "${file}" =~ \.(xlsx|csv|txt)$ ]]; then
        SIZE=$(curl -s --ssl-reqd --insecure -u "${FTP_USER}:${FTP_PASS}" -sI "${REMOTE_URL}${file}" | grep -i Content-Length | awk '{print $2}' | tr -d '\r')
        echo "${PROJETO};${file};$(date '+%Y-%m-%d %H:%M:%S');${SIZE:-0};PENDENTE" >> "${CSV_OUTPUT}"
    fi
done

echo "Concluido. Manifesto gerado em: ${CSV_OUTPUT}"

