import sqlite3
from .config import ARQ_SQLITE


def gerar_sql(base, fotos, historico):
    ARQ_SQLITE.parent.mkdir(parents=True, exist_ok=True)

    if ARQ_SQLITE.exists():
        ARQ_SQLITE.unlink()

    with sqlite3.connect(ARQ_SQLITE) as con:
        base.to_sql(
            "base_consolidada",
            con,
            if_exists="replace",
            index=False
        )

        fotos.to_sql(
            "fotos_normalizadas",
            con,
            if_exists="replace",
            index=False
        )

        historico.to_sql(
            "historico_visitas",
            con,
            if_exists="replace",
            index=False
        )

        con.execute(
            'CREATE INDEX idx_base_matricula '
            'ON base_consolidada ("Matrícula")'
        )

        con.execute(
            'CREATE INDEX idx_fotos_matricula '
            'ON fotos_normalizadas ("Matrícula")'
        )

        con.execute(
            'CREATE INDEX idx_hist_matricula '
            'ON historico_visitas ("Matrícula")'
        )

        con.commit()

    return ARQ_SQLITE
