import pandas as pd
from .config import ENTRADA


def nk(v):
    if pd.isna(v):
        return None
    s = str(v).strip().upper()
    return s if s and s not in {"NAN", "NONE"} else None


def nt(v):
    if pd.isna(v):
        return None
    s = str(v).strip()
    return s if s else None


def localizar_base(palavra):
    arquivos = [
        p for p in ENTRADA.iterdir()
        if p.is_file() and p.suffix.lower() in {".xlsx", ".xlsm", ".xls"}
    ]

    encontrados = [
        p for p in arquivos
        if palavra.upper() in p.stem.upper()
    ]

    if not encontrados:
        raise FileNotFoundError(
            f"Nenhuma base contendo '{palavra}' foi encontrada em:\n{ENTRADA}"
        )

    if len(encontrados) > 1:
        nomes = "\n".join(f" - {p.name}" for p in encontrados)
        raise RuntimeError(
            f"Foram encontradas várias bases contendo '{palavra}':\n{nomes}\n\n"
            "Deixe apenas uma base desse tipo na pasta ENTRADA."
        )

    return encontrados[0]


def ler_bases():
    roteiro_path = localizar_base("ROTEIRO")
    appdeep_path = localizar_base("APPDEEP")

    print(f"📘 Roteiro encontrado: {roteiro_path.name}")
    print(f"📗 AppDeep encontrado: {appdeep_path.name}")

    r = pd.read_excel(roteiro_path, sheet_name="Planilha1")
    a = pd.read_excel(appdeep_path, sheet_name="Sheet1")

    obrig_r = [
        "Matricula", "Dt. Execução", "Qtd. Tentat.",
        "Endereço", "Bairro", "Nome Completo", "Foto(s)"
    ]
    obrig_a = [
        "Matrícula DEEP", "codigo_unico_deep", "Data do registro",
        "visitas", "Tipo Registro Visita", "Endereço", "Bairro",
        "Nome completo", "Nome do Agente"
    ]

    falt_r = [c for c in obrig_r if c not in r.columns]
    falt_a = [c for c in obrig_a if c not in a.columns]

    if falt_r:
        raise ValueError(f"Colunas ausentes no Roteiro: {falt_r}")
    if falt_a:
        raise ValueError(f"Colunas ausentes no AppDeep: {falt_a}")

    # Cria as colunas auxiliares de uma vez para evitar DataFrame fragmentado.
    r_aux = pd.DataFrame({
        "_mat": r["Matricula"].map(nk),
        "_dt": pd.to_datetime(r["Dt. Execução"], errors="coerce", dayfirst=True),
        "_vis": pd.to_numeric(r["Qtd. Tentat."], errors="coerce").fillna(0),
    }, index=r.index)

    agent_cols = [
        c for c in ["Oficial", "Equipe (T3)", "Equipe (T2)", "Equipe (T1)"]
        if c in r.columns
    ]

    if agent_cols:
        r_aux["_agent"] = r[agent_cols].bfill(axis=1).iloc[:, 0].map(nt)
    else:
        r_aux["_agent"] = None

    r = pd.concat([r, r_aux], axis=1)

    matricula_deep = a["Matrícula DEEP"].map(nk)
    matricula_codigo = a["codigo_unico_deep"].map(nk)

    a_aux = pd.DataFrame({
        "_mat": matricula_deep.fillna(matricula_codigo),
        "_dt": pd.to_datetime(a["Data do registro"], errors="coerce", dayfirst=True),
        "_vis": pd.to_numeric(a["visitas"], errors="coerce"),
        "_dup": (
            a["Tipo Registro Visita"]
            .astype("string")
            .str.strip()
            .str.lower()
            .eq("duplicado")
        ),
    }, index=a.index)

    a = pd.concat([a, a_aux], axis=1)

    print(f"📊 Registros Roteiro: {len(r):,}")
    print(f"📊 Registros AppDeep: {len(a):,}")
    print(f"♻️ Registros duplicados AppDeep: {int(a['_dup'].sum()):,}")

    return r, a, roteiro_path, appdeep_path
