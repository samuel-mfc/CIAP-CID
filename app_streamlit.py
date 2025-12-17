"""
App Streamlit: Conversor CIAP2 <-> CID10

- Lê um CSV com colunas:
  CIAP,DescricaoCIAP,CID10,DescricaoCID

- Permite escolher se o usuário vai informar CIAP ou CID.
- Suporta múltiplas entradas (linhas / vírgula / ponto e vírgula).
"""

from __future__ import annotations

import re
import pandas as pd
import streamlit as st


# -----------------------------
# Utilitários
# -----------------------------
def normalize_code(value: str) -> str:
    """
    Normaliza um código:
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
def load_base(csv_file) -> pd.DataFrame:
    """
    Carrega a base a partir de um arquivo CSV (path ou UploadedFile)
    e cria colunas normalizadas para lookup.
    """
    df = pd.read_csv(csv_file, encoding="utf-8-sig")

    required = {"CIAP", "CID10"}
    if not required.issubset(df.columns):
        raise ValueError(
            f"CSV inválido. Precisa ter colunas {required}. "
            f"Colunas encontradas: {list(df.columns)}"
        )

    # Normalizados para busca
    df["CIAP_N"] = df["CIAP"].astype(str).map(normalize_code)
    df["CID10_N"] = df["CID10"].astype(str).map(normalize_code)

    # Garantir colunas de descrição mesmo se não existirem
    if "DescricaoCIAP" not in df.columns:
        df["DescricaoCIAP"] = ""
    if "DescricaoCID" not in df.columns:
        df["DescricaoCID"] = ""

    return df


def lookup(df: pd.DataFrame, mode: str, codes: list[str]) -> pd.DataFrame:
    """
    Faz lookup conforme modo:
    - mode = 'CIAP → CID' : procura CIAP_N
    - mode = 'CID → CIAP' : procura CID10_N

    Retorna dataframe com resultados (inclusive 'não encontrado').
    """
    results = []

    if mode == "CIAP → CID":
        for c in codes:
            hit = df.loc[df["CIAP_N"] == c]
            if hit.empty:
                results.append(
                    {"Entrada": c, "Tipo": "CIAP", "Resultado": "NÃO ENCONTRADO",
                     "CIAP": c, "DescricaoCIAP": "", "CID10": "", "DescricaoCID": ""}
                )
            else:
                # Se houver mais de uma correspondência, retornamos todas
                for _, row in hit.iterrows():
                    results.append(
                        {"Entrada": c, "Tipo": "CIAP", "Resultado": row["CID10"],
                         "CIAP": row["CIAP"], "DescricaoCIAP": row["DescricaoCIAP"],
                         "CID10": row["CID10"], "DescricaoCID": row["DescricaoCID"]}
                    )

    else:  # "CID → CIAP"
        for c in codes:
            hit = df.loc[df["CID10_N"] == c]
            if hit.empty:
                results.append(
                    {"Entrada": c, "Tipo": "CID", "Resultado": "NÃO ENCONTRADO",
                     "CIAP": "", "DescricaoCIAP": "", "CID10": c, "DescricaoCID": ""}
                )
            else:
                for _, row in hit.iterrows():
                    results.append(
                        {"Entrada": c, "Tipo": "CID", "Resultado": row["CIAP"],
                         "CIAP": row["CIAP"], "DescricaoCIAP": row["DescricaoCIAP"],
                         "CID10": row["CID10"], "DescricaoCID": row["DescricaoCID"]}
                    )

    return pd.DataFrame(results)


# -----------------------------
# UI Streamlit
# -----------------------------
st.set_page_config(page_title="Conversor CIAP2 ↔ CID10", layout="centered")

st.title("Conversor CIAP2 ↔ CID10")

st.write(
    "Carregue a base CSV (ou use um arquivo local) e escolha se vai digitar **CIAP** ou **CID**."
)

# Opção 1: upload
uploaded = st.file_uploader("Upload do arquivo ciap_cid.csv", type=["csv"])

# Opção 2: usar arquivo local (para quando você rodar no seu PC/servidor)
use_local = st.checkbox("Usar arquivo local 'ciap_cid.csv' (na mesma pasta do app)", value=True)

csv_source = None
if uploaded is not None:
    csv_source = uploaded
elif use_local:
    csv_source = "ciap_cid.csv"

if csv_source is None:
    st.info("Envie o CSV ou marque a opção de arquivo local.")
    st.stop()

# Carregar base
try:
    df_base = load_base(csv_source)
    st.success(f"Base carregada: {len(df_base)} linhas.")
except Exception as e:
    st.error(f"Erro ao carregar CSV: {e}")
    st.stop()

mode = st.radio("Modo de entrada:", ["CIAP → CID", "CID → CIAP"], horizontal=True)

placeholder = "Ex.: A01\nK86" if mode == "CIAP → CID" else "Ex.: I10\nR50"
raw_text = st.text_area("Cole um ou mais códigos (um por linha, ou separados por vírgula/;):", height=120, placeholder=placeholder)

codes = split_inputs(raw_text)

col1, col2 = st.columns([1, 1])
with col1:
    do_search = st.button("Converter", use_container_width=True)
with col2:
    st.caption("Dica: você pode colar uma lista inteira.")

if do_search:
    if not codes:
        st.warning("Digite pelo menos um código.")
        st.stop()

    df_out = lookup(df_base, mode, codes)

    st.subheader("Resultados")
    st.dataframe(df_out, use_container_width=True, hide_index=True)

    st.subheader("Visualização rápida")
    for _, r in df_out.iterrows():
        if r["Resultado"] == "NÃO ENCONTRADO":
            st.warning(f"{r['Tipo']} {r['Entrada']} → NÃO ENCONTRADO")
        else:
            if mode == "CIAP → CID":
                st.info(f"CIAP {r['CIAP']} → CID {r['CID10']}\n\n{r['DescricaoCIAP']}\n\n{r['DescricaoCID']}")
            else:
                st.info(f"CID {r['CID10']} → CIAP {r['CIAP']}\n\n{r['DescricaoCID']}\n\n{r['DescricaoCIAP']}")
