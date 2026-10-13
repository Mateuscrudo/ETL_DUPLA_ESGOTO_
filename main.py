from ETL.ler_bases import ler_bases
from ETL.consolidar import consolidar
from ETL.processar_fotos import processar_fotos
from ETL.gerar_excel import gerar_excel
from ETL.gerar_sql import gerar_sql
from ETL.relatorio import salvar_relatorio


def executar():
    print("=== ETL ESGOTO ===")

    linhas = []

    # 1. Ler e validar as bases
    r, a, roteiro_path, appdeep_path = ler_bases()

    # 2. Consolidar matrículas e histórico
    base, historico = consolidar(r, a)

    # 3. Normalizar fotos
    fotos = processar_fotos(roteiro_path, a)

    # 4. Estatísticas
    rk = set(r["_mat"].dropna())
    ak = set(a.loc[a["_dup"].eq(False), "_mat"].dropna())

    ambos = len(rk & ak)
    somente_r = len(rk - ak)
    somente_a = len(ak - rk)

    linhas.extend([
        f"Roteiro: {roteiro_path.name} | registros={len(r)}",
        f"AppDeep: {appdeep_path.name} | registros={len(a)}",
        f"Matrículas Roteiro={len(rk)}",
        f"Matrículas AppDeep={len(ak)}",
        f"Matrículas em ambas={ambos}",
        f"Somente Roteiro={somente_r}",
        f"Somente AppDeep={somente_a}",
        f"Base consolidada={len(base)}",
        f"Fotos normalizadas={len(fotos)}",
        f"Histórico={len(historico)}",
        f"Duplicados AppDeep excluídos={int(a['_dup'].sum())}",
        f"AppDeep após limpeza={int(a['_dup'].eq(False).sum())}",
        f"Histórico sem matrícula={int(historico['Matrícula'].isna().sum())}",
        f"Histórico sem data={int(historico['Data'].isna().sum())}",
        f"Histórico sem status={int(historico['Status'].isna().sum())}",
        f"Base sem status={int(base['status'].isna().sum())}",
    ])

    # 5. Validar todas as estruturas antes de criar qualquer saída.
    if base["Matrícula"].isna().any():
        raise ValueError(
            "A Base_Consolidada possui matrícula vazia."
        )

    if not fotos.empty:
        if fotos["Matrícula"].isna().any():
            raise ValueError(
                "Fotos_Normalizadas possui foto sem matrícula."
            )

        if fotos["URL"].isna().any():
            raise ValueError(
                "Fotos_Normalizadas possui URL vazia."
            )

    # 6. Gerar Excel
    arq_excel = gerar_excel(
        base,
        fotos,
        historico
    )

    # 7. Gerar SQLite
    arq_sqlite = gerar_sql(
        base,
        fotos,
        historico
    )

    linhas.append(
        "STATUS=SUCESSO | Validações finais=OK | "
        f"matrículas={base['Matrícula'].notna().sum()} | "
        f"registros={len(base)} | fotos={len(fotos)} | "
        f"histórico={len(historico)}"
    )

    # 8. Gerar log
    arq_log = salvar_relatorio(linhas)

    print()
    print("=== RESULTADO ===")
    print(f"📊 Base Consolidada: {len(base):,}")
    print(f"📸 Fotos Normalizadas: {len(fotos):,}")
    print(f"📜 Histórico: {len(historico):,}")
    print()
    print(f"📗 Excel: {arq_excel}")
    print(f"🗄️ SQLite: {arq_sqlite}")
    print(f"📝 Log: {arq_log}")
    print()
    print("=== ETL CONCLUÍDO ===")


def main():
    try:
        executar()
    except Exception as erro:
        salvar_relatorio([f"STATUS=FALHA | {type(erro).__name__}: {erro}"])
        raise


if __name__ == "__main__":
    main()
