import pandas as pd
from .config import ARQ_EXCEL


def gerar_excel(base, fotos, historico):
    ARQ_EXCEL.parent.mkdir(parents=True, exist_ok=True)

    # Não colocar as fotos dentro da Base_Consolidada.
    # Elas ficam normalizadas na própria aba.
    with pd.ExcelWriter(
        ARQ_EXCEL,
        engine="openpyxl"
    ) as writer:
        base.to_excel(
            writer,
            sheet_name="Base_Consolidada",
            index=False
        )

        fotos.to_excel(
            writer,
            sheet_name="Fotos_Normalizadas",
            index=False
        )

        historico.to_excel(
            writer,
            sheet_name="Historico_Visitas",
            index=False
        )

    return ARQ_EXCEL
