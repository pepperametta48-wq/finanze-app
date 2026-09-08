import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import plotly.express as px

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Le mie Finanze", page_icon="💸", layout="centered")

# --- CSS PERSONALIZZATO (Stile UI Moderna) ---
st.markdown("""
<style>
    .card-conto {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        color: white; padding: 20px; border-radius: 15px; 
        box-shadow: 0 10px 20px rgba(0,0,0,0.1); margin-bottom: 20px;
    }
    .card-movimento {
        background-color: #ffffff; padding: 15px; border-radius: 12px; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 10px; 
        display: flex; justify-content: space-between; align-items: center;
        border: 1px solid #f0f0f0;
    }
    .text-entrata { color: #10b981; font-weight: bold; font-size: 18px; }
    .text-uscita { color: #ef4444; font-weight: bold; font-size: 18px; }
    .importo-grande { font-size: 32px; font-weight: bold; margin: 10px 0; }
</style>
""", unsafe_allow_html=True)

# --- CONNESSIONE DATI ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=5)
def get_data(worksheet):
    df = conn.read(worksheet=worksheet)
    return df.dropna(how="all")

try:
    df_movimenti = get_data("Movimenti")
    df_conti = get_data("Conti")
    df_wishlist = get_data("Wishlist")
    df_abbonamenti = get_data("Abbonamenti")
except Exception as e:
    st.error("Errore di connessione. Assicurati che i fogli: Movimenti, Conti, Wishlist, Abbonamenti esistano.")
    st.stop()

# --- CALCOLO SALDI GLOBALI ---
saldature_conti = {}
for index, conto in df_conti.iterrows():
    nome = conto['Nome']
    saldo_iniziale = pd.to_numeric(conto['Saldo_Iniziale'])
    
    mov_conto = df_movimenti[df_movimenti['Conto'] == nome]
    entrate = pd.to_numeric(mov_conto[mov_conto['Tipo'] == 'Entrata']['Importo']).sum()
    uscite = pd.to_numeric(mov_conto[mov_conto['Tipo'] == 'Uscita']['Importo']).sum()
    
    saldo_attuale = saldo_iniziale + entrate - uscite
    saldature_conti[nome] = {"saldo": saldo_attuale, "tesoretto": pd.to_numeric(conto['Tesoretto'])}

# --- MENU LATERALE ---
st.sidebar.title("App Finanze 🧭")
sezione = st.sidebar.radio("Naviga:", ["Dashboard 📊", "Nuovo Movimento 💸", "I Miei Conti 🏦", "Abbonamenti 🔁", "Wishlist 🎁"])

# ==========================================
# 1. DASHBOARD
# ==========================================
if sezione == "Dashboard 📊":
    st.title("Panoramica")
    totale = sum(c['saldo'] for c in saldature_conti.values())
    
    # Card Patrimonio Totale
    st.markdown(f"""
    <div class="card-conto">
        <p style="margin:0; opacity:0.8;">Patrimonio Netto Disponibile</p>
        <p class="importo-grande">{totale:.2f} €</p>
    </div>
    """, unsafe_allow_html=True)

    # Grafici
    st.subheader("Analisi Spese")
    if not df_movimenti.empty:
        uscite_df = df_movimenti[df_movimenti['Tipo'] == 'Uscita'].copy()
        uscite_df['Importo'] = pd.to_numeric(uscite_df['Importo'])
        
        if not uscite_df.empty:
            # Grafico a ciambella
            fig = px.pie(uscite_df, values='Importo', names='Categoria', hole=0.4, 
                         color_discrete_sequence=px.colors.qualitative.Pastel)
            fig.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=300)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nessuna uscita registrata per generare il grafico.")

    st.subheader("Ultimi Movimenti")
    if not df_movimenti.empty:
        ultimi = df_movimenti.tail(5).iloc[::-1]
        for _, row in ultimi.iterrows():
            icona = "🟢" if row['Tipo'] == 'Entrata' else "🔴"
            css_class = "text-entrata" if row['Tipo'] == 'Entrata' else "text-uscita"
            segno = "+" if row['Tipo'] == 'Entrata' else "-"
            st.markdown(f"""
            <div class="card-movimento">
                <div>
                    <p style="margin:0; font-size:12px; color:#888;">{row['Data']} • {row['Conto']} • {row['Categoria']}</p>
                    <p style="margin:0; font-size:16px; font-weight:600; color:#333;">{icona} {row['Descrizione']}</p>
                </div>
                <div class="{css_class}">{segno}{pd.to_numeric(row['Importo']):.2f}€</div>
            </div>
            """, unsafe_allow_html=True)

# ==========================================
# 2. NUOVO MOVIMENTO
# ==========================================
elif sezione == "Nuovo Movimento 💸":
    st.title("Aggiungi Transazione")
    with st.form("form_movimenti", clear_on_submit=True):
        tipo = st.selectbox("Tipo", ["Uscita", "Entrata"])
        importo = st.number_input("Importo (€)", min_value=0.01, format="%.2f")
        conto = st.selectbox("Conto", df_conti['Nome'].tolist())
        categoria = st.selectbox("Categoria", ["Spesa", "Casa", "Svago", "Auto", "Stipendio", "Risparmio", "Altro"])
        descrizione = st.text_input("Descrizione")
        
        if st.form_submit_button("Registra"):
            nuova_riga = pd.DataFrame([{"Data": datetime.now().strftime("%Y-%m-%d"), "Conto": conto, "Tipo": tipo, "Categoria": categoria, "Importo": importo, "Descrizione": descrizione}])
            df_aggiornato = pd.concat([df_movimenti, nuova_riga], ignore_index=True)
            conn.update(worksheet="Movimenti", data=df_aggiornato)
            st.success("Transazione salvata!")
            st.rerun()

