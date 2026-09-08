import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Le mie Finanze", page_icon="💰", layout="centered")

# --- CONNESSIONE DATABASE (Google Sheets) ---
conn = st.connection("gsheets", type=GSheetsConnection)

# Funzioni per leggere i dati dai 3 fogli
@st.cache_data(ttl=5) # Aggiorna i dati ogni 5 secondi
def get_data(worksheet):
    df = conn.read(worksheet=worksheet)
    return df.dropna(how="all")

try:
    df_movimenti = get_data("Movimenti")
    df_conti = get_data("Conti")
    df_wishlist = get_data("Wishlist")
except Exception as e:
    st.error("Errore di connessione ai fogli. Assicurati che i nomi dei fogli siano corretti: 'Movimenti', 'Conti', 'Wishlist'.")
    st.stop()

# --- CALCOLI GLOBALI ---
# Calcola il saldo attuale per ogni conto (Saldo_Iniziale + Entrate - Uscite)
saldature_conti = {}
for index, conto in df_conti.iterrows():
    nome = conto['Nome']
    saldo_iniziale = pd.to_numeric(conto['Saldo_Iniziale'])
    
    # Filtra i movimenti per questo conto
    movimenti_conto = df_movimenti[df_movimenti['Conto'] == nome]
    entrate = pd.to_numeric(movimenti_conto[movimenti_conto['Tipo'] == 'Entrata']['Importo']).sum()
    uscite = pd.to_numeric(movimenti_conto[movimenti_conto['Tipo'] == 'Uscita']['Importo']).sum()
    
    saldo_attuale = saldo_iniziale + entrate - uscite
    saldature_conti[nome] = {
        "saldo": saldo_attuale,
        "tesoretto": pd.to_numeric(conto['Tesoretto'])
    }


# --- MENU LATERALE (Hamburger menu su mobile) ---
st.sidebar.title("Navigazione 🧭")
sezione = st.sidebar.radio("Vai a:", ["Panoramica Generale", "Inserisci Movimenti", "I Miei Conti", "Lista dei Desideri"])


# --- SEZIONE 1: PANORAMICA GENERALE ---
if sezione == "Panoramica Generale":
    st.title("Panoramica 📊")
    
    # Mostra i saldi totali
    totale_disponibile = sum(c['saldo'] for c in saldature_conti.values())
    
    st.metric("Patrimonio Totale", f"{totale_disponibile:.2f} €")
    
    st.subheader("Situazione Conti")
    for nome, dati in saldature_conti.items():
        col1, col2 = st.columns([3, 1])
        col1.write(f"**{nome}**")
        col2.write(f"{dati['saldo']:.2f} €")
        st.progress(min(dati['saldo'] / max((dati['tesoretto'] * 2), 1), 1.0)) # Barra puramente visiva
        
    st.divider()
    st.subheader("Ultimi 5 Movimenti")
    if not df_movimenti.empty:
        ultimi = df_movimenti.tail(5).iloc[::-1] # Prende gli ultimi 5 e li inverte
        st.dataframe(ultimi[['Data', 'Descrizione', 'Importo', 'Tipo']], use_container_width=True, hide_index=True)


# --- SEZIONE 2: INSERISCI MOVIMENTI ---
elif sezione == "Inserisci Movimenti":
    st.title("Nuova Transazione 💸")
    
    if df_conti.empty:
        st.warning("⚠️ Prima devi creare almeno un conto nella sezione 'I Miei Conti'.")
    else:
        with st.form("form_movimenti", clear_on_submit=True):
            tipo = st.radio("Tipo di movimento", ["Uscita", "Entrata"], horizontal=True)
            importo = st.number_input("Importo (€)", min_value=0.01, format="%.2f")
            conto = st.selectbox("Seleziona Conto", df_conti['Nome'].tolist())
            categoria = st.selectbox("Categoria", ["Spesa", "Casa", "Svago", "Auto", "Stipendio", "Risparmio", "Altro"])
            descrizione = st.text_input("Descrizione")
            
            if st.form_submit_button("Salva Movimento"):
                nuovo_movimento = pd.DataFrame([{
                    "Data": datetime.now().strftime("%Y-%m-%d"),
                    "Conto": conto,
                    "Tipo": tipo,
                    "Categoria": categoria,
                    "Importo": importo,
                    "Descrizione": descrizione
                }])
                df_aggiornato = pd.concat([df_movimenti, nuovo_movimento], ignore_index=True)
                conn.update(worksheet="Movimenti", data=df_aggiornato)
                st.success("Salvato!")
                st.rerun()


