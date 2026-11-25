import streamlit as st
import pandas as pd
import json
import base64
import tempfile
import os
from datetime import datetime, date, timedelta
from fpdf import FPDF
from PIL import Image

# --- CONFIGURAZIONE PAGINA (SIDEBAR CHIUSA) ---
st.set_page_config(
    page_title="Easy Gest - Gestionale Ditta Individuale",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CSS: NASCONDE SIDEBAR + STILE PULSANTI QUADRATI COLORATI ---
st.markdown("""
    <style>
    [data-testid="stSidebar"] {display: none !important;}
    [data-testid="stSidebarCollapsedControl"] {display: none !important;}
    [data-testid="collapsedControl"] {display: none !important;}

    .main {background-color: #f8f9fa;}
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
    }

    /* Pulsanti grandi quadrati della schermata iniziale */
    [class*="st-key-tile_"] button {
        height: 170px !important;
        width: 100% !important;
        border-radius: 16px !important;
        border: none !important;
        color: #ffffff !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: center !important;
        text-align: center !important;
        white-space: pre-wrap !important;
        padding: 14px !important;
        box-shadow: 0 6px 14px rgba(15, 23, 42, 0.14) !important;
        transition: transform 0.15s ease, box-shadow 0.15s ease !important;
    }

    [class*="st-key-tile_"] button:hover {
        transform: translateY(-3px) !important;
        box-shadow: 0 10px 20px rgba(15, 23, 42, 0.22) !important;
    }

    /* Dicitura sotto l'icona */
    [class*="st-key-tile_"] button p {
        font-size: 1.05rem !important;
        font-weight: 800 !important;
        line-height: 1.25 !important;
        margin: 0 !important;
    }

    /* Icona grande al centro */
    [class*="st-key-tile_"] button p::first-line {
        font-size: 4.8rem !important;
        line-height: 2.4 !important;
    }

    /* Colori distinti per ciascuno degli 8 pulsanti */
    .st-key-tile_1 button { background: linear-gradient(135deg, #1e3a8a, #2563eb) !important; }
    .st-key-tile_2 button { background: linear-gradient(135deg, #0f766e, #14b8a6) !important; }
    .st-key-tile_3 button { background: linear-gradient(135deg, #b45309, #f59e0b) !important; }
    .st-key-tile_4 button { background: linear-gradient(135deg, #5b21b6, #8b5cf6) !important; }
    .st-key-tile_5 button { background: linear-gradient(135deg, #15803d, #22c55e) !important; }
    .st-key-tile_6 button { background: linear-gradient(135deg, #be123c, #f43f5e) !important; }
    .st-key-tile_7 button { background: linear-gradient(135deg, #0369a1, #0ea5e9) !important; }
    .st-key-tile_8 button { background: linear-gradient(135deg, #334155, #64748b) !important; }

    .storico-box {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 14px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 3px 10px rgba(15, 23, 42, 0.05);
        margin-top: 12px;
    }
    </style>
""", unsafe_allow_html=True)

# --- INIZIALIZZAZIONE STATO ---
def init_db():
    if "pagina_attiva" not in st.session_state:
        st.session_state.pagina_attiva = "home"
    if "db" not in st.session_state:
        st.session_state.db = {
            "ditta": {
                "denominazione": "BLINDA 2000",
                "titolare": "Persi Luigi",
                "indirizzo": "Via di Torre Spaccata 149 A",
                "cap_citta": "00169 - Roma",
                "piva": "10416520582",
                "cf": "PRSLGU72C11H501T",
                "regime": "Regime Ordinario / Semplificato (con IVA)",
                "iban": "IT83Q0760103200001053005003",
                "pec": "",
                "telefono": "tel 06/263011 cell 3924532719 - 388/9339564",
                "logo_b64": ""
            },
            "clienti": [],
            "fornitori": [],
            "magazzino": [],
            "fatture_attive": [],
            "fatture_passive": [],
            "preventivi": []
        }

init_db()
db = st.session_state.db

def vai_a(sezione):
    st.session_state.pagina_attiva = sezione
    st.rerun()

def fmt_eur(val):
    if val is None or val == 0:
        return "-"
    return f"{val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# --- FUNZIONE GENERAZIONE PDF SU SCHEMA ALLEGATO ---
def genera_pdf_documento(tipo_doc, doc_data, ditta_data):
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.add_page()
    pdf.set_auto_page_break(auto=False)

    x0 = 15
    y0 = 15
    w_tot = 180

    blu_logo = (25, 65, 120)
    grigio_banda = (135, 138, 142)
    nero = (20, 20, 20)

    # 1. Riquadro superiore: Logo SX | Spettabile DX
    h_top = 46
    w_sx_top = 68
    w_dx_top = w_tot - w_sx_top

    pdf.set_draw_color(0, 0, 0)
    pdf.set_line_width(0.35)
    pdf.rect(x0, y0, w_sx_top, h_top)
    pdf.rect(x0 + w_sx_top, y0, w_dx_top, h_top)

    logo_b64 = ditta_data.get("logo_b64", "")
    if logo_b64:
        try:
            img_bytes = base64.b64decode(logo_b64)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_img:
                tmp_img.write(img_bytes)
                tmp_path = tmp_img.name
            pdf.image(tmp_path, x=x0 + 6, y=y0 + 3, w=w_sx_top - 12, h=h_top - 6, keep_aspect_ratio=True)
            os.remove(tmp_path)
        except Exception:
            pass
    else:
        pdf.set_xy(x0 + 2, y0 + 14)
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(*blu_logo)
        pdf.cell(w_sx_top - 4, 7, ditta_data.get("denominazione", "").upper(), align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.set_x(x0 + 2)
        pdf.set_fill_color(45, 95, 155)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Times", "BI", 12)
        pdf.cell(w_sx_top - 4, 8, f"di {ditta_data.get('titolare', '')}", align="C", fill=True)

    x_spett = x0 + w_sx_top + 2
    x_val = x0 + w_sx_top + 48
    pdf.set_text_color(*nero)

    pdf.set_xy(x_spett, y0 + 11)
    pdf.set_font("Times", "", 10)
    pdf.cell(44, 5, "Spettabile")
    pdf.set_xy(x_val, y0 + 11)
    pdf.set_font("Helvetica", "B", 9.5)
    pdf.cell(62, 5, doc_data.get("cliente_nome", ""))

    pdf.set_xy(x_spett, y0 + 21)
    pdf.set_font("Times", "", 10)
    pdf.cell(44, 5, "via")
    pdf.set_xy(x_val, y0 + 21)
    pdf.set_font("Times", "", 10)
    pdf.cell(62, 5, doc_data.get("cliente_indirizzo", ""))

    pdf.set_xy(x_spett, y0 + 26)
    pdf.cell(44, 5, "cap:")
    pdf.set_xy(x_val, y0 + 26)
    pdf.cell(62, 5, doc_data.get("cliente_cap", ""))

    pdf.set_xy(x_val, y0 + 31)
    pdf.cell(62, 5, doc_data.get("cliente_citta", ""))

    pdf.set_xy(x_spett, y0 + 36)
    pdf.cell(44, 5, "cod fiscale")
    pdf.set_xy(x_val, y0 + 36)
    pdf.cell(62, 5, doc_data.get("cliente_piva", ""))

    pdf.set_xy(x_spett, y0 + 41)
    pdf.cell(44, 5, "sdi")
    pdf.set_xy(x_val, y0 + 41)
    pdf.cell(62, 5, doc_data.get("cliente_sdi", ""))

    # 2. Riga metadati
    y1 = y0 + h_top
    h_meta = 12
    w_c1 = 55
    w_c2 = 55
    w_c3 = w_tot - w_c1 - w_c2

    pdf.rect(x0, y1, w_c1, h_meta)
    pdf.rect(x0 + w_c1, y1, w_c2, h_meta)
    pdf.rect(x0 + w_c1 + w_c2, y1, w_c3, h_meta)

    pdf.set_font("Times", "B", 10)
    pdf.set_xy(x0 + 1.5, y1 + 1)
    pdf.cell(w_c1 - 3, 4.5, "data fattura" if tipo_doc == "Fattura" else "data preventivo")
    pdf.set_xy(x0 + w_c1, y1 + 1)
    pdf.cell(w_c2, 4.5, tipo_doc.upper(), align="C")
    pdf.set_xy(x0 + w_c1 + w_c2 + 1.5, y1 + 1)
    pdf.cell(w_c3 - 3, 4.5, "RIFERIMENTO OFFERTA")

    pdf.set_font("Times", "", 10.5)
    pdf.set_xy(x0, y1 + 6.5)
    pdf.cell(w_c1, 5, doc_data.get("data", ""), align="C")
    pdf.set_xy(x0 + w_c1, y1 + 6.5)
    pdf.cell(w_c2, 5, doc_data.get("numero", ""), align="C")
    pdf.set_xy(x0 + w_c1 + w_c2 + 1.5, y1 + 6.5)
    pdf.cell(w_c3 - 3, 5, doc_data.get("rif_offerta", ""), align="L")

    # 3. Riga regolamento e IBAN
    y2 = y1 + h_meta
    h_pag = 15
    w_pag_sx = 92
    w_pag_dx = w_tot - w_pag_sx

    pdf.rect(x0, y2, w_pag_sx, h_pag)
    pdf.rect(x0 + w_pag_sx, y2, w_pag_dx, h_pag)

    pdf.set_font("Times", "B", 10)
    pdf.set_xy(x0 + 1.5, y2 + 1)
    pdf.cell(w_pag_sx - 3, 4.5, "Regolamento")
    pdf.set_font("Times", "", 10)
    pdf.set_xy(x0 + 1.5, y2 + 9.5)
    pdf.cell(w_pag_sx - 3, 4.5, doc_data.get("pagamento", "rimessa diretta"))

    pdf.set_font("Times", "B", 9.5)
    pdf.set_xy(x0 + w_pag_sx + 1.5, y2 + 1)
    pdf.cell(w_pag_dx - 3, 4.5, "bonifico intestato a:")
    pdf.set_xy(x0 + w_pag_sx + 1.5, y2 + 5.5)
    pdf.cell(w_pag_dx - 3, 4.5, ditta_data.get("titolare", ""))
    pdf.set_xy(x0 + w_pag_sx + 1.5, y2 + 10)
    pdf.cell(w_pag_dx - 3, 4.5, f"IBAN: {ditta_data.get('iban', '')}")

    # 4. Fascia grigia + intestazione tabella q.tà / descrizione
    y3 = y2 + h_pag
    h_banda1 = 4.5
    pdf.set_fill_color(*grigio_banda)
    pdf.rect(x0, y3, w_tot, h_banda1, "DF")

    y4 = y3 + h_banda1
    h_th = 5.5
    w_qta = 12
    w_desc = w_tot - w_qta
    pdf.rect(x0, y4, w_qta, h_th)
    pdf.rect(x0 + w_qta, y4, w_desc, h_th)

    pdf.set_font("Times", "", 9.5)
    pdf.set_xy(x0, y4 + 0.5)
    pdf.cell(w_qta, 4.5, "q.tà", align="C")
    pdf.set_xy(x0 + w_qta, y4 + 0.5)
    pdf.cell(w_desc, 4.5, "descrizione", align="C")

    # 5. Corpo centrale descrizione
    y5 = y4 + h_th
    h_body = 104
    pdf.rect(x0, y5, w_qta, h_body)
    pdf.rect(x0 + w_qta, y5, w_desc, h_body)

    pdf.set_font("Times", "B", 9.5)
    pdf.set_xy(x0 + w_qta + 1.5, y5 + 4)
    frase_intro = doc_data.get("intestazione_corpo", "Vi rimettiamo regolare fattura per :" if tipo_doc == "Fattura" else "Vi rimettiamo nostra migliore offerta per :")
    pdf.cell(w_desc - 3, 5, frase_intro)

    curr_y = y5 + 16
    pdf.set_font("Helvetica", "B", 9)
    for r in doc_data.get("righe", []):
        if curr_y > y5 + h_body - 16:
            break
        qta_val = r.get("qta", 0)
        if qta_val and qta_val > 0:
            pdf.set_xy(x0, curr_y)
            q_str = f"{int(qta_val)}" if float(qta_val).is_integer() else f"{qta_val:.2f}"
            pdf.cell(w_qta, 5, q_str, align="C")
        pdf.set_xy(x0 + w_qta + 1.5, curr_y)
        pdf.cell(w_desc - 3, 5, r.get("descrizione", ""))
        curr_y += 5.2

    dicitura_finale = doc_data.get("note", "saldo")
    if dicitura_finale:
        pdf.set_font("Times", "B", 9.5)
        pdf.set_xy(x0 + w_qta + 1.5, y5 + 58)
        pdf.cell(w_desc - 3, 5, dicitura_finale)

    # 6. Fascia grigia inferiore + riepilogo fiscale
    y6 = y5 + h_body
    h_banda2 = 7
    pdf.set_fill_color(*grigio_banda)
    pdf.rect(x0, y6, w_tot, h_banda2, "DF")

    y7 = y6 + h_banda2
    h_tot_hdr = 5.5
    h_tot_body = 16.5
    w_t1 = 48
    w_t2 = 46
    w_t3 = w_tot - w_t1 - w_t2

    pdf.rect(x0, y7, w_t1, h_tot_hdr)
    pdf.rect(x0 + w_t1, y7, w_t2, h_tot_hdr)
    pdf.rect(x0 + w_t1 + w_t2, y7, w_t3, h_tot_hdr)

    pdf.set_font("Times", "B", 10)
    pdf.set_xy(x0, y7 + 0.5)
    pdf.cell(w_t1, 4.5, "Imponibile", align="C")
    pdf.set_xy(x0 + w_t1 + 1.5, y7 + 0.5)
    pdf.cell(w_t2 - 3, 4.5, "IVA", align="L")
    pdf.set_xy(x0 + w_t1 + w_t2, y7 + 0.5)
    pdf.cell(w_t3, 4.5, "totale fattura" if tipo_doc == "Fattura" else "totale preventivo", align="C")

    y8 = y7 + h_tot_hdr
    pdf.rect(x0, y8, w_t1, h_tot_body)
    pdf.rect(x0 + w_t1, y8, w_t2, h_tot_body)
    pdf.rect(x0 + w_t1 + w_t2, y8, w_t3, h_tot_body)

    imp_4 = doc_data.get("imp_4", 0.0)
    iva_4 = doc_data.get("iva_4", 0.0)
    tot_4 = imp_4 + iva_4

    imp_std = doc_data.get("imp_std", 0.0)
    aliq_std = doc_data.get("aliq_std", 10)
    iva_std = doc_data.get("iva_std", 0.0)
    tot_std = imp_std + iva_std

    rit_perc = doc_data.get("rit_perc", 0.0)
    rit_imp = doc_data.get("rit_imp", 0.0)
    totale_finale = doc_data.get("totale", 0.0)

    pdf.set_font("Times", "", 9.5)
    pdf.set_xy(x0 + 14, y8 + 0.8)
    pdf.cell(6, 4.8, "€")
    pdf.cell(26, 4.8, fmt_eur(imp_4), align="R")

    pdf.set_xy(x0 + w_t1 + 1.5, y8 + 0.8)
    pdf.cell(18, 4.8, "iva 4%")
    pdf.cell(6, 4.8, "€")
    pdf.cell(19, 4.8, fmt_eur(iva_4), align="R")

    pdf.set_xy(x0 + w_t1 + w_t2 + 24, y8 + 0.8)
    pdf.cell(6, 4.8, "€")
    pdf.cell(52, 4.8, fmt_eur(tot_4), align="R")

    pdf.set_xy(x0 + 14, y8 + 5.8)
    pdf.cell(6, 4.8, "€")
    pdf.cell(26, 4.8, fmt_eur(imp_std), align="R")

    pdf.set_xy(x0 + w_t1 + 1.5, y8 + 5.8)
    pdf.cell(18, 4.8, f"iva {aliq_std}%")
    pdf.cell(6, 4.8, "€")
    pdf.cell(19, 4.8, fmt_eur(iva_std), align="R")

    pdf.set_xy(x0 + w_t1 + w_t2 + 24, y8 + 5.8)
    pdf.cell(6, 4.8, "€")
    pdf.cell(52, 4.8, fmt_eur(tot_std), align="R")

    pdf.set_xy(x0 + 14, y8 + 10.8)
    pdf.cell(32, 4.8, f"- RIT {int(rit_perc)}%" if rit_perc > 0 else "")

    pdf.set_xy(x0 + w_t1 + 19.5, y8 + 10.8)
    pdf.cell(6, 4.8, "€" if rit_imp > 0 else "")
    pdf.cell(19, 4.8, fmt_eur(rit_imp) if rit_imp > 0 else "", align="R")

    pdf.set_font("Times", "B", 10)
    pdf.set_xy(x0 + w_t1 + w_t2 + 24, y8 + 10.8)
    pdf.cell(6, 4.8, "€")
    pdf.cell(52, 4.8, fmt_eur(totale_finale), align="R")

    # 7. Piè di pagina riquadrato in basso a sinistra
    y9 = y8 + h_tot_body
    h_foot = 23
    w_foot = 112
    pdf.rect(x0, y9, w_foot, h_foot)

    pdf.set_font("Times", "B", 10)
    pdf.set_xy(x0 + 1.5, y9 + 1)
    pdf.cell(w_foot - 3, 4.5, ditta_data.get("titolare", ""))

    pdf.set_font("Times", "", 9.5)
    pdf.set_xy(x0 + 1.5, y9 + 5.5)
    pdf.cell(w_foot - 3, 4.2, ditta_data.get("indirizzo", ""))

    pdf.set_xy(x0 + 1.5, y9 + 9.7)
    pdf.cell(w_foot - 3, 4.2, ditta_data.get("cap_citta", ""))

    pdf.set_xy(x0 + 1.5, y9 + 13.9)
    pdf.cell(w_foot - 3, 4.2, f"P.IVA {ditta_data.get('piva', '')} cf {ditta_data.get('cf', '')}")

    pdf.set_xy(x0 + 1.5, y9 + 18.1)
    pdf.cell(w_foot - 3, 4.2, ditta_data.get("telefono", ""))

    return bytes(pdf.output())

# --- BARRA SUPERIORE NELLE SEZIONI INTERNE ---
if st.session_state.pagina_attiva != "home":
    top_l, top_c, top_r = st.columns([1.4, 3.6, 1.4])
    with top_l:
        if st.button("⬅️ Torna alla Home", key="btn_back_home"):
            vai_a("home")
    with top_c:
        st.caption(f"**{db['ditta'].get('denominazione', 'Ditta Individuale')}** — {db['ditta'].get('titolare', '')}")
    with top_r:
        json_str_top = json.dumps(db, indent=2, default=str)
        st.download_button(
            label="💾 Salva Storico (.json)",
            data=json_str_top,
            file_name=f"contabilita_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
            mime="application/json",
            key="dl_top_json"
        )
    st.divider()

# ==============================================================================
# SCHERMATA INIZIALE: PULSANTI GRANDI QUADRATI COLORATI + CARICAMENTO STORICO
# ==============================================================================
if st.session_state.pagina_attiva == "home":
    col_logo, col_titolo = st.columns([1.2, 6], vertical_alignment="center")
    with col_logo:
        if os.path.exists("logo_app.png"):
            st.image(Image.open("logo_app.png"), width=110)
    with col_titolo:
        st.title("Easy Gest")
        st.caption(
            f"{db['ditta'].get('denominazione', '')} — {db['ditta'].get('titolare', '')} | "
            "Gestione contabile Ditta Individuale"
        )

    riga1 = st.columns(4, gap="medium")
    with riga1[0]:
        if st.button("🏢\n\nDati Ditta Individuale", key="tile_1"):
            vai_a("ditta")
    with riga1[1]:
        if st.button("👥\n\nAnagrafica Clienti", key="tile_2"):
            vai_a("clienti")
    with riga1[2]:
        if st.button("🏭\n\nAnagrafica Fornitori", key="tile_3"):
            vai_a("fornitori")
    with riga1[3]:
        if st.button("📦\n\nMagazzino e Listino", key="tile_4"):
            vai_a("magazzino")

    st.write("")

    riga2 = st.columns(4, gap="medium")
    with riga2[0]:
        if st.button("🧾\n\nFatture Vendita", key="tile_5"):
            vai_a("fatture_attive")
    with riga2[1]:
        if st.button("📥\n\nFatture Acquisti", key="tile_6"):
            vai_a("fatture_passive")
    with riga2[2]:
        if st.button("📅\n\nScadenzario", key="tile_7"):
            vai_a("scadenzario")
    with riga2[3]:
        if st.button("📝\n\nPreventivi", key="tile_8"):
            vai_a("preventivi")

    st.write("")

    # Sezione Caricamento / Salvataggio File Storico posizionata sotto i pulsanti
    st.markdown('<div class="storico-box">', unsafe_allow_html=True)
    st.subheader("📂 Gestione File dello Storico (.json)")
    st.write("Carica un file dello storico salvato in precedenza oppure esporta una copia aggiornata dell'archivio corrente.")

    col_up, col_dl = st.columns([2.2, 1.2], gap="large")
    with col_up:
        uploaded_file = st.file_uploader("Carica file storico (.json)", type=["json"], key="home_uploader")
        if uploaded_file is not None:
            if st.button("✅ Carica e Ripristina Storico", key="btn_carica_storico", type="primary"):
                try:
                    loaded_data = json.load(uploaded_file)
                    st.session_state.db = loaded_data
                    st.success("Storico caricato con successo!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore durante il caricamento del file: {e}")

    with col_dl:
        st.write("")
        st.write("")
        json_str_home = json.dumps(db, indent=2, default=str)
        st.download_button(
            label="⬇️ Scarica Storico Attuale (.json)",
            data=json_str_home,
            file_name=f"contabilita_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
            mime="application/json",
            key="btn_scarica_storico"
        )
    st.markdown('</div>', unsafe_allow_html=True)

# ==============================================================================
# 1. DATI DITTA INDIVIDUALE
# ==============================================================================
elif st.session_state.pagina_attiva == "ditta":
    st.header("🏢 Dati Ditta Individuale & Intestazione Fattura")
    st.info("Questi dati popolano automaticamente il riquadro superiore sinistro, l'area IBAN e il riquadro piè di pagina dello schema fattura.")

    with st.form("form_ditta"):
        col1, col2 = st.columns(2)
        with col1:
            denominazione = st.text_input("Denominazione Ditta*", value=db["ditta"]["denominazione"])
            titolare = st.text_input("Nome e Cognome Titolare*", value=db["ditta"]["titolare"])
            piva = st.text_input("Partita IVA*", value=db["ditta"]["piva"])
            cf = st.text_input("Codice Fiscale*", value=db["ditta"]["cf"])
            regime = st.selectbox(
                "Regime Fiscale",
                ["Regime Ordinario / Semplificato (con IVA)", "Regime Forfettario (L. 190/2014)"],
                index=0 if "Ordinario" in db["ditta"]["regime"] else 1
            )
        with col2:
            indirizzo = st.text_input("Indirizzo (Via/Piazza)", value=db["ditta"]["indirizzo"])
            cap_citta = st.text_input("CAP e Città (es. 00169 - Roma)", value=db["ditta"]["cap_citta"])
            iban = st.text_input("IBAN per bonifici", value=db["ditta"]["iban"])
            telefono = st.text_input("Recapiti Telefonici (es. tel 06/... cell ...)", value=db["ditta"]["telefono"])
            pec = st.text_input("PEC / Email", value=db["ditta"]["pec"])

        st.subheader("🖼️ Logo Aziendale (Riquadro in alto a sinistra)")
        logo_file = st.file_uploader("Carica immagine Logo (PNG o JPG)", type=["png", "jpg", "jpeg"])

        if st.form_submit_button("💾 Salva Dati Ditta", type="primary"):
            logo_b64_val = db["ditta"].get("logo_b64", "")
            if logo_file is not None:
                logo_b64_val = base64.b64encode(logo_file.read()).decode("utf-8")

            db["ditta"] = {
                "denominazione": denominazione,
                "titolare": titolare,
                "indirizzo": indirizzo,
                "cap_citta": cap_citta,
                "piva": piva,
                "cf": cf,
                "regime": regime,
                "iban": iban,
                "pec": pec,
                "telefono": telefono,
                "logo_b64": logo_b64_val
            }
            st.success("Dati della Ditta Individuale salvati correttamente!")

# ==============================================================================
# 2. ANAGRAFICA CLIENTI
# ==============================================================================
elif st.session_state.pagina_attiva == "clienti":
    st.header("👥 Anagrafica Clienti")

    with st.expander("➕ Aggiungi Nuovo Cliente", expanded=len(db["clienti"]) == 0):
        with st.form("form_cliente", clear_on_submit=True):
            c1, c2 = st.columns(2)
            nome = c1.text_input("Spettabile / Ragione Sociale (es. condominio)*")
            indirizzo = c1.text_input("Via e Civico (es. Bruno Rizzieri 40/66)")
            cap = c1.text_input("CAP (es. 00173)")
            citta = c1.text_input("Città (es. Roma)")

            piva = c2.text_input("Codice Fiscale / Partita IVA*")
            sdi = c2.text_input("Codice SDI (es. JHBM40P)", value="0000000")
            pagamento_pref = c2.text_input("Regolamento Default", value="rimessa diretta")
            ritenuta_default = c2.checkbox("Cliente soggetto a Ritenuta d'Acconto 4% (es. Condominio)", value=True)

            if st.form_submit_button("Salva Cliente"):
                if nome:
                    db["clienti"].append({
                        "id": len(db["clienti"]) + 1,
                        "nome": nome,
                        "indirizzo": indirizzo,
                        "cap": cap,
                        "citta": citta,
                        "piva": piva,
                        "sdi": sdi,
                        "pagamento": pagamento_pref,
                        "ritenuta_4": ritenuta_default
                    })
                    st.success(f"Cliente '{nome}' aggiunto!")
                    st.rerun()
                else:
                    st.warning("Inserisci almeno la denominazione del cliente.")

    if db["clienti"]:
        st.dataframe(pd.DataFrame(db["clienti"]), use_container_width=True, hide_index=True)
    else:
        st.info("Nessun cliente in anagrafica.")

# ==============================================================================
# 3. ANAGRAFICA FORNITORI
# ==============================================================================
elif st.session_state.pagina_attiva == "fornitori":
    st.header("🏭 Anagrafica Fornitori")

    with st.expander("➕ Aggiungi Nuovo Fornitore", expanded=len(db["fornitori"]) == 0):
        with st.form("form_fornitore", clear_on_submit=True):
            c1, c2 = st.columns(2)
            nome = c1.text_input("Ragione Sociale Fornitore*")
            piva = c1.text_input("Partita IVA / Codice Fiscale*")
            categoria = c1.selectbox("Categoria Spesa", ["Materiali / Ferramenta / Ricambi", "Servizi / Consulenze", "Utenze / Affitti", "Carburante / Mezzi", "Attrezzature", "Altro"])
            indirizzo = c2.text_input("Indirizzo Completo")
            iban = c2.text_input("IBAN Fornitore")
            note = c2.text_input("Note / Contatti")

            if st.form_submit_button("Salva Fornitore"):
                if nome:
                    db["fornitori"].append({
                        "id": len(db["fornitori"]) + 1,
                        "nome": nome,
                        "piva": piva,
                        "categoria": categoria,
                        "indirizzo": indirizzo,
                        "iban": iban,
                        "note": note
                    })
                    st.success(f"Fornitore '{nome}' aggiunto!")
                    st.rerun()
                else:
                    st.warning("Inserisci la Ragione Sociale del fornitore.")

    if db["fornitori"]:
        st.dataframe(pd.DataFrame(db["fornitori"]), use_container_width=True, hide_index=True)
    else:
        st.info("Nessun fornitore in anagrafica.")

# ==============================================================================
# 4. MAGAZZINO
# ==============================================================================
elif st.session_state.pagina_attiva == "magazzino":
    st.header("📦 Gestione Magazzino & Listino Interventi")

    with st.expander("➕ Aggiungi Articolo / Prestazione", expanded=len(db["magazzino"]) == 0):
        with st.form("form_magazzino", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            codice = c1.text_input("Codice Articolo", value=f"ART-{len(db['magazzino'])+1:03d}")
            descrizione = c2.text_input("Descrizione Articolo / Intervento*")
            tipo = c3.selectbox("Tipologia", ["Prodotto Fisico (con giacenza)", "Intervento / Prestazione"])

            c4, c5, c6 = st.columns(3)
            prezzo_acquisto = c4.number_input("Costo Acquisto Unitario (EUR)", min_value=0.0, step=1.0)
            prezzo_vendita = c5.number_input("Prezzo Vendita Unitario (EUR)", min_value=0.0, step=1.0)
            iva_default = c6.selectbox("Aliquota IVA (%)", [10, 22, 4, 0], index=0)

            giacenza = st.number_input("Giacenza Iniziale (unità)", min_value=0.0, value=0.0, step=1.0)

            if st.form_submit_button("Salva in Magazzino"):
                if descrizione:
                    db["magazzino"].append({
                        "codice": codice,
                        "descrizione": descrizione,
                        "tipo": tipo,
                        "costo_acquisto": prezzo_acquisto,
                        "prezzo_vendita": prezzo_vendita,
                        "iva": iva_default,
                        "giacenza": giacenza
                    })
                    st.success(f"Articolo '{descrizione}' salvato!")
                    st.rerun()
                else:
                    st.warning("Inserisci una descrizione.")

    if db["magazzino"]:
        df_mag = pd.DataFrame(db["magazzino"])
        df_mag["Valore Giacenza (EUR)"] = df_mag["costo_acquisto"] * df_mag["giacenza"]
        st.dataframe(df_mag, use_container_width=True, hide_index=True)
    else:
        st.info("Il magazzino è vuoto.")

# ==============================================================================
# 5. FATTURAZIONE VENDITA (ATTIVA)
# ==============================================================================
elif st.session_state.pagina_attiva == "fatture_attive":
    st.header("🧾 Fatturazione Vendita (Attiva)")

    tab1, tab2 = st.tabs(["➕ Nuova Fattura di Vendita", "📋 Registro Fatture Emesse & Stampa PDF"])

    with tab1:
        if not db["clienti"]:
            st.warning("⚠️ Inserisci almeno un cliente nella sezione 'Anagrafica Clienti' prima di emettere una fattura.")
        else:
            if "righe_fattura_attiva" not in st.session_state:
                st.session_state.righe_fattura_attiva = []

            col1, col2, col3, col4 = st.columns(4)
            num_fatt = col1.text_input("Numero Fattura", value=f"{len(db['fatture_attive'])+1}/{str(datetime.now().year)[-2:]}")
            data_fatt = col2.date_input("Data Fattura", value=date.today())
            rif_offerta = col3.text_input("Riferimento Offerta", value="")
            scad_fatt = col4.date_input("Scadenza Pagamento", value=date.today() + timedelta(days=30))

            c_cli, c_reg = st.columns([2, 1])
            nomi_clienti = [c["nome"] for c in db["clienti"]]
            cliente_scelto_nome = c_cli.selectbox("Spettabile Cliente", nomi_clienti)
            cliente_obj = next(c for c in db["clienti"] if c["nome"] == cliente_scelto_nome)
            regolamento = c_reg.text_input("Regolamento", value=cliente_obj.get("pagamento", "rimessa diretta"))

            intestazione_corpo = st.text_input("Intestazione Corpo Descrizione", value="Vi rimettiamo regolare fattura per :")

            st.subheader("Aggiungi Righe Descrizione")
            c_art, c_qta, c_prz, c_iva = st.columns([3, 1, 1.5, 1])

            opzioni_mag = ["Inserimento Libero"] + [f"{m['codice']} - {m['descrizione']}" for m in db["magazzino"]]
            scelta_mag = c_art.selectbox("Articolo da Magazzino o Testo Libero", opzioni_mag)

            if scelta_mag != "Inserimento Libero":
                art_obj = next(m for m in db["magazzino"] if f"{m['codice']} - {m['descrizione']}" == scelta_mag)
                desc_riga = st.text_input("Testo riga descrizione", value=art_obj["descrizione"])
                prz_default = float(art_obj["prezzo_vendita"])
                iva_default = int(art_obj["iva"])
            else:
                desc_riga = st.text_input("Testo riga descrizione (es. sostituzione cerniere del cancello civ 66)")
                prz_default = 0.0
                iva_default = 10

            qta_riga = c_qta.number_input("Q.tà (0 se solo testo)", min_value=0.0, value=0.0, step=1.0)
            prz_riga = c_prz.number_input("Importo Riga (EUR)", min_value=0.0, value=prz_default, step=10.0)
            iva_riga = c_iva.selectbox("Aliquota IVA %", [10, 22, 4, 0], index=[10, 22, 4, 0].index(iva_default))

            if st.button("➕ Aggiungi Riga"):
                if desc_riga:
                    st.session_state.righe_fattura_attiva.append({
                        "codice_mag": scelta_mag.split(" - ")[0] if scelta_mag != "Inserimento Libero" else None,
                        "descrizione": desc_riga,
                        "qta": qta_riga,
                        "prezzo": prz_riga,
                        "iva": iva_riga
                    })
                    st.rerun()

            if st.session_state.righe_fattura_attiva:
                df_righe = pd.DataFrame(st.session_state.righe_fattura_attiva)
                st.dataframe(df_righe[["qta", "descrizione", "prezzo", "iva"]], use_container_width=True, hide_index=True)

                if st.button("🗑️ Svuota Righe"):
                    st.session_state.righe_fattura_attiva = []
                    st.rerun()

                imp_4 = 0.0
                iva_4 = 0.0
                imp_std = 0.0
                iva_std = 0.0
                aliq_std = 10

                for r in st.session_state.righe_fattura_attiva:
                    molt = r["qta"] if r["qta"] > 0 else 1.0
                    val_riga = round(molt * r["prezzo"], 2)
                    if r["iva"] == 4:
                        imp_4 += val_riga
                        iva_4 += round(val_riga * 0.04, 2)
                    elif r["iva"] > 0:
                        aliq_std = r["iva"]
                        imp_std += val_riga
                        iva_std += round(val_riga * (r["iva"] / 100.0), 2)
                    else:
                        imp_std += val_riga

                imponibile_tot = round(imp_4 + imp_std, 2)
                applica_rit = st.checkbox("Applica Ritenuta d'Acconto 4% (- RIT 4%)", value=cliente_obj.get("ritenuta_4", True))
                rit_perc = 4.0 if applica_rit else 0.0
                rit_imp = round(imponibile_tot * 0.04, 2) if applica_rit else 0.0

                totale_doc = round(imponibile_tot + iva_4 + iva_std - rit_imp, 2)

                st.markdown(f"### Totale Netto Fattura: **€ {totale_doc:.2f}** (Imponibile: € {imponibile_tot:.2f} | IVA: € {iva_4+iva_std:.2f} | -RIT 4%: € {rit_imp:.2f})")

                col_p1, col_p2 = st.columns(2)
                note_fatt = col_p1.text_input("Dicitura finale nel corpo fattura", value="saldo")
                stato_pag = col_p2.selectbox("Stato Pagamento", ["Da Incassare", "Incassata"])

                if st.button("💾 Registra Fattura e Scarica Magazzino", type="primary"):
                    nuova_fatt = {
                        "numero": num_fatt,
                        "data": data_fatt.strftime("%d/%m/%Y"),
                        "scadenza": scad_fatt.strftime("%d/%m/%Y"),
                        "rif_offerta": rif_offerta,
                        "cliente_nome": cliente_obj["nome"],
                        "cliente_indirizzo": cliente_obj.get("indirizzo", ""),
                        "cliente_cap": cliente_obj.get("cap", ""),
                        "cliente_citta": cliente_obj.get("citta", ""),
                        "cliente_piva": cliente_obj.get("piva", ""),
                        "cliente_sdi": cliente_obj.get("sdi", ""),
                        "pagamento": regolamento,
                        "intestazione_corpo": intestazione_corpo,
                        "righe": st.session_state.righe_fattura_attiva.copy(),
                        "imp_4": imp_4,
                        "iva_4": iva_4,
                        "imp_std": imp_std,
                        "aliq_std": aliq_std,
                        "iva_std": iva_std,
                        "rit_perc": rit_perc,
                        "rit_imp": rit_imp,
                        "totale": totale_doc,
                        "stato": stato_pag,
                        "note": note_fatt
                    }
                    db["fatture_attive"].append(nuova_fatt)

                    for r in st.session_state.righe_fattura_attiva:
                        if r["codice_mag"] and r["qta"] > 0:
                            for m in db["magazzino"]:
                                if m["codice"] == r["codice_mag"] and "Fisico" in m["tipo"]:
                                    m["giacenza"] = max(0.0, m["giacenza"] - r["qta"])

                    st.session_state.righe_fattura_attiva = []
                    st.success(f"Fattura N. {num_fatt} registrata!")
                    st.rerun()

    with tab2:
        if db["fatture_attive"]:
            df_fa = pd.DataFrame(db["fatture_attive"])
            st.dataframe(df_fa[["numero", "data", "scadenza", "cliente_nome", "totale", "stato"]], use_container_width=True, hide_index=True)

            st.subheader("🖨️ Stampa / Salva PDF Fattura")
            sel_num = st.selectbox("Seleziona Fattura da esportare", [f["numero"] for f in db["fatture_attive"]])
            fatt_selezionata = next(f for f in db["fatture_attive"] if f["numero"] == sel_num)

            pdf_bytes = genera_pdf_documento("Fattura", fatt_selezionata, db["ditta"])
            st.download_button(
                label=f"📄 Scarica / Stampa PDF Fattura {sel_num}",
                data=pdf_bytes,
                file_name=f"Fattura_{sel_num.replace('/', '_')}.pdf",
                mime="application/pdf",
                type="primary"
            )
        else:
            st.info("Nessuna fattura attiva registrata.")

# ==============================================================================
# 6. FATTURAZIONE ACQUISTI (PASSIVA)
# ==============================================================================
elif st.session_state.pagina_attiva == "fatture_passive":
    st.header("📥 Fatturazione Acquisti (Passiva)")

    with st.expander("➕ Registra Nuova Fattura di Acquisto", expanded=True):
        if not db["fornitori"]:
            st.warning("⚠️ Inserisci almeno un fornitore in 'Anagrafica Fornitori'.")
        else:
            with st.form("form_acquisto", clear_on_submit=True):
                c1, c2, c3 = st.columns(3)
                num_doc = c1.text_input("Numero Fattura Fornitore*")
                data_doc = c2.date_input("Data Fattura", value=date.today())
                scad_doc = c3.date_input("Scadenza Pagamento", value=date.today() + timedelta(days=30))

                forn_scelto = st.selectbox("Fornitore", [f["nome"] for f in db["fornitori"]])
                descrizione = st.text_input("Descrizione Acquisto / Fornitura*")

                c4, c5, c6 = st.columns(3)
                imponibile = c4.number_input("Imponibile (EUR)", min_value=0.0, step=10.0)
                iva = c5.number_input("IVA (EUR)", min_value=0.0, step=2.0)
                stato = c6.selectbox("Stato Pagamento", ["Da Pagare", "Pagata"])

                st.markdown("**Carico Magazzino (Opzionale)**")
                cm1, cm2 = st.columns(2)
                art_carico = cm1.selectbox("Aggiorna giacenza articolo", ["Nessuno"] + [f"{m['codice']} - {m['descrizione']}" for m in db["magazzino"]])
                qta_carico = cm2.number_input("Quantità acquistata", min_value=0.0, value=0.0, step=1.0)

                if st.form_submit_button("💾 Registra Fattura Passiva"):
                    if num_doc and descrizione:
                        totale = round(imponibile + iva, 2)
                        db["fatture_passive"].append({
                            "numero": num_doc,
                            "data": data_doc.strftime("%d/%m/%Y"),
                            "scadenza": scad_doc.strftime("%d/%m/%Y"),
                            "fornitore": forn_scelto,
                            "descrizione": descrizione,
                            "imponibile": imponibile,
                            "iva": iva,
                            "totale": totale,
                            "stato": stato
                        })
                        if art_carico != "Nessuno" and qta_carico > 0:
                            cod_m = art_carico.split(" - ")[0]
                            for m in db["magazzino"]:
                                if m["codice"] == cod_m:
                                    m["giacenza"] += qta_carico
                        st.success("Fattura passiva registrata!")
                        st.rerun()
                    else:
                        st.warning("Compila numero documento e descrizione.")

    if db["fatture_passive"]:
        st.subheader("Registro Fatture Passive")
        st.dataframe(pd.DataFrame(db["fatture_passive"]), use_container_width=True, hide_index=True)

# ==============================================================================
# 7. SCADENZARIO
# ==============================================================================
elif st.session_state.pagina_attiva == "scadenzario":
    st.header("📅 Scadenzario Incassi e Pagamenti")

    incassi_aperti = [f for f in db["fatture_attive"] if f["stato"] == "Da Incassare"]
    pagamenti_aperti = [f for f in db["fatture_passive"] if f["stato"] == "Da Pagare"]

    tot_incassare = sum(f["totale"] for f in incassi_aperti)
    tot_pagare = sum(f["totale"] for f in pagamenti_aperti)
    saldo_previsto = tot_incassare - tot_pagare

    m1, m2, m3 = st.columns(3)
    m1.metric("🟢 Crediti da Incassare", f"€ {tot_incassare:.2f}")
    m2.metric("🔴 Debiti da Pagare", f"€ {tot_pagare:.2f}")
    m3.metric("⚖️ Saldo Netto Previsionale", f"€ {saldo_previsto:.2f}")

    st.divider()
    col_sx, col_dx = st.columns(2)

    with col_sx:
        st.subheader("🟢 Scadenze Clienti (Da Incassare)")
        if incassi_aperti:
            for idx, f in enumerate(db["fatture_attive"]):
                if f["stato"] == "Da Incassare":
                    with st.container(border=True):
                        st.write(f"**Fatt. {f['numero']}** - {f['cliente_nome']}")
                        st.write(f"Scadenza: `{f['scadenza']}` | Importo: **€ {f['totale']:.2f}**")
                        if st.button(f"✅ Segna come Incassata ({f['numero']})", key=f"inc_{idx}"):
                            db["fatture_attive"][idx]["stato"] = "Incassata"
                            st.rerun()
        else:
            st.success("Nessun credito in sospeso!")

    with col_dx:
        st.subheader("🔴 Scadenze Fornitori (Da Pagare)")
        if pagamenti_aperti:
            for idx, f in enumerate(db["fatture_passive"]):
                if f["stato"] == "Da Pagare":
                    with st.container(border=True):
                        st.write(f"**Fatt. {f['numero']}** - {f['fornitore']}")
                        st.write(f"Scadenza: `{f['scadenza']}` | Importo: **€ {f['totale']:.2f}**")
                        if st.button(f"✅ Segna come Pagata ({f['numero']})", key=f"pag_{idx}"):
                            db["fatture_passive"][idx]["stato"] = "Pagata"
                            st.rerun()
        else:
            st.success("Nessun pagamento in sospeso!")

# ==============================================================================
# 8. PREVENTIVI
# ==============================================================================
elif st.session_state.pagina_attiva == "preventivi":
    st.header("📝 Gestione Preventivi & Conversione in Fattura")

    tab_p1, tab_p2 = st.tabs(["➕ Nuovo Preventivo (Offerta)", "📂 Archivio Preventivi & Conversione"])

    with tab_p1:
        if not db["clienti"]:
            st.warning("⚠️ Inserisci almeno un cliente in 'Anagrafica Clienti'.")
        else:
            if "righe_preventivo" not in st.session_state:
                st.session_state.righe_preventivo = []

            c1, c2, c3 = st.columns(3)
            num_prev = c1.text_input("Numero Offerta / Preventivo", value=f"{len(db['preventivi'])+1}/{str(datetime.now().year)[-2:]}")
            data_prev = c2.date_input("Data Offerta", value=date.today())
            validita_prev = c3.date_input("Valido fino al", value=date.today() + timedelta(days=15))

            cliente_prev_nome = st.selectbox("Cliente Destinatario", [c["nome"] for c in db["clienti"]], key="prev_cli")
            cliente_prev_obj = next(c for c in db["clienti"] if c["nome"] == cliente_prev_nome)

            cp1, cp2, cp3, cp4 = st.columns([3, 1, 1.5, 1])
            desc_p = cp1.text_input("Descrizione voce preventivo")
            qta_p = cp2.number_input("Q.tà", min_value=0.0, value=0.0, step=1.0, key="pqta")
            prz_p = cp3.number_input("Importo (EUR)", min_value=0.0, value=0.0, step=10.0, key="pprz")
            iva_p = cp4.selectbox("IVA %", [10, 22, 4, 0], index=0, key="piva")

            if st.button("➕ Aggiungi Voce al Preventivo"):
                if desc_p:
                    st.session_state.righe_preventivo.append({
                        "codice_mag": None,
                        "descrizione": desc_p,
                        "qta": qta_p,
                        "prezzo": prz_p,
                        "iva": iva_p
                    })
                    st.rerun()

            if st.session_state.righe_preventivo:
                df_rp = pd.DataFrame(st.session_state.righe_preventivo)
                st.dataframe(df_rp[["qta", "descrizione", "prezzo", "iva"]], use_container_width=True, hide_index=True)

                imp_std_p = sum((r["qta"] if r["qta"] > 0 else 1.0) * r["prezzo"] for r in st.session_state.righe_preventivo)
                iva_std_p = round(sum(((r["qta"] if r["qta"] > 0 else 1.0) * r["prezzo"]) * (r["iva"] / 100.0) for r in st.session_state.righe_preventivo), 2)
                tot_p = round(imp_std_p + iva_std_p, 2)

                st.markdown(f"### Totale Preventivo: **€ {tot_p:.2f}**")
                note_p = st.text_input("Note finali preventivo", value="")

                if st.button("💾 Salva Preventivo", type="primary"):
                    db["preventivi"].append({
                        "numero": num_prev,
                        "data": data_prev.strftime("%d/%m/%Y"),
                        "scadenza": validita_prev.strftime("%d/%m/%Y"),
                        "rif_offerta": num_prev,
                        "cliente_nome": cliente_prev_obj["nome"],
                        "cliente_indirizzo": cliente_prev_obj.get("indirizzo", ""),
                        "cliente_cap": cliente_prev_obj.get("cap", ""),
                        "cliente_citta": cliente_prev_obj.get("citta", ""),
                        "cliente_piva": cliente_prev_obj.get("piva", ""),
                        "cliente_sdi": cliente_prev_obj.get("sdi", ""),
                        "pagamento": cliente_prev_obj.get("pagamento", "rimessa diretta"),
                        "intestazione_corpo": "Vi rimettiamo nostra migliore offerta per :",
                        "righe": st.session_state.righe_preventivo.copy(),
                        "imp_4": 0.0,
                        "iva_4": 0.0,
                        "imp_std": imp_std_p,
                        "aliq_std": 10,
                        "iva_std": iva_std_p,
                        "rit_perc": 0.0,
                        "rit_imp": 0.0,
                        "totale": tot_p,
                        "stato": "In Attesa",
                        "note": note_p
                    })
                    st.session_state.righe_preventivo = []
                    st.success(f"Preventivo {num_prev} salvato!")
                    st.rerun()

    with tab_p2:
        if db["preventivi"]:
            for idx, p in enumerate(db["preventivi"]):
                with st.container(border=True):
                    c_info, c_act1, c_act2 = st.columns([3, 1.5, 1.5])
                    c_info.write(f"**Offerta {p['numero']}** | Cliente: **{p['cliente_nome']}** | Data: {p['data']}")
                    c_info.write(f"Totale: **€ {p['totale']:.2f}** | Stato: `{p['stato']}`")

                    pdf_prev = genera_pdf_documento("Preventivo", p, db["ditta"])
                    c_act1.download_button(
                        label="📄 Scarica PDF",
                        data=pdf_prev,
                        file_name=f"Preventivo_{p['numero'].replace('/', '_')}.pdf",
                        mime="application/pdf",
                        key=f"dl_prev_{idx}"
                    )

                    if p["stato"] != "Fatturato":
                        if c_act2.button("🔄 Converti in Fattura", key=f"conv_{idx}"):
                            nuovo_num_fatt = f"{len(db['fatture_attive'])+1}/{str(datetime.now().year)[-2:]}"
                            nuova_fatt_da_prev = p.copy()
                            nuova_fatt_da_prev["numero"] = nuovo_num_fatt
                            nuova_fatt_da_prev["rif_offerta"] = p["numero"]
                            nuova_fatt_da_prev["data"] = date.today().strftime("%d/%m/%Y")
                            nuova_fatt_da_prev["scadenza"] = (date.today() + timedelta(days=30)).strftime("%d/%m/%Y")
                            nuova_fatt_da_prev["intestazione_corpo"] = "Vi rimettiamo regolare fattura per :"
                            nuova_fatt_da_prev["note"] = "saldo"
                            nuova_fatt_da_prev["stato"] = "Da Incassare"
                            db["fatture_attive"].append(nuova_fatt_da_prev)
                            db["preventivi"][idx]["stato"] = "Fatturato"
                            st.success(f"Convertito nella Fattura N. {nuovo_num_fatt} con Riferimento Offerta {p['numero']}!")
                            st.rerun()
        else:
            st.info("Nessun preventivo in archivio.")