# ==========================================
# 3. I MIEI CONTI
# ==========================================
elif sezione == "I Miei Conti 🏦":
    st.title("Gestione Conti")
    for nome, dati in saldature_conti.items():
        st.markdown(f"""
        <div style="padding:15px; border-radius:10px; background:#f8f9fa; border-left: 5px solid #2a5298; margin-bottom:10px;">
            <h4 style="margin:0; color:#333;">{nome}</h4>
            <p style="margin:0; color:#555;">Saldo: <b>{dati['saldo']:.2f} €</b> (Tesoretto: {dati['tesoretto']} €)</p>
        </div>
        """, unsafe_allow_html=True)
        
    st.divider()
    with st.form("form_conti"):
        st.write("Aggiungi un nuovo conto")
        nome = st.text_input("Nome Conto")
        saldo = st.number_input("Saldo Iniziale", min_value=0.0, format="%.2f")
        tesoretto = st.number_input("Tesoretto Intoccabile", min_value=0.0, format="%.2f")
        if st.form_submit_button("Crea"):
            conn.update(worksheet="Conti", data=pd.concat([df_conti, pd.DataFrame([{"Nome": nome, "Saldo_Iniziale": saldo, "Tesoretto": tesoretto}])], ignore_index=True))
            st.rerun()

# ==========================================
# 4. ABBONAMENTI
# ==========================================
elif sezione == "Abbonamenti 🔁":
    st.title("Spese Fisse")
    if not df_abbonamenti.empty:
        totale_mensile = pd.to_numeric(df_abbonamenti['Costo_Mensile']).sum()
        st.warning(f"💸 Le tue spese fisse ammontano a **{totale_mensile:.2f} €** al mese.")
        for _, row in df_abbonamenti.iterrows():
            st.markdown(f"""
            <div class="card-movimento">
                <div>
                    <p style="margin:0; font-size:16px; font-weight:600; color:#333;">🔄 {row['Nome']}</p>
                    <p style="margin:0; font-size:12px; color:#888;">{row['Categoria']} • Rinnovo: {row['Data_Rinnovo']}</p>
                </div>
                <div class="text-uscita">-{pd.to_numeric(row['Costo_Mensile']):.2f}€ / mese</div>
            </div>
            """, unsafe_allow_html=True)
            
    with st.form("form_abbonamenti"):
        st.write("Aggiungi abbonamento")
        nome = st.text_input("Servizio (es. Netflix)")
        costo = st.number_input("Costo Mensile", min_value=0.01, format="%.2f")
        categoria = st.selectbox("Categoria", ["Svago", "Casa", "Lavoro", "Altro"])
        rinnovo = st.text_input("Giorno del mese (es. 15)")
        if st.form_submit_button("Aggiungi"):
            conn.update(worksheet="Abbonamenti", data=pd.concat([df_abbonamenti, pd.DataFrame([{"Nome": nome, "Costo_Mensile": costo, "Categoria": categoria, "Data_Rinnovo": rinnovo}])], ignore_index=True))
            st.rerun()

# ==========================================
# 5. WISHLIST & ACQUISTO
# ==========================================
elif sezione == "Wishlist 🎁":
    st.title("Lista dei Desideri")
    conto_risparmio = st.selectbox("Da quale conto paghi?", df_conti['Nome'].tolist())
    
    if conto_risparmio in saldature_conti:
        disponibile = saldature_conti[conto_risparmio]['saldo'] - saldature_conti[conto_risparmio]['tesoretto']
        st.info(f"Budget Extra (oltre il tesoretto): **{disponibile:.2f} €**")
        
        if not df_wishlist.empty:
            da_comprare = df_wishlist[df_wishlist['Stato'] == 'Da comprare']
            
            for idx, row in da_comprare.iterrows():
                costo = pd.to_numeric(row['Costo'])
                puo_permettersi = costo <= disponibile
                
                col1, col2 = st.columns([3, 1])
                col1.markdown(f"**{row['Oggetto']}** ({costo:.2f} €)")
                
                if puo_permettersi:
                    col1.success("✨ Puoi permettertelo!")
                    # Bottone per comprare e scalare i soldi
                    if col2.button("Acquista", key=f"buy_{idx}"):
                        # 1. Cambia stato wishlist
                        df_wishlist.at[idx, 'Stato'] = 'Acquistato'
                        conn.update(worksheet="Wishlist", data=df_wishlist)
                        
                        # 2. Registra l'uscita automatica
                        nuova_spesa = pd.DataFrame([{"Data": datetime.now().strftime("%Y-%m-%d"), "Conto": conto_risparmio, "Tipo": "Uscita", "Categoria": "Svago", "Importo": costo, "Descrizione": f"Acquisto Wishlist: {row['Oggetto']}"}])
                        conn.update(worksheet="Movimenti", data=pd.concat([df_movimenti, nuova_spesa], ignore_index=True))
                        
                        st.balloons() # Animazione festeggiamento
                        st.rerun()
                else:
                    col1.error(f"Mancano {costo - disponibile:.2f} €")
                    
    st.divider()
    with st.form("form_wishlist"):
        st.write("Aggiungi Obiettivo")
        oggetto = st.text_input("Oggetto")
        costo = st.number_input("Costo", min_value=1.0)
        if st.form_submit_button("Aggiungi"):
            conn.update(worksheet="Wishlist", data=pd.concat([df_wishlist, pd.DataFrame([{"Oggetto": oggetto, "Costo": costo, "Stato": "Da comprare"}])], ignore_index=True))
            st.rerun()
