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

# --- CSS: NASCONDE SIDEBAR + STILE PULSANTI TUTTI IDENTICI ---
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

    /* Contenitore dei pulsanti della Home: larghezza e altezza bloccate */
    [class*="st-key-tile_"] {
        width: 100% !important;
        height: 175px !important;
    }

    /* Pulsanti grandi della schermata iniziale: dimensioni identiche */
    [class*="st-key-tile_"] button {
        height: 175px !important;
        min-height: 175px !important;
        max-height: 175px !important;
        width: 100% !important;
        box-sizing: border-box !important;
        overflow: hidden !important;
        border-radius: 16px !important;
        border: none !important;
        color: #ffffff !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: center !important;
        text-align: center !important;
        white-space: pre-wrap !important;
        padding: 14px 10px !important;
        box-shadow: 0 6px 14px rgba(15, 23, 42, 0.14) !important;
        transition: transform 0.15s ease, box-shadow 0.15s ease !important;
    }

    [class*="st-key-tile_"] button:hover {
        transform: translateY(-3px) !important;
        box-shadow: 0 10px 20px rgba(15, 23, 42, 0.22) !important;
    }

    /* Dicitura sotto l'icona */
    [class*="st-key-tile_"] button p {
        font-size: 1.45rem !important;
        font-weight: 800 !important;
        line-height: 1.25 !important;
        margin: 0 !important;
    }

    /* Icona grande al centro */
    [class*="st-key-tile_"] button p::first-line {
        font-size: 3.8rem !important;
        line-height: 1.45 !important;
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

# --- HELPER LOGHI SEPARATI: LOGO PROGRAMMA (logo_app.png) VS LOGO DOCUMENTI (logo_azienda.png) ---
LOGO_APP_CANDIDATES = ["logo_app.png", "logo_app.jpg", "logo_app.jpeg"]
LOGO_AZIENDA_CANDIDATES = ["logo_azienda.png", "logo_azienda.jpg", "logo_azienda.jpeg"]

def leggi_file_b64(candidati):
    for nome_file in candidati:
        if os.path.exists(nome_file):
            try:
                with open(nome_file, "rb") as f:
                    return base64.b64encode(f.read()).decode("utf-8")
            except Exception:
                pass
    return ""

def mostra_logo_programma(width=110):
    logo_app_b64 = leggi_file_b64(LOGO_APP_CANDIDATES)
    if logo_app_b64:
        try:
            st.image(base64.b64decode(logo_app_b64), width=width)
            return
        except Exception:
            pass
    for nome_file in LOGO_APP_CANDIDATES:
        if os.path.exists(nome_file):
            st.image(Image.open(nome_file), width=width)
            return

def carica_logo_azienda_locale_b64():
    return leggi_file_b64(LOGO_AZIENDA_CANDIDATES)

def ottieni_logo_azienda_b64(ditta_data):
    logo_salvato = ditta_data.get("logo_b64", "")
    if logo_salvato:
        return logo_salvato
    return carica_logo_azienda_locale_b64()

def mostra_logo_azienda_widget(ditta_data, width=120):
    logo_b64 = ottieni_logo_azienda_b64(ditta_data)
    if logo_b64:
        try:
            st.image(base64.b64decode(logo_b64), width=width)
            return
        except Exception:
            pass
    for nome_file in LOGO_AZIENDA_CANDIDATES:
        if os.path.exists(nome_file):
            st.image(Image.open(nome_file), width=width)
            return

# --- NORMALIZZAZIONE DATABASE STORICO ---
DEFAULT_DITTA = {
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
}

def normalizza_db(raw_db):
    base = {
        "ditta": dict(DEFAULT_DITTA),
        "clienti": [],
        "fornitori": [],
        "magazzino": [],
        "fatture_attive": [],
        "fatture_passive": [],
        "preventivi": []
    }
    if isinstance(raw_db, dict):
        ditta_in = raw_db.get("ditta")
        if isinstance(ditta_in, dict):
            base["ditta"].update(ditta_in)
        for key in ["clienti", "fornitori", "magazzino", "fatture_attive", "fatture_passive", "preventivi"]:
            val = raw_db.get(key)
            if isinstance(val, list):
                base[key] = val
    if not base["ditta"].get("logo_b64"):
        base["ditta"]["logo_b64"] = carica_logo_azienda_locale_b64()
    return base

# --- INIZIALIZZAZIONE STATO ---
def init_db():
    if "pagina_attiva" not in st.session_state:
        st.session_state.pagina_attiva = "home"
    if "storico_caricato" not in st.session_state:
        st.session_state.storico_caricato = False
    if "db" not in st.session_state:
        st.session_state.db = normalizza_db({})
    else:
        st.session_state.db = normalizza_db(st.session_state.db)

init_db()
db = st.session_state.db

if "conferma_elimina" not in st.session_state:
    st.session_state.conferma_elimina = None

def vai_a(sezione):
    st.session_state.pagina_attiva = sezione
    st.rerun()

def fmt_eur(val):
    if val is None or val == 0:
        return "-"
    return f"{val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

FONT_REG_CANDIDATES = ["DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
FONT_BOLD_CANDIDATES = ["DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]

def trova_font(candidati):
    for p in candidati:
        if p and os.path.exists(p):
            return p
    return None

def prepara_font_pdf(pdf):
    reg_path = trova_font(FONT_REG_CANDIDATES)
    bold_path = trova_font(FONT_BOLD_CANDIDATES)
    if reg_path:
        pdf.add_font("AppFont", "", reg_path)
        pdf.add_font("AppFont", "B", bold_path if bold_path else reg_path)
        pdf.add_font("AppFont", "I", reg_path)
        pdf.add_font("AppFont", "BI", bold_path if bold_path else reg_path)
        return "AppFont", True
    return None, False

def pdf_txt(val, usa_unicode=False):
    if val is None:
        return ""
    s = str(val)
    if usa_unicode:
        return s
    return s.replace("€", "EUR").encode("latin-1", errors="replace").decode("latin-1")

def aggiungi_o_aggiorna_magazzino(nuovo_art):
    cod_new = str(nuovo_art.get("codice", "")).strip().lower()
    desc_new = str(nuovo_art.get("descrizione", "")).strip().lower()
    qta_new = float(nuovo_art.get("giacenza", 0.0) or 0.0)

    for art in db["magazzino"]:
        cod_es = str(art.get("codice", "")).strip().lower()
        desc_es = str(art.get("descrizione", "")).strip().lower()
        stesso_codice = bool(cod_new and cod_es and cod_new == cod_es)
        stessa_desc = bool(desc_new and desc_es and desc_new == desc_es)

        if stesso_codice or stessa_desc:
            art["giacenza"] = round(float(art.get("giacenza", 0.0) or 0.0) + qta_new, 2)
            if float(nuovo_art.get("costo_acquisto", 0.0) or 0.0) > 0:
                art["costo_acquisto"] = float(nuovo_art["costo_acquisto"])
            if float(nuovo_art.get("prezzo_vendita", 0.0) or 0.0) > 0:
                art["prezzo_vendita"] = float(nuovo_art["prezzo_vendita"])
            if nuovo_art.get("tipo"):
                art["tipo"] = nuovo_art["tipo"]
            if nuovo_art.get("iva") is not None:
                art["iva"] = int(nuovo_art["iva"])
            return "aggiornato"

    voce = {
        "codice": str(nuovo_art.get("codice", "")).strip() or f"ART-{len(db['magazzino'])+1:03d}",
        "descrizione": str(nuovo_art.get("descrizione", "")).strip(),
        "tipo": nuovo_art.get("tipo", "Prodotto Fisico (con giacenza)"),
        "costo_acquisto": float(nuovo_art.get("costo_acquisto", 0.0) or 0.0),
        "prezzo_vendita": float(nuovo_art.get("prezzo_vendita", 0.0) or 0.0),
        "iva": int(nuovo_art.get("iva", 10) or 10),
        "giacenza": round(qta_new, 2)
    }
    db["magazzino"].append(voce)
    return "inserito"

def pulsante_elimina_sicuro(stato_key, etichetta_avviso, on_conferma, key_prefix):
    if "conferma_elimina" not in st.session_state:
        st.session_state.conferma_elimina = None

    if st.session_state.conferma_elimina == stato_key:
        st.warning(f"⚠️ {etichetta_avviso}")
        c_ok, c_no = st.columns(2)
        if c_ok.button("Conferma", key=f"{key_prefix}_ok", type="primary"):
            st.session_state.conferma_elimina = None
            on_conferma()
            st.rerun()
        if c_no.button("Annulla", key=f"{key_prefix}_no"):
            st.session_state.conferma_elimina = None
            st.rerun()
    else:
        if st.button("🗑️ Elimina", key=f"{key_prefix}_ask"):
            st.session_state.conferma_elimina = stato_key
            st.rerun()

# --- FUNZIONE GENERAZIONE PDF SU SCHEMA ALLEGATO (USA LOGO AZIENDA) ---

def genera_pdf_documento(tipo_doc, doc_data, ditta_data):
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    font_fam, usa_uni = prepara_font_pdf(pdf)
    f_serif = font_fam if font_fam else "Times"
    f_sans = font_fam if font_fam else "Helvetica"
    pdf.add_page()
    pdf.set_auto_page_break(auto=False)
    
    x0 = 15
    y0 = 15
    w_tot = 180

    blu_logo = (25, 65, 120)
    grigio_banda = (135, 138, 142)
    nero = (20, 20, 20)

    # 1. Riquadro superiore: Logo Azienda SX | Spettabile DX
    h_top = 46
    w_sx_top = 68
    w_dx_top = w_tot - w_sx_top

    pdf.set_draw_color(0, 0, 0)
    pdf.set_line_width(0.35)
    pdf.rect(x0, y0, w_sx_top, h_top)
    pdf.rect(x0 + w_sx_top, y0, w_dx_top, h_top)

    logo_b64 = ottieni_logo_azienda_b64(ditta_data)
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
    pdf.set_font(f_serif, "", 10)
    pdf.cell(44, 5, pdf_txt("Spettabile", usa_uni))
    pdf.set_xy(x_val, y0 + 11)
    pdf.set_font(f_sans, "B", 9.5)
    pdf.cell(62, 5, pdf_txt(doc_data.get("cliente_nome", ""), usa_uni))

    pdf.set_xy(x_spett, y0 + 21)
    pdf.set_font(f_serif, "", 10)
    pdf.cell(44, 5, pdf_txt("via", usa_uni))
    pdf.set_xy(x_val, y0 + 21)
    pdf.set_font(f_serif, "", 10)
    pdf.cell(62, 5, pdf_txt(doc_data.get("cliente_indirizzo", ""), usa_uni))

    pdf.set_xy(x_spett, y0 + 26)
    pdf.cell(44, 5, pdf_txt("cap:", usa_uni))
    pdf.set_xy(x_val, y0 + 26)
    pdf.cell(62, 5, pdf_txt(doc_data.get("cliente_cap", ""), usa_uni))

    pdf.set_xy(x_val, y0 + 31)
    pdf.cell(62, 5, pdf_txt(doc_data.get("cliente_citta", ""), usa_uni))

    pdf.set_xy(x_spett, y0 + 36)
    pdf.cell(44, 5, pdf_txt("cod fiscale", usa_uni))
    pdf.set_xy(x_val, y0 + 36)
    pdf.cell(62, 5, pdf_txt(doc_data.get("cliente_piva", ""), usa_uni))

    pdf.set_xy(x_spett, y0 + 41)
    pdf.cell(44, 5, pdf_txt("sdi", usa_uni))
    pdf.set_xy(x_val, y0 + 41)
    pdf.cell(62, 5, pdf_txt(doc_data.get("cliente_sdi", ""), usa_uni))

    # 2. Riga metadati
    y1 = y0 + h_top
    h_meta = 12
    w_c1 = 55
    w_c2 = 55
    w_c3 = w_tot - w_c1 - w_c2

    pdf.rect(x0, y1, w_c1, h_meta)
    pdf.rect(x0 + w_c1, y1, w_c2, h_meta)
    pdf.rect(x0 + w_c1 + w_c2, y1, w_c3, h_meta)

    pdf.set_font(f_serif, "B", 10)
    pdf.set_xy(x0 + 1.5, y1 + 1)
    pdf.cell(w_c1 - 3, 4.5, pdf_txt("data fattura" if tipo_doc == "Fattura" else "data preventivo", usa_uni))
    pdf.set_xy(x0 + w_c1, y1 + 1)
    pdf.cell(w_c2, 4.5, pdf_txt(tipo_doc.upper(), usa_uni), align="C")
    pdf.set_xy(x0 + w_c1 + w_c2 + 1.5, y1 + 1)
    pdf.cell(w_c3 - 3, 4.5, pdf_txt("RIFERIMENTO OFFERTA", usa_uni))

    pdf.set_font(f_serif, "", 10.5)
    pdf.set_xy(x0, y1 + 6.5)
    pdf.cell(w_c1, 5, pdf_txt(doc_data.get("data", ""), usa_uni), align="C")
    pdf.set_xy(x0 + w_c1, y1 + 6.5)
    pdf.cell(w_c2, 5, pdf_txt(doc_data.get("numero", ""), usa_uni), align="C")
    pdf.set_xy(x0 + w_c1 + w_c2 + 1.5, y1 + 6.5)
    pdf.cell(w_c3 - 3, 5, pdf_txt(doc_data.get("rif_offerta", ""), usa_uni), align="L")

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

    pdf.set_font(f_serif, "B", 10)
    pdf.set_xy(x0 + 1.5, y2 + 1)
    pdf.cell(w_pag_sx - 3, 4.5, pdf_txt("Regolamento", usa_uni))
    pdf.set_font(f_serif, "", 10)
    pdf.set_xy(x0 + 1.5, y2 + 9.5)
    pdf.cell(w_pag_sx - 3, 4.5, pdf_txt(doc_data.get("pagamento", "rimessa diretta"), usa_uni))

    pdf.set_font(f_serif, "B", 9.5)
    pdf.set_xy(x0 + w_pag_sx + 1.5, y2 + 1)
    pdf.cell(w_pag_dx - 3, 4.5, pdf_txt("bonifico intestato a:", usa_uni))
    pdf.set_xy(x0 + w_pag_sx + 1.5, y2 + 5.5)
    pdf.cell(w_pag_dx - 3, 4.5, pdf_txt(ditta_data.get("titolare", ""), usa_uni))
    pdf.set_xy(x0 + w_pag_sx + 1.5, y2 + 10)
    pdf.cell(w_pag_dx - 3, 4.5, pdf_txt(f"IBAN: {ditta_data.get('iban', '')}", usa_uni))

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

    pdf.set_font(f_serif, "", 9.5)
    pdf.set_xy(x0, y4 + 0.5)
    pdf.cell(w_qta, 4.5, pdf_txt("q.tà", usa_uni), align="C")
    pdf.set_xy(x0 + w_qta, y4 + 0.5)
    pdf.cell(w_desc, 4.5, pdf_txt("descrizione", usa_uni), align="C")

    # 5. Corpo centrale descrizione
    y5 = y4 + h_th
    h_body = 104
    pdf.rect(x0, y5, w_qta, h_body)
    pdf.rect(x0 + w_qta, y5, w_desc, h_body)

    pdf.set_font(f_serif, "B", 9.5)
    pdf.set_xy(x0 + w_qta + 1.5, y5 + 4)
    frase_intro = doc_data.get("intestazione_corpo", "Vi rimettiamo regolare fattura per :" if tipo_doc == "Fattura" else "Vi rimettiamo nostra migliore offerta per :")
    pdf.cell(w_desc - 3, 5, pdf_txt(frase_intro, usa_uni))

    curr_y = y5 + 16
    pdf.set_font(f_sans, "B", 9)
    for r in doc_data.get("righe", []):
        if curr_y > y5 + h_body - 16:
            break
        qta_val = r.get("qta", 0)
        if qta_val and qta_val > 0:
            pdf.set_xy(x0, curr_y)
            q_str = f"{int(qta_val)}" if float(qta_val).is_integer() else f"{qta_val:.2f}"
            pdf.cell(w_qta, 5, pdf_txt(q_str, usa_uni), align="C")
        pdf.set_xy(x0 + w_qta + 1.5, curr_y)
        pdf.cell(w_desc - 3, 5, pdf_txt(r.get("descrizione", ""), usa_uni))
        curr_y += 5.2

    dicitura_finale = doc_data.get("note", "saldo")
    if dicitura_finale:
        pdf.set_font(f_serif, "B", 9.5)
        pdf.set_xy(x0 + w_qta + 1.5, y5 + 58)
        pdf.cell(w_desc - 3, 5, pdf_txt(dicitura_finale, usa_uni))

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

    pdf.set_font(f_serif, "B", 10)
    pdf.set_xy(x0, y7 + 0.5)
    pdf.cell(w_t1, 4.5, pdf_txt("Imponibile", usa_uni), align="C")
    pdf.set_xy(x0 + w_t1 + 1.5, y7 + 0.5)
    pdf.cell(w_t2 - 3, 4.5, pdf_txt("IVA", usa_uni), align="L")
    pdf.set_xy(x0 + w_t1 + w_t2, y7 + 0.5)
    pdf.cell(w_t3, 4.5, pdf_txt("totale fattura" if tipo_doc == "Fattura" else "totale preventivo", usa_uni), align="C")

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

    pdf.set_font(f_serif, "", 9.5)
    pdf.set_xy(x0 + 14, y8 + 0.8)
    pdf.cell(6, 4.8, pdf_txt("€", usa_uni))
    pdf.cell(26, 4.8, pdf_txt(fmt_eur(imp_4), usa_uni), align="R")

    pdf.set_xy(x0 + w_t1 + 1.5, y8 + 0.8)
    pdf.cell(18, 4.8, pdf_txt("iva 4%", usa_uni))
    pdf.cell(6, 4.8, pdf_txt("€", usa_uni))
    pdf.cell(19, 4.8, pdf_txt(fmt_eur(iva_4), usa_uni), align="R")

    pdf.set_xy(x0 + w_t1 + w_t2 + 24, y8 + 0.8)
    pdf.cell(6, 4.8, pdf_txt("€", usa_uni))
    pdf.cell(52, 4.8, pdf_txt(fmt_eur(tot_4), usa_uni), align="R")

    pdf.set_xy(x0 + 14, y8 + 5.8)
    pdf.cell(6, 4.8, pdf_txt("€", usa_uni))
    pdf.cell(26, 4.8, pdf_txt(fmt_eur(imp_std), usa_uni), align="R")

    pdf.set_xy(x0 + w_t1 + 1.5, y8 + 5.8)
    pdf.cell(18, 4.8, pdf_txt(f"iva {aliq_std}%", usa_uni))
    pdf.cell(6, 4.8, pdf_txt("€", usa_uni))
    pdf.cell(19, 4.8, pdf_txt(fmt_eur(iva_std), usa_uni), align="R")

    pdf.set_xy(x0 + w_t1 + w_t2 + 24, y8 + 5.8)
    pdf.cell(6, 4.8, pdf_txt("€", usa_uni))
    pdf.cell(52, 4.8, pdf_txt(fmt_eur(tot_std), usa_uni), align="R")

    pdf.set_xy(x0 + 14, y8 + 10.8)
    pdf.cell(32, 4.8, pdf_txt(f"- RIT {int(rit_perc)}%" if rit_perc > 0 else "", usa_uni))

    pdf.set_xy(x0 + w_t1 + 19.5, y8 + 10.8)
    pdf.cell(6, 4.8, pdf_txt("€", usa_uni) if rit_imp > 0 else "")
    pdf.cell(19, 4.8, pdf_txt(fmt_eur(rit_imp), usa_uni) if rit_imp > 0 else "", align="R")

    pdf.set_font(f_serif, "B", 10)
    pdf.set_xy(x0 + w_t1 + w_t2 + 24, y8 + 10.8)
    pdf.cell(6, 4.8, pdf_txt("€", usa_uni))
    pdf.cell(52, 4.8, pdf_txt(fmt_eur(totale_finale), usa_uni), align="R")

    # 7. Piè di pagina riquadrato in basso a sinistra
    # 7. Piè di pagina riquadrato in basso a sinistra
    y9 = y8 + h_tot_body
    h_foot = 23
    w_foot = 112
    pdf.rect(x0, y9, w_foot, h_foot)

    pdf.set_font(f_serif, "B", 10)
    pdf.set_xy(x0 + 1.5, y9 + 1)
    pdf.cell(w_foot - 3, 4.5, pdf_txt(ditta_data.get("titolare", ""), usa_uni))

    pdf.set_font(f_serif, "", 9.5)
    pdf.set_xy(x0 + 1.5, y9 + 5.5)
    pdf.cell(w_foot - 3, 4.2, pdf_txt(ditta_data.get("indirizzo", ""), usa_uni))

    pdf.set_xy(x0 + 1.5, y9 + 9.7)
    pdf.cell(w_foot - 3, 4.2, pdf_txt(ditta_data.get("cap_citta", ""), usa_uni))

    pdf.set_xy(x0 + 1.5, y9 + 13.9)
    pdf.cell(w_foot - 3, 4.2, pdf_txt(f"P.IVA {ditta_data.get('piva', '')} cf {ditta_data.get('cf', '')}", usa_uni))

    pdf.set_xy(x0 + 1.5, y9 + 18.1)
    pdf.cell(w_foot - 3, 4.2, pdf_txt(ditta_data.get("telefono", ""), usa_uni))

    return bytes(pdf.output())

# --- BARRA SUPERIORE NELLE SEZIONI INTERNE ---
if st.session_state.pagina_attiva != "home":
    top_l, col_logo, col_titolo, top_r = st.columns([2, 1, 5, 1.5])
    with top_l:
        if st.button("⬅️ Torna alla Home", key="btn_back_home"):
            vai_a("home")
    #with top_c:
        #st.caption(f"**{db['ditta'].get('denominazione', 'Ditta Individuale')}** — {db['ditta'].get('titolare', '')}")
    
    #col_logo, col_titolo = st.columns([1.2, 6], vertical_alignment="center")
    with col_logo:
        mostra_logo_programma(width=110)
    with col_titolo:
        st.title("Gestione contabile semplice")
        st.caption(
            f"{db['ditta'].get('denominazione', '')} — {db['ditta'].get('titolare', '')} | "
            "Ditta individuale"
        ) 
    
    with top_r:
        db_top = json.loads(json.dumps(db, default=str))
        db_top.setdefault("ditta", {})["logo_b64"] = ottieni_logo_azienda_b64(db["ditta"])
        json_str_top = json.dumps(db_top, indent=2, default=str)
        st.download_button(
            label="💾 Salva Storico (.json)",
            data=json_str_top,
            file_name=f"contabilita_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
            mime="application/json",
            key="dl_top_json"
        )
    st.divider()

# ==============================================================================
# SCHERMATA INIZIALE: LOGO PROGRAMMA (logo_app.png) + PULSANTI GRANDI
# ==============================================================================
if st.session_state.pagina_attiva == "home":
    col_logo, col_titolo = st.columns([1.2, 6], vertical_alignment="center")
    with col_logo:
        mostra_logo_programma(width=110)
    with col_titolo:
        st.title("Gestione contabile semplice")
        st.caption(
            f"{db['ditta'].get('denominazione', '')} — {db['ditta'].get('titolare', '')} | "
            "Ditta individuale"
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
        if st.button("📦\n\nMagazzino", key="tile_4"):
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
                    st.session_state.db = normalizza_db(loaded_data)
                    st.session_state.storico_caricato = True
                    st.success("Storico caricato con successo! Ora tutte le sezioni mostrano i dati salvati.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore durante il caricamento del file: {e}")

    with col_dl:
        st.write("")
        st.write("")
        db_export = normalizza_db(json.loads(json.dumps(db, default=str)))
        json_str_home = json.dumps(db_export, indent=2, default=str)
        st.download_button(
            label="⬇️ Scarica Storico Attuale (.json)",
            data=json_str_home,
            file_name=f"contabilita_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
            mime="application/json",
            key="btn_scarica_storico"
        )
    st.markdown('</div>', unsafe_allow_html=True)

# ==============================================================================
# 1. DATI DITTA INDIVIDUALE (USA LOGO AZIENDA: logo_azienda.png)
# ==============================================================================
elif st.session_state.pagina_attiva == "ditta":
    st.header("🏢 Dati Ditta Individuale & Intestazione Fattura")
    st.info("Questi dati e il logo aziendale (logo_azienda.png) popolano automaticamente il riquadro superiore sinistro, l'area IBAN e il riquadro piè di pagina dei documenti PDF.")

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

        st.subheader("🖼️ Logo Aziendale per Documenti (logo_azienda.png)")
        mostra_logo_azienda_widget(db["ditta"], width=120)
        logo_file = st.file_uploader("Carica o sostituisci Logo Azienda per i documenti (PNG o JPG)", type=["png", "jpg", "jpeg"])

        if st.form_submit_button("💾 Salva Dati Ditta", type="primary"):
            logo_b64_val = ottieni_logo_azienda_b64(db["ditta"])
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
            st.session_state.storico_caricato = True
            st.success("Dati della Ditta Individuale e logo aziendale salvati correttamente!")
            st.rerun()

# ==============================================================================
# 2. ANAGRAFICA CLIENTI
# ==============================================================================
elif st.session_state.pagina_attiva == "clienti":
    st.header("👥 Anagrafica Clienti")

    with st.expander("➕ Aggiungi Nuovo Cliente", expanded=False):
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
                    st.session_state.storico_caricato = True
                    st.success(f"Cliente '{nome}' aggiunto!")
                    st.rerun()
                else:
                    st.warning("Inserisci almeno la denominazione del cliente.")

    if db["clienti"]:
        st.subheader("Elenco Clienti")
        for idx, cli in enumerate(db["clienti"]):
            with st.container(border=True):
                col_info, col_del = st.columns([5, 1], vertical_alignment="center")
                col_info.write(
                    f"**{cli.get('nome', '')}** | P.IVA/CF: `{cli.get('piva', '')}` | SDI: `{cli.get('sdi', '')}`\n"
                    f"Indirizzo: {cli.get('indirizzo', '')}, {cli.get('cap', '')} {cli.get('citta', '')}"
                )
                with col_del:
                    pulsante_elimina_sicuro(
                        stato_key=f"cli_{idx}_{cli.get('nome', '')}",
                        etichetta_avviso=f"Eliminare il cliente '{cli.get('nome', '')}'?",
                        on_conferma=lambda i=idx: db["clienti"].pop(i),
                        key_prefix=f"del_cli_{idx}"
                    )

# ==============================================================================
# 3. ANAGRAFICA FORNITORI
# ==============================================================================
elif st.session_state.pagina_attiva == "fornitori":
    st.header("🏭 Anagrafica Fornitori")

    with st.expander("➕ Aggiungi Nuovo Fornitore", expanded=False):
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
                    st.session_state.storico_caricato = True
                    st.success(f"Fornitore '{nome}' aggiunto!")
                    st.rerun()
                else:
                    st.warning("Inserisci la Ragione Sociale del fornitore.")

    if db["fornitori"]:
        st.subheader("Elenco Fornitori")
        for idx, forn in enumerate(db["fornitori"]):
            with st.container(border=True):
                col_info, col_del = st.columns([5, 1], vertical_alignment="center")
                col_info.write(
                    f"**{forn.get('nome', '')}** | P.IVA/CF: `{forn.get('piva', '')}` | Categoria: *{forn.get('categoria', '')}*\n"
                    f"Indirizzo: {forn.get('indirizzo', '')} | IBAN: `{forn.get('iban', '')}`"
                )
                with col_del:
                    pulsante_elimina_sicuro(
                        stato_key=f"forn_{idx}_{forn.get('nome', '')}",
                        etichetta_avviso=f"Eliminare il fornitore '{forn.get('nome', '')}'?",
                        on_conferma=lambda i=idx: db["fornitori"].pop(i),
                        key_prefix=f"del_forn_{idx}"
                    )

# ==============================================================================
# 4. MAGAZZINO
# ==============================================================================
elif st.session_state.pagina_attiva == "magazzino":
    st.header("📦 Gestione Magazzino")

    with st.expander("📊 Importa Magazzino da file Excel (.xlsx / .xls)", expanded=False):
        st.caption(
            "Colonne supportate (anche con nomi simili): `codice`, `descrizione`, `tipo`, "
            "`costo_acquisto`, `prezzo_vendita`, `iva`, `giacenza` (o `quantita`). "
            "Se un articolo è già presente, le quantità vengono sommate."
        )
        file_excel = st.file_uploader("Seleziona file Excel", type=["xlsx", "xls"], key="excel_magazzino_up")

        if file_excel is not None and st.button("📥 Importa e Aggiorna Magazzino", key="btn_import_excel_mag", type="primary"):
            try:
                df_xl = pd.read_excel(file_excel)
                df_xl.columns = [str(c).strip().lower().replace(" ", "_") for c in df_xl.columns]

                def pick_col(row, nomi, default=None):
                    for n in nomi:
                        if n in df_xl.columns and pd.notna(row.get(n)):
                            return row.get(n)
                    return default

                inseriti, aggiornati = 0, 0
                for _, row in df_xl.iterrows():
                    desc_val = str(pick_col(row, ["descrizione", "articolo", "nome", "prodotto"], "") or "").strip()
                    if not desc_val:
                        continue

                    cod_val = str(pick_col(row, ["codice", "cod", "sku", "id"], "") or "").strip()
                    tipo_val = str(pick_col(row, ["tipo", "tipologia"], "Prodotto Fisico (con giacenza)") or "Prodotto Fisico (con giacenza)").strip()
                    costo_val = float(pd.to_numeric(pick_col(row, ["costo_acquisto", "costo", "prezzo_acquisto"], 0.0), errors="coerce") or 0.0)
                    vendita_val = float(pd.to_numeric(pick_col(row, ["prezzo_vendita", "prezzo", "listino"], 0.0), errors="coerce") or 0.0)
                    iva_val = int(float(pd.to_numeric(pick_col(row, ["iva", "aliquota_iva"], 10), errors="coerce") or 10))
                    qta_val = float(pd.to_numeric(pick_col(row, ["giacenza", "quantita", "quantità", "qta", "qty"], 0.0), errors="coerce") or 0.0)

                    esito = aggiungi_o_aggiorna_magazzino({
                        "codice": cod_val,
                        "descrizione": desc_val,
                        "tipo": tipo_val,
                        "costo_acquisto": costo_val,
                        "prezzo_vendita": vendita_val,
                        "iva": iva_val,
                        "giacenza": qta_val
                    })
                    if esito == "aggiornato":
                        aggiornati += 1
                    else:
                        inseriti += 1

                st.session_state.storico_caricato = True
                st.success(f"Importazione completata: {inseriti} nuovi articoli inseriti, {aggiornati} già presenti aggiornati con somma quantità.")
                st.rerun()
            except Exception as e:
                st.error(f"Errore durante la lettura del file Excel: {e}")
        
    with st.expander("➕ Aggiungi Articolo / Prestazione", expanded=False):
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
                    esito = aggiungi_o_aggiorna_magazzino({
                        "codice": codice,
                        "descrizione": descrizione,
                        "tipo": tipo,
                        "costo_acquisto": prezzo_acquisto,
                        "prezzo_vendita": prezzo_vendita,
                        "iva": iva_default,
                        "giacenza": giacenza
                    })
                    st.session_state.storico_caricato = True
                    if esito == "aggiornato":
                        st.success(f"Articolo già presente: quantità sommata a '{descrizione}'!")
                    else:
                        st.success(f"Articolo '{descrizione}' salvato!")
                    st.rerun()
                else:
                    st.warning("Inserisci una descrizione.")

    if db["magazzino"]:
        st.subheader("Elenco Articoli")
        for idx, art in enumerate(db["magazzino"]):
            val_giac = float(art.get("costo_acquisto", 0.0)) * float(art.get("giacenza", 0.0))
            with st.container(border=True):
                col_info, col_del = st.columns([5, 1], vertical_alignment="center")
                col_info.write(
                    f"**`{art.get('codice', '')}` — {art.get('descrizione', '')}** ({art.get('tipo', '')})\n"
                    f"Acquisto: **€ {float(art.get('costo_acquisto', 0.0)):.2f}** | "
                    f"Vendita: **€ {float(art.get('prezzo_vendita', 0.0)):.2f}** | "
                    f"IVA: `{art.get('iva', 10)}%` | Giacenza: **{art.get('giacenza', 0)}** | Valore: **€ {val_giac:.2f}**"
                )
                with col_del:
                    pulsante_elimina_sicuro(
                        stato_key=f"mag_{idx}_{art.get('codice', '')}",
                        etichetta_avviso=f"Eliminare l'articolo '{art.get('descrizione', '')}'?",
                        on_conferma=lambda i=idx: db["magazzino"].pop(i),
                        key_prefix=f"del_mag_{idx}"
                    )

# ==============================================================================
# 5. FATTURAZIONE VENDITA (ATTIVA)
# ==============================================================================
elif st.session_state.pagina_attiva == "fatture_attive":
    st.header("🧾 Fatturazione Vendita (Attiva)")

    tab1, tab2 = st.tabs(["➕ Nuova Fattura di Vendita", "📋 Registro Fatture Emesse & Stampa PDF"])

    with tab1:
        if "righe_fattura_attiva" not in st.session_state:
            st.session_state.righe_fattura_attiva = []

        if not db["clienti"]:
            st.caption("Nessun cliente in anagrafica: puoi caricare lo storico dalla Home o aggiungere un cliente.")
        else:
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

                    st.session_state.storico_caricato = True
                    st.session_state.righe_fattura_attiva = []
                    st.success(f"Fattura N. {num_fatt} registrata!")
                    st.rerun()

    with tab2:
        if db["fatture_attive"]:
            st.subheader("Elenco Fatture Attive")
            for idx, f in enumerate(db["fatture_attive"]):
                with st.container(border=True):
                    c_info, c_pdf, c_del = st.columns([3.5, 1.5, 1], vertical_alignment="center")
                    c_info.write(
                        f"**Fatt. {f.get('numero', '')}** — Cliente: **{f.get('cliente_nome', '')}**\n"
                        f"Data: `{f.get('data', '')}` | Scad.: `{f.get('scadenza', '')}` | "
                        f"Totale: **€ {float(f.get('totale', 0.0)):.2f}** | Stato: `{f.get('stato', '')}`"
                    )
                    pdf_bytes = genera_pdf_documento("Fattura", f, db["ditta"])
                    c_pdf.download_button(
                        label="📄 Scarica PDF",
                        data=pdf_bytes,
                        file_name=f"Fattura_{str(f.get('numero', '')).replace('/', '_')}.pdf",
                        mime="application/pdf",
                        key=f"dl_fa_{idx}"
                    )
                    with c_del:
                        pulsante_elimina_sicuro(
                            stato_key=f"fa_{idx}_{f.get('numero', '')}",
                            etichetta_avviso=f"Eliminare la fattura N. {f.get('numero', '')}?",
                            on_conferma=lambda i=idx: db["fatture_attive"].pop(i),
                            key_prefix=f"del_fa_{idx}"
                        )

# ==============================================================================
# 6. FATTURAZIONE ACQUISTI (PASSIVA)
# ==============================================================================
elif st.session_state.pagina_attiva == "fatture_passive":
    st.header("📥 Fatturazione Acquisti (Passiva)")

    with st.expander("➕ Registra Nuova Fattura di Acquisto", expanded=False):
        if not db["fornitori"]:
            st.caption("Nessun fornitore in anagrafica: puoi caricare lo storico dalla Home o aggiungere un fornitore.")
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
                        st.session_state.storico_caricato = True
                        st.success("Fattura passiva registrata!")
                        st.rerun()
                    else:
                        st.warning("Compila numero documento e descrizione.")

    if db["fatture_passive"]:
        st.subheader("Registro Fatture Passive")
        for idx, fp in enumerate(db["fatture_passive"]):
            with st.container(border=True):
                col_info, col_del = st.columns([5, 1], vertical_alignment="center")
                col_info.write(
                    f"**Fatt. {fp.get('numero', '')}** — Fornitore: **{fp.get('fornitore', '')}** | {fp.get('descrizione', '')}\n"
                    f"Data: `{fp.get('data', '')}` | Scad.: `{fp.get('scadenza', '')}` | "
                    f"Totale: **€ {float(fp.get('totale', 0.0)):.2f}** | Stato: `{fp.get('stato', '')}`"
                )
                with col_del:
                    pulsante_elimina_sicuro(
                        stato_key=f"fp_{idx}_{fp.get('numero', '')}",
                        etichetta_avviso=f"Eliminare la fattura acquisto N. {fp.get('numero', '')}?",
                        on_conferma=lambda i=idx: db["fatture_passive"].pop(i),
                        key_prefix=f"del_fp_{idx}"
                    )

# ==============================================================================
# 7. SCADENZARIO
# ==============================================================================
elif st.session_state.pagina_attiva == "scadenzario":
    st.header("📅 Scadenzario Incassi e Pagamenti")

    incassi_aperti = [f for f in db["fatture_attive"] if f.get("stato") == "Da Incassare"]
    pagamenti_aperti = [f for f in db["fatture_passive"] if f.get("stato") == "Da Pagare"]

    tot_incassare = sum(float(f.get("totale", 0.0)) for f in incassi_aperti)
    tot_pagare = sum(float(f.get("totale", 0.0)) for f in pagamenti_aperti)
    saldo_previsto = tot_incassare - tot_pagare

    if st.session_state.storico_caricato or db["fatture_attive"] or db["fatture_passive"]:
        m1, m2, m3 = st.columns(3)
        m1.metric("🟢 Crediti da Incassare", f"€ {tot_incassare:.2f}")
        m2.metric("🔴 Debiti da Pagare", f"€ {tot_pagare:.2f}")
        m3.metric("⚖️ Saldo Netto Previsionale", f"€ {saldo_previsto:.2f}")

        st.divider()
        col_sx, col_dx = st.columns(2)

        with col_sx:
            st.subheader("🟢 Scadenze Clienti (Da Incassare)")
            for idx, f in enumerate(db["fatture_attive"]):
                if f.get("stato") == "Da Incassare":
                    with st.container(border=True):
                        st.write(f"**Fatt. {f.get('numero', '')}** - {f.get('cliente_nome', '')}")
                        st.write(f"Scadenza: `{f.get('scadenza', '')}` | Importo: **€ {float(f.get('totale', 0.0)):.2f}**")
                        b1, b2 = st.columns(2)
                        if b1.button("✅ Incassata", key=f"inc_{idx}"):
                            db["fatture_attive"][idx]["stato"] = "Incassata"
                            st.rerun()
                        if b2.button("🗑️ Elimina", key=f"del_sc_inc_{idx}"):
                            st.session_state.conferma_elimina = f"sc_inc_{idx}_{f.get('numero', '')}"
                            st.rerun()
                        if st.session_state.conferma_elimina == f"sc_inc_{idx}_{f.get('numero', '')}":
                            st.warning(f"⚠️ Eliminare la fattura {f.get('numero', '')}?")
                            k1, k2 = st.columns(2)
                            if k1.button("Conferma", key=f"sc_inc_ok_{idx}", type="primary"):
                                st.session_state.conferma_elimina = None
                                db["fatture_attive"].pop(idx)
                                st.rerun()
                            if k2.button("Annulla", key=f"sc_inc_no_{idx}"):
                                st.session_state.conferma_elimina = None
                                st.rerun()

        with col_dx:
            st.subheader("🔴 Scadenze Fornitori (Da Pagare)")
            for idx, f in enumerate(db["fatture_passive"]):
                if f.get("stato") == "Da Pagare":
                    with st.container(border=True):
                        st.write(f"**Fatt. {f.get('numero', '')}** - {f.get('fornitore', '')}")
                        st.write(f"Scadenza: `{f.get('scadenza', '')}` | Importo: **€ {float(f.get('totale', 0.0)):.2f}**")
                        b1, b2 = st.columns(2)
                        if b1.button("✅ Pagata", key=f"pag_{idx}"):
                            db["fatture_passive"][idx]["stato"] = "Pagata"
                            st.rerun()
                        if b2.button("🗑️ Elimina", key=f"del_sc_pag_{idx}"):
                            st.session_state.conferma_elimina = f"sc_pag_{idx}_{f.get('numero', '')}"
                            st.rerun()
                        if st.session_state.conferma_elimina == f"sc_pag_{idx}_{f.get('numero', '')}":
                            st.warning(f"⚠️ Eliminare la fattura {f.get('numero', '')}?")
                            k1, k2 = st.columns(2)
                            if k1.button("Conferma", key=f"sc_pag_ok_{idx}", type="primary"):
                                st.session_state.conferma_elimina = None
                                db["fatture_passive"].pop(idx)
                                st.rerun()
                            if k2.button("Annulla", key=f"sc_pag_no_{idx}"):
                                st.session_state.conferma_elimina = None
                                st.rerun()

# ==============================================================================
# 8. PREVENTIVI
# ==============================================================================
elif st.session_state.pagina_attiva == "preventivi":
    st.header("📝 Gestione Preventivi & Conversione in Fattura")

    tab_p1, tab_p2 = st.tabs(["➕ Nuovo Preventivo (Offerta)", "📂 Archivio Preventivi & Conversione"])

    with tab_p1:
        if "righe_preventivo" not in st.session_state:
            st.session_state.righe_preventivo = []

        if not db["clienti"]:
            st.caption("Nessun cliente in anagrafica: puoi caricare lo storico dalla Home o aggiungere un cliente.")
        else:
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
                    st.session_state.storico_caricato = True
                    st.session_state.righe_preventivo = []
                    st.success(f"Preventivo {num_prev} salvato!")
                    st.rerun()

    with tab_p2:
        if db["preventivi"]:
            for idx, p in enumerate(db["preventivi"]):
                with st.container(border=True):
                    c_info, c_act1, c_act2, c_del = st.columns([3, 1.3, 1.4, 0.9], vertical_alignment="center")
                    c_info.write(f"**Offerta {p.get('numero', '')}** | Cliente: **{p.get('cliente_nome', '')}** | Data: {p.get('data', '')}")
                    c_info.write(f"Totale: **€ {float(p.get('totale', 0.0)):.2f}** | Stato: `{p.get('stato', '')}`")

                    pdf_prev = genera_pdf_documento("Preventivo", p, db["ditta"])
                    c_act1.download_button(
                        label="📄 PDF",
                        data=pdf_prev,
                        file_name=f"Preventivo_{str(p.get('numero', '')).replace('/', '_')}.pdf",
                        mime="application/pdf",
                        key=f"dl_prev_{idx}"
                    )

                    if p.get("stato") != "Fatturato":
                        if c_act2.button("🔄 Converti", key=f"conv_{idx}"):
                            nuovo_num_fatt = f"{len(db['fatture_attive'])+1}/{str(datetime.now().year)[-2:]}"
                            nuova_fatt_da_prev = p.copy()
                            nuova_fatt_da_prev["numero"] = nuovo_num_fatt
                            nuova_fatt_da_prev["rif_offerta"] = p.get("numero", "")
                            nuova_fatt_da_prev["data"] = date.today().strftime("%d/%m/%Y")
                            nuova_fatt_da_prev["scadenza"] = (date.today() + timedelta(days=30)).strftime("%d/%m/%Y")
                            nuova_fatt_da_prev["intestazione_corpo"] = "Vi rimettiamo regolare fattura per :"
                            nuova_fatt_da_prev["note"] = "saldo"
                            nuova_fatt_da_prev["stato"] = "Da Incassare"
                            db["fatture_attive"].append(nuova_fatt_da_prev)
                            db["preventivi"][idx]["stato"] = "Fatturato"
                            st.success(f"Convertito nella Fattura N. {nuovo_num_fatt} con Riferimento Offerta {p.get('numero', '')}!")
                            st.rerun()

                    with c_del:
                        pulsante_elimina_sicuro(
                            stato_key=f"prev_{idx}_{p.get('numero', '')}",
                            etichetta_avviso=f"Eliminare il preventivo N. {p.get('numero', '')}?",
                            on_conferma=lambda i=idx: db["preventivi"].pop(i),
                            key_prefix=f"del_prev_{idx}"
                        )

