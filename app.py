import streamlit as st
import pandas as pd
import requests
from io import BytesIO

HEADERS = {"Accept": "application/json"}
ORCID_API = "https://pub.orcid.org/v3.0"

st.set_page_config(page_title="Enriquecedor ORCID", layout="wide")

st.title("🔎 Enriquecedor de Dados ORCID")
st.markdown("Aplicação para extração automática de identificação, afiliação e obras de pesquisadores via ORCID.")

# -------------------------------------------------
# 1. Funções
# -------------------------------------------------

def extrair_identificacao(orcid):
    url = f"{ORCID_API}/{orcid}/person"
    r = requests.get(url, headers=HEADERS)
    if r.status_code != 200:
        return {}

    p = r.json()

    given_name = p.get("name", {}).get("given-names", {}).get("value")
    family_name = p.get("name", {}).get("family-name", {}).get("value")

    addresses = p.get("addresses", {}).get("address", [])
    country = None
    if addresses:
        country = addresses[0].get("country", {}).get("value")

    return {
        "orcid": orcid,
        "given_name": given_name,
        "family_name": family_name,
        "country": country
    }


def extrair_obras(orcid):
    url = f"{ORCID_API}/{orcid}/works"
    r = requests.get(url, headers=HEADERS)
    obras = []

    if r.status_code != 200:
        return obras

    for group in r.json().get("group", []):
        for w in group.get("work-summary", []):
            doi = None
            for eid in w.get("external-ids", {}).get("external-id", []):
                if eid.get("external-id-type") == "doi":
                    doi = eid.get("external-id-value")

            year = w.get("publication-date", {}).get("year", {}).get("value")

            obras.append({
                "titulo": w.get("title", {}).get("title", {}).get("value"),
                "tipo": w.get("type"),
                "ano": year,
                "doi": doi
            })

    return obras


# -------------------------------------------------
# 2. Interface
# -------------------------------------------------

uploaded_file = st.file_uploader("📂 Envie um arquivo Excel com a coluna 'ORCID'", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    if "ORCID" not in df.columns:
        st.error("O arquivo precisa conter uma coluna chamada 'ORCID'")
    else:
        st.success("Arquivo carregado com sucesso!")

        if st.button("🚀 Processar ORCIDs"):
            resultados = []

            progress_bar = st.progress(0)

            for i, row in df.iterrows():
                orcid = row["ORCID"]

                if pd.isna(orcid):
                    continue

                autor = extrair_identificacao(orcid)
                if not autor:
                    continue

                obras = extrair_obras(orcid)

                for obra in obras:
                    obra.update({
                        "orcid": autor["orcid"],
                        "given_name": autor["given_name"],
                        "family_name": autor["family_name"],
                        "country": autor["country"]
                    })
                    resultados.append(obra)

                progress_bar.progress((i + 1) / len(df))

            df_saida = pd.DataFrame(resultados)

            st.success("Processamento concluído!")
            st.dataframe(df_saida.head())

            # Gerar arquivo para download
            output = BytesIO()
            df_saida.to_excel(output, index=False)
            output.seek(0)

            st.download_button(
                label="📥 Baixar Excel Enriquecido",
                data=output,
                file_name="autores_enriquecidos_orcid.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
