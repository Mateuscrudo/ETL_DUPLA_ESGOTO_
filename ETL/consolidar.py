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

    original = endereco

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

    # Escapa caracteres especiais da matrícula
    matricula_regex = re.escape(matricula)

    # Remove a matrícula somente se estiver NO INÍCIO.
    padrao = rf"^\s*{matricula_regex}\s*[-–—:;|]*\s*"

    endereco_limpo = re.sub(
        padrao,
        "",
        endereco,
        flags=re.IGNORECASE
    )

    return endereco_limpo.strip()

def consolidar(r, a):
    r_valid = r.dropna(subset=["_mat"]).copy()
    a_valid = a[(~a["_dup"]) & a["_mat"].notna()].copy()

    # Último registro de cada fonte.
    r_latest = (
        r_valid
        .sort_values(["_mat", "_dt"], na_position="first")
        .groupby("_mat")
        .tail(1)
        .set_index("_mat")
    )

    a_latest = (
        a_valid
        .sort_values(["_mat", "_dt"], na_position="first")
        .groupby("_mat")
        .tail(1)
        .set_index("_mat")
    )

    # Visitas acumuladas por fonte.
    r_vis = r_valid.groupby("_mat")["_vis"].max().fillna(0)
    a_vis = a_valid.groupby("_mat")["_vis"].max().fillna(0)

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
            "Agente Responsável": agente,
            "Origem dos Dados": (
                "AMBOS" if matricula in rk and matricula in ak
                else "ROTEIRO" if matricula in rk
                else "APPDEEP"
            ),
        })

    base = pd.DataFrame(registros)

    # Histórico: mantém inclusive duplicados do AppDeep, identificados como tal.
    historico_r = pd.DataFrame({
        "Matrícula": r["_mat"],
        "Origem": "ROTEIRO",
        "Data": r["_dt"],
        "Visitas": r["_vis"],
        "Agente": r["_agent"],
        "Endereço": r["Endereço"].map(nt),
        "Bairro": r["Bairro"].map(nt),
        "Nome do Morador": r["Nome Completo"].map(nt),
        "Status do Registro": "ORIGINAL",
    })

    historico_a = pd.DataFrame({
        "Matrícula": a["_mat"],
        "Origem": "APPDEEP",
        "Data": a["_dt"],
        "Visitas": a["_vis"],
        "Agente": a["Nome do Agente"].map(nt),
        "Endereço": a["Endereço"].map(nt),
        "Bairro": a["Bairro"].map(nt),
        "Nome do Morador": a["Nome completo"].map(nt),
        "Status do Registro": np.where(
            a["_dup"], "DUPLICADO", "ORIGINAL"
        ),
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
