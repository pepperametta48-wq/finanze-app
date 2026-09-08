import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Le mie Finanze", page_icon="💸")
st.title("Gestione Finanze 💸")

conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(worksheet="Foglio1", usecols=[0, 1, 2, 3, 4])
df = df.dropna(how="all")

with st.form("nuova_transazione", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        importo = st.number_input("Importo (€)", min_value=0.0, format="%.2f", step=1.0)
        tipo = st.selectbox("Tipo", ["Uscita", "Entrata"])
    with col2:
        descrizione = st.text_input("Descrizione")
        categoria = st.selectbox("Categoria", ["Spesa", "Casa", "Svago", "Auto", "Stipendio", "Altro"])
        
    submit = st.form_submit_button("Aggiungi Transazione")

    if submit and importo > 0 and descrizione != "":
        nuova_riga = pd.DataFrame([{
            "Data": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "Descrizione": descrizione,
            "Categoria": categoria,
            "Tipo": tipo,
            "Importo": importo
        }])
        df_aggiornato = pd.concat([df, nuova_riga], ignore_index=True)
        conn.update(worksheet="Foglio1", data=df_aggiornato)
        st.success("Transazione salvata!")
        st.rerun()

st.divider()
st.subheader("Ultimi Movimenti")
st.dataframe(df, use_container_width=True, hide_index=True)
