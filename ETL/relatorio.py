from .config import ARQ_LOG


def salvar_relatorio(linhas):
    ARQ_LOG.parent.mkdir(parents=True, exist_ok=True)
    ARQ_LOG.write_text(
        "\n".join(linhas) + "\n",
        encoding="utf-8"
    )
    return ARQ_LOG
