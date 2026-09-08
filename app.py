import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import plotly.express as px

# --- CONFIGURAZIONE ---
st.set_page_config(page_title="Le mie Finanze", page_icon="💸", layout="centered", initial_sidebar_state="collapsed")

# --- CSS HACKS PER STILE APP NATIVA ---
st.markdown("""
<style>
    header {visibility: hidden;}
    .banner-gradient {
        background: linear-gradient(180deg, #69E2FF 0%, #5E9BFF 100%);
        padding: 50px 20px 30px 20px; text-align: center;
        border-bottom-left-radius: 35px; border-bottom-right-radius: 35px;
        margin-top: -6rem; margin-left: -1.25rem; margin-right: -1.25rem; margin-bottom: 25px;
    }
    .banner-title { color: rgba(255,255,255,0.7); font-size: 14px; margin-bottom: 5px; font-weight: 500;}
    .banner-amount { color: white; font-size: 42px; font-weight: 700; margin: 0; }
    .banner-buttons { display: flex; justify-content: center; gap: 15px; margin-top: 20px; }
    .banner-btn { 
        background: rgba(255,255,255,0.25); border-radius: 12px; width: 45px; height: 35px; 
        display: flex; align-items: center; justify-content: center; backdrop-filter: blur(5px); color: white; font-size: 18px;
    }
    .section-title { font-size: 20px; font-weight: 700; color: #1e1e1e; text-align: center; margin-bottom: 15px; }
    .tx-item { display: flex; justify-content: space-between; align-items: center; padding: 12px 10px; margin-bottom: 8px; }
    .tx-left { display: flex; align-items: center; gap: 15px; }
    .tx-icon-box { width: 45px; height: 45px; border-radius: 14px; display: flex; align-items: center; justify-content: center; font-size: 20px; color: white; }
    .tx-title { margin: 0; font-size: 15px; font-weight: 600; color: #333; }
    .tx-date { margin: 0; font-size: 12px; color: #a1a1aa; }
    .tx-right { text-align: right; }
    .tx-amount-out { margin: 0; font-size: 16px; font-weight: 700; color: #ff4b6a; }
    .tx-amount-in { margin: 0; font-size: 16px; font-weight: 700; color: #00d287; }
    .tx-balance { margin: 0; font-size: 11px; color: #a1a1aa; }
    .analytic-card { background: linear-gradient(135deg, #69E2FF 0%, #5E9BFF 100%); border-radius: 20px; padding: 20px; color: white; margin-bottom: 15px; }
    .analytic-card-title { font-size: 12px; opacity: 0.8; margin-bottom: 5px; }
    .analytic-card-amount { font-size: 24px; font-weight: 700; margin: 0; }
</style>
""", unsafe_allow_html=True)

cat_styles = {
    "Spesa": ("linear-gradient(135deg, #a18cd1 0%, #fbc2eb 100%)", "🛍️"),
    "Casa": ("linear-gradient(135deg, #f6d365 0%, #fda085 100%)", "🏠"),
    "Svago": ("linear-gradient(135deg, #84fab0 0%, #8fd3f4 100%)", "🛜"), 
    "Auto": ("linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%)", "🚗"), 
    "Stipendio": ("linear-gradient(135deg, #fbc2eb 0%, #a6c1ee 100%)", "🖥️"),
    "Risparmio": ("linear-gradient(135deg, #84fab0 0%, #8fd3f4 100%)", "💰"),
    "Altro": ("linear-gradient(135deg, #e0c3fc 0%, #8ec5fc 100%)", "✨"),
}

# --- CONNESSIONE E LETTURA DATI ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=5)
def get_data(worksheet):
    df = conn.read(worksheet=worksheet)
    return df.dropna(how="all")

try:
    df_movimenti = get_data("Movimenti")
    df_conti = get_data("Conti")
    df_wishlist = get_data("Wishlist")
except Exception as e:
    st.error("Errore di connessione. Verifica che i fogli Movimenti, Conti e Wishlist esistano.")
    st.stop()

# --- CALCOLO SALDI GLOBALI E PER CONTO ---
saldature_conti = {}
if not df_conti.empty:
    for index, row_conto in df_conti.iterrows():
        nome = row_conto['Nome']
        saldo_iniziale = pd.to_numeric(row_conto['Saldo_Iniziale'])
        tesoretto = pd.to_numeric(row_conto['Tesoretto'])
        
        entrate = 0
        uscite = 0
        if not df_movimenti.empty:
            mov_conto = df_movimenti[df_movimenti['Conto'] == nome]
            entrate = pd.to_numeric(mov_conto[mov_conto['Tipo'] == 'Entrata']['Importo']).sum()
            uscite = pd.to_numeric(mov_conto[mov_conto['Tipo'] == 'Uscita']['Importo']).sum()
        
        saldo_attuale = saldo_iniziale + entrate - uscite
        saldature_conti[nome] = {"saldo": saldo_attuale, "tesoretto": tesoretto}

