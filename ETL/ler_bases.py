from io import BytesIO
from .leitura_arquivo import ler_bytes
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


def status_consolidado(linha):
    """Aplica somente as conversões de status documentadas no processo."""
    status_colunas = [
        coluna for coluna in linha.index
        if str(coluna).strip().lower() in {
            "status",
            "status original",
            "status da visita",
        }
    ]
    status = nt(next((linha[coluna] for coluna in status_colunas
                     if nt(linha[coluna]) is not None), None))
    if not status:
        return None

    status_normalizado = status.casefold()
    if status_normalizado == "cancelado":
        return "Cancelado"
    if status_normalizado in {
        "impedimento campo",
        "pendente validação",
        "executado conferido",
    }:
        return "Adesão executada"

    def status_tentativa(numero):
        return nt(linha.get(f"Status tentativa (T{numero})"))

    if status_normalizado == "impedimento finalizado":
        return status_tentativa(3)

    if status_normalizado in {"programado", "disp. p/ programação"}:
        for numero in (3, 2, 1):
            valor = status_tentativa(numero)
            if valor:
                return valor
        return "Não visitado"

    return status


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


def horario_ordenacao(valor):
    """Hora auxiliar: aceita hora Excel, texto ou datetime; não sai na consulta."""
    if pd.isna(valor):
        return pd.NaT
    if isinstance(valor, (int, float)):
        return pd.to_timedelta(valor % 1, unit="D")
    texto = str(valor).strip()
    if " " in texto:
        texto = texto.rsplit(" ", 1)[-1]
    if texto.count(":") == 1:
        texto += ":00"
    try:
        return pd.to_timedelta(texto)
    except (ValueError, TypeError):
        return pd.NaT


def ler_bases():
    roteiro_path = localizar_base("ROTEIRO")
    appdeep_path = localizar_base("APPDEEP")

    print(f"📘 Roteiro encontrado: {roteiro_path.name}")
    print(f"📗 AppDeep encontrado: {appdeep_path.name}")

    bytes_roteiro = ler_bytes(roteiro_path)
    bytes_appdeep = ler_bytes(appdeep_path)
    with pd.ExcelFile(BytesIO(bytes_roteiro)) as excel:
        abas_roteiro = excel.sheet_names
    with pd.ExcelFile(BytesIO(bytes_appdeep)) as excel:
        abas_appdeep = excel.sheet_names

    if "Planilha1" not in abas_roteiro:
        raise ValueError(
            f"A base Roteiro '{roteiro_path.name}' não possui a aba "
            "'Planilha1'. Abas encontradas: "
            f"{abas_roteiro}"
        )
    if "Sheet1" not in abas_appdeep:
        raise ValueError(
            f"A base AppDeep '{appdeep_path.name}' não possui a aba "
            "'Sheet1'. Abas encontradas: "
            f"{abas_appdeep}"
        )

    r = pd.read_excel(BytesIO(bytes_roteiro), sheet_name="Planilha1")
    a = pd.read_excel(BytesIO(bytes_appdeep), sheet_name="Sheet1")

    obrig_r = [
        "Matricula", "Dt. Execução", "Qtd. Tentat.",
        "Endereço", "Bairro", "Nome Completo", "Foto(s)"
    ]
    obrig_a = [
        "Matrícula DEEP", "codigo_unico_deep", "Data do registro",
        "visitas", "Tipo Registro Visita", "Endereço", "Bairro",
        "Nome completo", "Nome do Agente", "Situação Campo", "Hora do registro"
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
        "_status": r.apply(status_consolidado, axis=1),
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
            .eq("duplicado").fillna(False)
        ),
        "_status": a["Situação Campo"].map(nt).fillna("Adesão executada"),
    }, index=a.index)

    a_aux["_ord"] = (
        a_aux["_dt"].dt.normalize()
        + pd.Series([horario_ordenacao(v) for v in a["Hora do registro"]],
                    index=a.index, dtype="timedelta64[ns]").fillna(pd.Timedelta(0))
    )
    a = pd.concat([a, a_aux], axis=1)

    print(f"📊 Registros Roteiro: {len(r):,}")
    print(f"📊 Registros AppDeep: {len(a):,}")
    print(f"♻️ Registros duplicados AppDeep: {int(a['_dup'].sum()):,}")

    return r, a, roteiro_path, appdeep_path
