"""
App Streamlit: Conversor CIAP2 <-> CID10 (base nativa do repositório)

Requisitos:
- Arquivos na mesma pasta do app:
  - app_streamlit.py
  - ciap_cid.csv  (com colunas: CIAP,DescricaoCIAP,CID10,DescricaoCID)
"""

from __future__ import annotations

import os
import re

import pandas as pd
import streamlit as st


# -----------------------------
# Utilitários
# -----------------------------
def normalize_code(value: str) -> str:
    """
    Normaliza um código (CIAP ou CID):
    - remove espaços
    - coloca em maiúsculo
    """
    return (value or "").strip().upper().replace(" ", "")


def split_inputs(text: str) -> list[str]:
    """
    Divide a entrada do usuário em uma lista de códigos.
    Aceita separação por:
    - novas linhas
    - vírgula
    - ponto e vírgula
    - tab
    """
    if not text:
        return []
    parts = re.split(r"[,\n;\t]+", text)
    return [normalize_code(p) for p in parts if normalize_code(p)]


@st.cache_data(show_spinner=False)
def load_base(csv_path: str) -> pd.DataFrame:
    """
    Carrega a base CIAP/CID do CSV do repositório e cria colunas normalizadas
    para busca rápida.
    """
    df = pd.read_csv(csv_path, encoding="utf-8-sig")

    required = {"CIAP", "CID10"}
    if not required.issubset(df.columns):
        raise ValueError(
            f"CSV inválido. Precisa ter colunas {required}. "
            f"Colunas encontradas: {list(df.columns)}"
        )

    # Colunas de descrição são opcionais — se não existirem, cria vazias
    if "DescricaoCIAP" not in df.columns:
        df["DescricaoCIAP"] = ""
    if "DescricaoCID" not in df.columns:
        df["DescricaoCID"] = ""

    # Normalizados para lookup
    df["CIAP_N"] = df["CIAP"].astype(str).map(normalize_code)
    df["CID10_N"] = df["CID10"].astype(str).map(normalize_code)

    return df


def lookup(df: pd.DataFrame, mode: str, codes: list[str]) -> pd.DataFrame:
    """
    Faz lookup conforme o modo:
    - 'CIAP → CID' busca em CIAP_N
    - 'CID → CIAP' busca em CID10_N

    Retorna dataframe com resultados (inclui linhas "NÃO ENCONTRADO").
    """
    results: list[dict] = []

    if mode == "CIAP → CID":
        for c in codes:
            hit = df.loc[df["CIAP_N"] == c]
            if hit.empty:
                results.append(
                    {
                        "Entrada": c,
                        "Tipo": "CIAP",
                        "Resultado": "NÃO ENCONTRADO",
                        "CIAP": c,
                        "DescricaoCIAP": "",
                        "CID10": "",
                        "DescricaoCID": "",
                    }
                )
            else:
                for _, row in hit.iterrows():
                    results.append(
                        {
                            "Entrada": c,
                            "Tipo": "CIAP",
                            "Resultado": row["CID10"],
                            "CIAP": row["CIAP"],
                            "DescricaoCIAP": row["DescricaoCIAP"],
                            "CID10": row["CID10"],
                            "DescricaoCID": row["DescricaoCID"],
                        }
                    )
    else:  # 'CID → CIAP'
        for c in codes:
            hit = df.loc[df["CID10_N"] == c]
            if hit.empty:
                results.append(
                    {
                        "Entrada": c,
                        "Tipo": "CID",
                        "Resultado": "NÃO ENCONTRADO",
                        "CIAP": "",
                        "DescricaoCIAP": "",
                        "CID10": c,
                        "DescricaoCID": "",
                    }
                )
            else:
                for _, row in hit.iterrows():
                    results.append(
                        {
                            "Entrada": c,
                            "Tipo": "CID",
                            "Resultado": row["CIAP"],
                            "CIAP": row["CIAP"],
                            "DescricaoCIAP": row["DescricaoCIAP"],
                            "CID10": row["CID10"],
                            "DescricaoCID": row["DescricaoCID"],
                        }
                    )

    return pd.DataFrame(results)


# -----------------------------
# UI Streamlit
# -----------------------------
st.set_page_config(page_title="Conversor CIAP2 ↔ CID10", layout="centered")
st.title("Conversor CIAP2 ↔ CID10")

# Caminho do CSV no repositório (mesma pasta do app)
CSV_NAME = "ciap_cid.csv"
csv_path = os.path.join(os.path.dirname(__file__), CSV_NAME)
df_base = load_base(csv_path)

mode = st.radio("Modo de entrada:", ["CIAP → CID", "CID → CIAP"], horizontal=True)

placeholder = "Ex.: A01\nK86" if mode == "CIAP → CID" else "Ex.: I10\nR50"
raw_text = st.text_area(
    "Cole um ou mais códigos (um por linha, ou separados por vírgula/;):",
    height=120,
    placeholder=placeholder,
)

codes = split_inputs(raw_text)

col1, col2 = st.columns([1, 1])
with col1:
    do_search = st.button("Converter", use_container_width=True)
with col2:
    st.caption("Aceita lista (linhas, vírgula, ;).")

if do_search:
    if not codes:
        st.warning("Digite pelo menos um código.")
        st.stop()

    df_out = lookup(df_base, mode, codes)


    st.subheader("Resultado")
    for _, r in df_out.iterrows():
        if r["Resultado"] == "NÃO ENCONTRADO":
            st.warning(f"{r['Tipo']} {r['Entrada']} → NÃO ENCONTRADO")
            continue

        if mode == "CIAP → CID":
            st.info(
                f"CIAP {r['CIAP']} → CID {r['CID10']}\n\n"
                f"CIAP: {r['DescricaoCIAP']}\n\n"
                f"CID: {r['DescricaoCID']}"
            )
        else:
            st.info(
                f"CIAP {r['CIAP']} → CID {r['CID10']}\n\n"
                f"CIAP: {r['DescricaoCIAP']}\n\n"
                f"CID: {r['DescricaoCID']}"
            )
