import sqlite3
import os
import tempfile
from .config import ARQ_SQLITE


def gerar_sql(base, fotos, historico):
    ARQ_SQLITE.parent.mkdir(parents=True, exist_ok=True)
    fd, temporario = tempfile.mkstemp(
        prefix=f".{ARQ_SQLITE.stem}.",
        suffix=".tmp",
        dir=ARQ_SQLITE.parent,
    )
    os.close(fd)
    try:
        con = sqlite3.connect(temporario)
        try:
            base.to_sql("base_consolidada", con, if_exists="replace", index=False)
            fotos.to_sql("fotos_normalizadas", con, if_exists="replace", index=False)
            historico.to_sql("historico_visitas", con, if_exists="replace", index=False)
            con.execute(
                'CREATE INDEX idx_base_matricula ON base_consolidada ("Matrícula")'
            )
            con.execute(
                'CREATE INDEX idx_fotos_matricula ON fotos_normalizadas ("Matrícula")'
            )
            con.execute(
                'CREATE INDEX idx_hist_matricula ON historico_visitas ("Matrícula")'
            )
            con.commit()
            if con.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise RuntimeError("SQLite temporário reprovado no integrity_check.")
        finally:
            con.close()
        os.replace(temporario, ARQ_SQLITE)
        return ARQ_SQLITE
    except Exception:
        if os.path.exists(temporario):
            os.unlink(temporario)
        raise
