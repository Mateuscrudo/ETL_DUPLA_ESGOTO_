import re
import numpy as np
import pandas as pd
from .ler_bases import nt

def limpar_endereco(endereco):
    """
    Padroniza o endereço removendo identificadores
    que aparecem indevidamente no início.

    Regras:

    1. Cantagalo:
       9741-CG - RUA...
       9741-CGN - RUA...
       9908CGN - RUA...
       3846-CG - RUA...

       Remove somente o identificador inicial.

    2. Endereço começando com "-":
       - RUA...
       - VIELA...

       Remove somente o hífen inicial.

    3. Não altera o restante do endereço.
       Exemplos:
       COMPL MC1151
       COMPL MC5137

    4. Não tenta corrigir endereços incompletos.
    """

    if endereco is None or pd.isna(endereco):
        return None

    endereco = str(endereco).strip()

    if not endereco:
        return None


    # =====================================================
    # REGRA 1 - CANTAGALO
    # =====================================================
    #
    # Exemplos:
    #
    # 9741-CG - RUA ONZE...
    # 9741-CGN - RUA ONZE...
    # 9908CGN - RUA VINTE...
    # 3846-CG - RUA VINTE...
    #
    # O CG/CGN identifica Cantagalo.
    #
    padrao_cantagalo = (
        r"^\s*\d{4,5}\s*-?\s*CGN?\s*[-–—:;|]\s*"
    )

    endereco = re.sub(
        padrao_cantagalo,
        "",
        endereco,
        flags=re.IGNORECASE
    )

    # =====================================================
    # REGRA 2 - HÍFEN SOLTO NO INÍCIO
    # =====================================================
    #
    # Exemplos:
    #
    # - RUA JARANAS B...
    # - VIELA E...
    #
    # Remove apenas o separador.
    #
    endereco = re.sub(
        r"^\s*[-–—]\s*",
        "",
        endereco
    )

    endereco = endereco.strip()

    return endereco


def link_registro(row):
    """Somente o link fornecido pela exportação, sem construir URLs por matrícula."""
    from urllib.parse import urlsplit
    if row is None:
        return None
    value = row.get("Link Backoffice")
    if value is None or pd.isna(value):
        return None
    value = str(value).strip()
    try:
        parsed = urlsplit(value)
        return value if parsed.scheme in {"https", "http"} and parsed.hostname else None
    except ValueError:
        return None