totale_disponibile = sum(c['saldo'] for c in saldature_conti.values()) if saldature_conti else 0.0
totale_entrate = pd.to_numeric(df_movimenti[df_movimenti['Tipo'] == 'Entrata']['Importo']).sum() if not df_movimenti.empty else 0
totale_uscite = pd.to_numeric(df_movimenti[df_movimenti['Tipo'] == 'Uscita']['Importo']).sum() if not df_movimenti.empty else 0

# --- MENU LATERALE ---
sezione = st.sidebar.radio("Menu Finanze", ["Dashboard", "Analytics", "Nuovo Movimento", "Conti", "Wishlist"])

# ==========================================
# 1. DASHBOARD
# ==========================================
if sezione == "Dashboard":
    st.markdown(f"""
    <div class="banner-gradient">
        <p class="banner-title">Current Balance</p>
        <p class="banner-amount">€ {totale_disponibile:,.2f}</p>
        <div class="banner-buttons">
            <div class="banner-btn"><span>▲</span></div>
            <div class="banner-btn"><span>▼</span></div>
        </div>
    </div>
    <div class="section-title">Transactions</div>
    """, unsafe_allow_html=True)
    
    if not df_movimenti.empty:
        ultimi = df_movimenti.tail(15).iloc[::-1]
        for _, row in ultimi.iterrows():
            tipo, cat = row['Tipo'], row['Categoria']
            importo = pd.to_numeric(row['Importo'])
            bg_grad, icon = cat_styles.get(cat, cat_styles["Altro"])
            amount_class = "tx-amount-in" if tipo == 'Entrata' else "tx-amount-out"
            segno = "+" if tipo == 'Entrata' else "-"
            
            st.markdown(f"""
            <div class="tx-item">
                <div class="tx-left">
                    <div class="tx-icon-box" style="background: {bg_grad};">{icon}</div>
                    <div><p class="tx-title">{row['Descrizione']}</p><p class="tx-date">{row['Data']}</p></div>
                </div>
                <div class="tx-right">
                    <p class="{amount_class}">{segno}{importo:,.2f}</p>
                    <p class="tx-balance">{cat}</p>
                </div>
            </div>
            """, unsafe_allow_html=True)