# --- SEZIONE 3: I MIEI CONTI ---
elif sezione == "I Miei Conti":
    st.title("Gestione Conti 🏦")
    st.write("Crea i tuoi portafogli (es. Conto Corrente, Carta Prepagata, Salvadanaio).")
    
    with st.form("form_conti", clear_on_submit=True):
        nome_conto = st.text_input("Nome Conto (es. Revolut, Intesa)")
        saldo_iniziale = st.number_input("Saldo Iniziale (€)", min_value=0.0, format="%.2f")
        tesoretto = st.number_input("Tesoretto Intoccabile (€) - Soglia di sicurezza", min_value=0.0, format="%.2f")
        
        if st.form_submit_button("Aggiungi Conto"):
            nuovo_conto = pd.DataFrame([{
                "Nome": nome_conto,
                "Saldo_Iniziale": saldo_iniziale,
                "Tesoretto": tesoretto
            }])
            df_aggiornato = pd.concat([df_conti, nuovo_conto], ignore_index=True)
            conn.update(worksheet="Conti", data=df_aggiornato)
            st.success("Conto aggiunto!")
            st.rerun()


# --- SEZIONE 4: LISTA DEI DESIDERI E RISPARMI ---
elif sezione == "Lista dei Desideri":
    st.title("Wishlist 🎯")
    
    # 1. Sistema di Allerta
    st.subheader("Cosa puoi permetterti oggi?")
    conto_risparmio = st.selectbox("Seleziona il conto da cui attingere i risparmi:", df_conti['Nome'].tolist())
    
    if conto_risparmio in saldature_conti:
        saldo_disponibile = saldature_conti[conto_risparmio]['saldo']
        tesoretto = saldature_conti[conto_risparmio]['tesoretto']
        potere_acquisto = saldo_disponibile - tesoretto
        
        st.info(f"💰 Sul conto **{conto_risparmio}** hai {saldo_disponibile:.2f} €.\nTogliendo il tesoretto di {tesoretto:.2f} €, il tuo budget reale è: **{potere_acquisto:.2f} €**")
        
        # Mostra avvisi per gli oggetti che puoi comprare
        if not df_wishlist.empty:
            oggetti_acquistabili = df_wishlist[(df_wishlist['Stato'] == 'Da comprare') & (pd.to_numeric(df_wishlist['Costo']) <= potere_acquisto)]
            
            if not oggetti_acquistabili.empty:
                st.success("🎉 **Puoi permetterti questi oggetti!**")
                for index, row in oggetti_acquistabili.iterrows():
                    st.write(f"- 🎁 **{row['Oggetto']}** ({row['Costo']} €)")
            else:
                st.warning("Non hai ancora abbastanza budget extra per gli oggetti nella lista.")
    
    st.divider()
    
    # 2. Inserimento nuovi desideri
    with st.form("form_wishlist", clear_on_submit=True):
        st.write("Aggiungi un nuovo obiettivo")
        oggetto = st.text_input("Cosa vuoi comprare?")
        costo = st.number_input("Costo Stimato (€)", min_value=1.0, format="%.2f")
        
        if st.form_submit_button("Aggiungi alla Wishlist"):
            nuovo_desiderio = pd.DataFrame([{
                "Oggetto": oggetto,
                "Costo": costo,
                "Stato": "Da comprare"
            }])
            df_aggiornato = pd.concat([df_wishlist, nuovo_desiderio], ignore_index=True)
            conn.update(worksheet="Wishlist", data=df_aggiornato)
            st.success("Desiderio aggiunto!")
            st.rerun()
            
    # 3. Lista Completa
    st.subheader("I tuoi obiettivi")
    if not df_wishlist.empty:
        st.dataframe(df_wishlist[['Oggetto', 'Costo', 'Stato']], use_container_width=True, hide_index=True)