def consolidar(r, a):
    r_valid = r.dropna(subset=["_mat"]).copy()
    a_valid = a[(~a["_dup"]) & a["_mat"].notna()].copy()

    # Último registro de cada fonte.
    r_latest = (
        r_valid
        .sort_values(["_mat", "_dt"], na_position="first", kind="stable")
        .groupby("_mat")
        .tail(1)
        .set_index("_mat")
    )

    a_latest = (
        a_valid
        .sort_values(["_mat", "_dt", "_ord"], na_position="first", kind="stable")
        .groupby("_mat")
        .tail(1)
        .set_index("_mat")
    )

    # Acumulado do registro mais recente de cada sistema, nunca o máximo histórico.
    r_vis = r_latest["_vis"].fillna(0)
    a_vis = a_latest["_vis"].fillna(0)

    rk = set(r_vis.index)
    ak = set(a_vis.index)

    registros = []

    for matricula in sorted(rk | ak):
        rr = r_latest.loc[matricula] if matricula in r_latest.index else None
        aa = a_latest.loc[matricula] if matricula in a_latest.index else None

        r_dt = rr["_dt"] if rr is not None else pd.NaT
        a_dt = aa["_dt"] if aa is not None else pd.NaT

        # REGRA: o registro mais recente é a fonte principal dos dados cadastrais.
        # Em caso de empate, AppDeep tem prioridade.
        if aa is not None and (
            rr is None
            or pd.isna(r_dt)
            or (pd.notna(a_dt) and a_dt >= r_dt)
        ):
            latest = aa
            data_execucao = a_dt
            endereco = limpar_endereco(aa.get("Endereço"))
            bairro = nt(aa.get("Bairro"))
            nome = nt(aa.get("Nome completo"))
            agente = nt(aa.get("Nome do Agente"))
        else:
            latest = rr

            # Neste ponto rr necessariamente existe,
            # pois o if acima já tratou o caso rr is None.
            assert rr is not None

            data_execucao = r_dt

            endereco = limpar_endereco(
                rr.get("Endereço")
            )

            bairro = nt(
                rr.get("Bairro")
            )

            nome = nt(
                rr.get("Nome Completo")
            )

            agente = nt(
                rr.get("_agent")
            )

        assert latest is not None

        rv = float(r_vis.get(matricula, 0) or 0)
        av = float(a_vis.get(matricula, 0) or 0)

        if not np.isfinite(rv):
            rv = 0
        if not np.isfinite(av):
            av = 0

        registros.append({
            "Matrícula": matricula,
            "Endereço": endereco,
            "Nome do Morador": nome,
            "Bairro": bairro,
            "Data de Execução": data_execucao,
            # REGRA: soma dos acumulados das duas bases.
            "Quantidade de Visitas": int(rv + av),
            # Roteiro já convertido na leitura; status acompanha a fonte mais recente.
            "status": latest.get("_status"),
            "Agente Responsável": agente,
            "origem_adesao": "APPDEEP" if latest is aa else "ROTEIRO",
            "data_origem_adesao": data_execucao,
            "link_appdeep": link_registro(latest) if latest is aa else None,
            "registro_appdeep": nt(latest.get("Code Deep")) if latest is aa else None,
            "Origem dos Dados": (
                "AMBOS" if matricula in rk and matricula in ak
                else "ROTEIRO" if matricula in rk
                else "APPDEEP"
            ),
        })

    base = pd.DataFrame(registros, columns=[
        "Matrícula", "Endereço", "Nome do Morador", "Bairro", "Data de Execução",
        "Quantidade de Visitas", "status", "Agente Responsável", "Origem dos Dados",
        "origem_adesao", "data_origem_adesao", "link_appdeep", "registro_appdeep",
    ])

    # Uma linha por tentativa do Roteiro, com os dados próprios da tentativa.
    eventos = []
    for _, row in r.iterrows():
        tentativas = []
        for numero in (1, 2, 3):
            data_original = row.get(f"Data tentativa (T{numero})")
            status = nt(row.get(f"Status tentativa (T{numero})"))
            agente = nt(row.get(f"Equipe (T{numero})"))
            if pd.notna(data_original) or status is not None or agente is not None:
                tentativas.append({
                    "Data": pd.to_datetime(data_original, errors="coerce", dayfirst=True),
                    "Status": status, "Agente": agente,
                    "Visitas": 1, "Tentativa": f"T{numero}",
                })
        # A execução é uma visita própria; linhas sem tentativas preservam o registro.
        if not tentativas or row["_status"] == "Adesão executada":
            tentativas.append({
                "Data": row["_dt"], "Status": row["_status"],
                "Agente": row["_agent"], "Visitas": 1,
                "Tentativa": "EXECUÇÃO" if row["_status"] == "Adesão executada" else "REGISTRO",
            })
        for evento in tentativas:
            eventos.append({
                "Matrícula": row["_mat"], "Origem": "ROTEIRO",
                "Endereço": nt(row.get("Endereço")), "Bairro": nt(row.get("Bairro")),
                "Nome do Morador": nt(row.get("Nome Completo")),
                "Status do Registro": "ORIGINAL", **evento,
            })
    colunas_hist = ["Matrícula", "Origem", "Data", "Visitas", "Agente", "Endereço",
                    "Bairro", "Nome do Morador", "Status do Registro", "Status", "Tentativa"]
    historico_r = pd.DataFrame(eventos, columns=colunas_hist)

    # Envios repetidos não entram em nenhuma saída, inclusive no histórico.
    a_hist = a[a["_dup"].eq(False)]
    historico_a = pd.DataFrame({
        "Matrícula": a_hist["_mat"], "Origem": "APPDEEP",
        "Data": a_hist["_dt"], "Visitas": 1,
        "Agente": a_hist["Nome do Agente"].map(nt),
        "Endereço": a_hist["Endereço"].map(nt), "Bairro": a_hist["Bairro"].map(nt),
        "Nome do Morador": a_hist["Nome completo"].map(nt),
        "Status do Registro": "ORIGINAL", "Status": a_hist["_status"],
        "Tentativa": "REGISTRO",
        "link_appdeep": a_hist.apply(link_registro, axis=1),
        "registro_appdeep": a_hist.get("Code Deep", pd.Series(None, index=a_hist.index)),
    })

    historico = (
        pd.concat([historico_r, historico_a], ignore_index=True)
        .sort_values(
            ["Matrícula", "Data", "Origem"],
            na_position="last"
        )
        .reset_index(drop=True)
    )

    return base, historico