# ==========================================
# 2. ANALYTICS
# ==========================================
elif sezione == "Analytics":
    st.markdown("<h2 style='text-align: center; color: #1e1e1e; margin-bottom: 20px;'>Analytics</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #69E2FF; font-weight: bold; margin-bottom: 10px;'>Overview</p>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f'<div class="analytic-card"><p class="analytic-card-title">▲ Income</p><p class="analytic-card-amount">€ {totale_entrate:,.2f}</p></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="analytic-card"><p class="analytic-card-title">▼ Expenses</p><p class="analytic-card-amount">€ {totale_uscite:,.2f}</p></div>', unsafe_allow_html=True)
        
    st.markdown("<p style='color: #69E2FF; font-weight: bold; margin-top: 20px;'>Income & Spending</p>", unsafe_allow_html=True)
    if not df_movimenti.empty:
        df_chart = df_movimenti.copy()
        df_chart['Importo'] = pd.to_numeric(df_chart['Importo'])
        df_grouped = df_chart.groupby(['Data', 'Tipo'])['Importo'].sum().reset_index()
        fig = px.bar(df_grouped, x='Data', y='Importo', color='Tipo', barmode='group', color_discrete_map={'Entrata': '#84fab0', 'Uscita': '#5E9BFF'})
        fig.update_layout(plot_bgcolor='white', paper_bgcolor='white', margin=dict(l=0, r=0, t=0, b=0), xaxis=dict(showgrid=False, title=""), yaxis=dict(showgrid=True, gridcolor='#f0f0f0', title=""), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

# ==========================================
# 3. NUOVO MOVIMENTO
# ==========================================
elif sezione == "Nuovo Movimento":
    st.markdown("<br><h2 style='text-align:center;'>Aggiungi Transazione</h2>", unsafe_allow_html=True)
    with st.form("form_movimenti", clear_on_submit=True):
        tipo = st.selectbox("Tipo", ["Uscita", "Entrata"])
        importo = st.number_input("Importo (€)", min_value=0.01, format="%.2f")
        conto = st.selectbox("Conto", df_conti['Nome'].tolist() if not df_conti.empty else [])
        categoria = st.selectbox("Categoria", list(cat_styles.keys()))
        descrizione = st.text_input("Descrizione")
        data_mov = st.date_input("Data")
        
        if st.form_submit_button("Registra Movimento", use_container_width=True):
            nuova_riga = pd.DataFrame([{"Data": data_mov.strftime("%Y-%m-%d"), "Conto": conto, "Tipo": tipo, "Categoria": categoria, "Importo": importo, "Descrizione": descrizione}])
            conn.update(worksheet="Movimenti", data=pd.concat([df_movimenti, nuova_riga], ignore_index=True))
            st.success("Transazione salvata!")
            st.cache_data.clear()
            st.rerun()

# ==========================================
# 4. CONTI
# ==========================================
elif sezione == "Conti":
    st.markdown("<br><h2 style='text-align:center;'>I Miei Conti</h2>", unsafe_allow_html=True)
    
    # Mostra la lista dei conti esistenti con le card blu!
    if saldature_conti:
        for nome, dati in saldature_conti.items():
            st.markdown(f"""
            <div class="analytic-card" style="margin-bottom: 10px;">
                <p class="analytic-card-title">{nome}</p>
                <p class="analytic-card-amount">€ {dati['saldo']:,.2f}</p>
                <p style="margin:0; margin-top: 5px; font-size:12px; color:rgba(255,255,255,0.7);">Tesoretto intoccabile: € {dati['tesoretto']:,.2f}</p>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Nessun conto esistente. Creane uno qui sotto!")

    st.divider()
    
    with st.form("form_conti", clear_on_submit=True):
        st.write("**Crea un nuovo conto**")
        nome = st.text_input("Nome Conto")
        saldo = st.number_input("Saldo Iniziale", min_value=0.0, format="%.2f")
        tesoretto = st.number_input("Tesoretto Intoccabile", min_value=0.0, format="%.2f")
        if st.form_submit_button("Crea Conto", use_container_width=True):
            conn.update(worksheet="Conti", data=pd.concat([df_conti, pd.DataFrame([{"Nome": nome, "Saldo_Iniziale": saldo, "Tesoretto": tesoretto}])], ignore_index=True))
            st.success("Conto aggiunto!")
            st.cache_data.clear()
            st.rerun()

# ==========================================
# 5. WISHLIST E RISPARMI
# ==========================================
elif sezione == "Wishlist":
    st.markdown("<br><h2 style='text-align:center;'>Wishlist & Risparmi</h2>", unsafe_allow_html=True)
    
    if df_conti.empty:
        st.warning("Crea un conto per gestire la wishlist.")
    else:
        conto_risparmio = st.selectbox("Da quale conto paghi i tuoi sfizi?", df_conti['Nome'].tolist())
        
        if conto_risparmio in saldature_conti:
            disponibile = saldature_conti[conto_risparmio]['saldo'] - saldature_conti[conto_risparmio]['tesoretto']
            st.info(f"Budget Extra (oltre il tesoretto intoccabile): **€ {disponibile:,.2f}**")
            
            if not df_wishlist.empty:
                da_comprare = df_wishlist[df_wishlist['Stato'] == 'Da comprare']
                
                for idx, row in da_comprare.iterrows():
                    costo = pd.to_numeric(row['Costo'])
                    puo_permettersi = costo <= disponibile
                    
                    st.markdown(f"**{row['Oggetto']}** - € {costo:,.2f}")
                    if puo_permettersi:
                        if st.button(f"Acquista '{row['Oggetto']}'", key=f"buy_{idx}", type="primary"):
                            df_wishlist.at[idx, 'Stato'] = 'Acquistato'
                            conn.update(worksheet="Wishlist", data=df_wishlist)
                            nuova_spesa = pd.DataFrame([{"Data": datetime.now().strftime("%Y-%m-%d"), "Conto": conto_risparmio, "Tipo": "Uscita", "Categoria": "Svago", "Importo": costo, "Descrizione": f"Acquisto: {row['Oggetto']}"}])
                            conn.update(worksheet="Movimenti", data=pd.concat([df_movimenti, nuova_spesa], ignore_index=True))
                            st.balloons()
                            st.cache_data.clear()
                            st.rerun()
                    else:
                        st.error(f"Ti mancano € {(costo - disponibile):,.2f}")
                    st.write("---")
                        
        with st.form("form_wishlist", clear_on_submit=True):
            st.write("**Aggiungi un nuovo Obiettivo**")
            oggetto = st.text_input("Cosa vuoi comprare?")
            costo = st.number_input("Costo", min_value=1.0)
            if st.form_submit_button("Aggiungi", use_container_width=True):
                conn.update(worksheet="Wishlist", data=pd.concat([df_wishlist, pd.DataFrame([{"Oggetto": oggetto, "Costo": costo, "Stato": "Da comprare"}])], ignore_index=True))
                st.success("Aggiunto alla Wishlist!")
                st.cache_data.clear()
                st.rerun()
