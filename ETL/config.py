from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

ENTRADA = ROOT / "ENTRADA"
SAIDA = ROOT / "SAIDA"
LOG = ROOT / "LOG"

ARQ_EXCEL = SAIDA / "CONSOLIDADO_ESGOTO.xlsx"
ARQ_SQLITE = SAIDA / "base_esgoto.db"
ARQ_LOG = LOG / "execucao_etl.txt"
