import streamlit as st
import pandas as pd
import json
import base64
import tempfile
import os
from datetime import datetime, date, timedelta
from fpdf import FPDF
from PIL import Image
import re
import xml.etree.ElementTree as ET
import zipfile
import io

def pulisci_testo(val):
    return "" if val is None else str(val).strip()

def valida_cap(val):
    s = pulisci_testo(val)
    if not s:
        return True, ""
    if not re.fullmatch(r"\d{5}", s):
        return False, "Il CAP deve contenere esattamente 5 cifre numeriche."
    return True, ""

def valida_piva(val, obbligatoria=False):
    s = re.sub(r"\s+", "", pulisci_testo(val))
    if not s:
        return (False, "La Partita IVA è obbligatoria.") if obbligatoria else (True, "")
    if not re.fullmatch(r"\d{11}", s):
        return False, "La Partita IVA deve contenere esattamente 11 cifre numeriche."
    return True, ""

def valida_cf_o_piva(val, obbligatorio=False):
    s = re.sub(r"\s+", "", pulisci_testo(val)).upper()
    if not s:
        return (False, "Il Codice Fiscale / P.IVA è obbligatorio.") if obbligatorio else (True, "")
    if re.fullmatch(r"[A-Z0-9]{16}", s):
        return True, ""
    if re.fullmatch(r"\d{11}", s):
        return True, ""
    return False, "Inserisci un Codice Fiscale di 16 caratteri alfanumerici oppure una Partita IVA di 11 cifre."

def valida_iban(val, obbligatorio=False):
    s = re.sub(r"[\s\-]+", "", pulisci_testo(val)).upper()
    if not s:
        return (False, "L'IBAN è obbligatorio.") if obbligatorio else (True, "")
    if not re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]{10,30}", s):
        return False, "Formato IBAN non valido (es. IT + 2 cifre di controllo + coordinate)."
    if s.startswith("IT") and len(s) != 27:
        return False, "Un IBAN italiano (IT) deve avere esattamente 27 caratteri."
    riordinato = s[4:] + s[:4]
    numerico = "".join(str(ord(ch) - 55) if ch.isalpha() else ch for ch in riordinato)
    if int(numerico) % 97 != 1:
        return False, "IBAN non valido: cifra di controllo (MOD-97) errata."
    return True, ""

def valida_sdi(val):
    s = pulisci_testo(val).upper()
    if not s:
        return True, ""
    if not re.fullmatch(r"[A-Z0-9]{7}", s):
        return False, "Il codice SDI deve essere di 7 caratteri alfanumerici (es. 0000000 o JHBM40P)."
    return True, ""

def pick_excel_col(df_cols, row, nomi, default=None):
    for n in nomi:
        if n in df_cols and pd.notna(row.get(n)):
            return row.get(n)
    return default

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

    # 7. Piè di pagina riquadrato
    y9 = y8 + h_tot_body
    h_foot = 23
    w_foot = w_tot
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

def genera_xml_fatturapa(doc_data, ditta_data):
    ns = "http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2"
    ET.register_namespace("p", ns)
    root = ET.Element(f"{{{ns}}}FatturaElettronica", attrib={"versione": "FPR12"})

    def sub(parent, tag, text=None):
        el = ET.SubElement(parent, f"{{{ns}}}{tag}")
        if text is not None:
            el.text = str(text)
        return el

    piva_ced = re.sub(r"\D", "", pulisci_testo(ditta_data.get("piva", ""))) or "00000000000"
    cf_ced = pulisci_testo(ditta_data.get("cf", "")).upper() or piva_ced
    num_fatt = pulisci_testo(doc_data.get("numero", "1"))
    prog_invio = re.sub(r"[^A-Za-z0-9]", "", num_fatt)[:10] or "00001"

    header = sub(root, "FatturaElettronicaHeader")
    dati_trasm = sub(header, "DatiTrasmissione")
    id_trasm = sub(dati_trasm, "IdTrasmittente")
    sub(id_trasm, "IdPaese", "IT")
    sub(id_trasm, "IdCodice", piva_ced)
    sub(dati_trasm, "ProgressivoInvio", prog_invio)
    sub(dati_trasm, "FormatoTrasmissione", "FPR12")

    sdi_cli = pulisci_testo(doc_data.get("cliente_sdi", "")).upper()
    if not re.fullmatch(r"[A-Z0-9]{7}", sdi_cli):
        sdi_cli = "0000000"
    sub(dati_trasm, "CodiceDestinatario", sdi_cli)

    ced = sub(header, "CedentePrestatore")
    ced_anag = sub(ced, "DatiAnagrafici")
    ced_idf = sub(ced_anag, "IdFiscaleIVA")
    sub(ced_idf, "IdPaese", "IT")
    sub(ced_idf, "IdCodice", piva_ced)
    if cf_ced:
        sub(ced_anag, "CodiceFiscale", cf_ced)
    ced_dati_anag = sub(ced_anag, "Anagrafica")
    denom_ced = pulisci_testo(ditta_data.get("denominazione", ""))
    tit_ced = pulisci_testo(ditta_data.get("titolare", ""))
    if denom_ced:
        sub(ced_dati_anag, "Denominazione", denom_ced)
    elif tit_ced:
        parti = tit_ced.split(" ", 1)
        sub(ced_dati_anag, "Nome", parti[0])
        sub(ced_dati_anag, "Cognome", parti[1] if len(parti) > 1 else parti[0])
    sub(ced_anag, "RegimeFiscale", "RF01" if "Forfettario" not in pulisci_testo(ditta_data.get("regime", "")) else "RF19")

    ced_sede = sub(ced, "Sede")
    cap_citta_raw = pulisci_testo(ditta_data.get("cap_citta", ""))
    m_cap = re.search(r"\b(\d{5})\b", cap_citta_raw)
    cap_ced = m_cap.group(1) if m_cap else "00100"
    citta_ced = re.sub(r"^\d{5}\s*[-–]?\s*", "", cap_citta_raw).strip() or "Roma"
    sub(ced_sede, "Indirizzo", pulisci_testo(ditta_data.get("indirizzo", "")) or "N.D.")
    sub(ced_sede, "CAP", cap_ced)
    sub(ced_sede, "Comune", citta_ced)
    sub(ced_sede, "Nazione", "IT")

    cess = sub(header, "CessionarioCommittente")
    cess_anag = sub(cess, "DatiAnagrafici")
    cf_piva_cli = re.sub(r"\s+", "", pulisci_testo(doc_data.get("cliente_piva", ""))).upper()
    if re.fullmatch(r"\d{11}", cf_piva_cli):
        cess_idf = sub(cess_anag, "IdFiscaleIVA")
        sub(cess_idf, "IdPaese", "IT")
        sub(cess_idf, "IdCodice", cf_piva_cli)
    elif cf_piva_cli:
        sub(cess_anag, "CodiceFiscale", cf_piva_cli)

    cess_dati_anag = sub(cess_anag, "Anagrafica")
    sub(cess_dati_anag, "Denominazione", pulisci_testo(doc_data.get("cliente_nome", "")) or "Cliente")

    cess_sede = sub(cess, "Sede")
    cap_cli = pulisci_testo(doc_data.get("cliente_cap", ""))
    if not re.fullmatch(r"\d{5}", cap_cli):
        cap_cli = "00100"
    sub(cess_sede, "Indirizzo", pulisci_testo(doc_data.get("cliente_indirizzo", "")) or "N.D.")
    sub(cess_sede, "CAP", cap_cli)
    sub(cess_sede, "Comune", pulisci_testo(doc_data.get("cliente_citta", "")) or "Roma")
    sub(cess_sede, "Nazione", "IT")

    body = sub(root, "FatturaElettronicaBody")
    dati_gen = sub(body, "DatiGenerali")
    dati_doc = sub(dati_gen, "DatiGeneraliDocumento")
    sub(dati_doc, "TipoDocumento", "TD01")
    sub(dati_doc, "Divisa", "EUR")

    data_raw = pulisci_testo(doc_data.get("data", ""))
    data_iso = date.today().strftime("%Y-%m-%d")
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            data_iso = datetime.strptime(data_raw[:10], fmt).strftime("%Y-%m-%d")
            break
        except ValueError:
            pass
    sub(dati_doc, "Data", data_iso)
    sub(dati_doc, "Numero", num_fatt)

    rit_imp = float(doc_data.get("rit_imp", 0.0) or 0.0)
    rit_perc = float(doc_data.get("rit_perc", 0.0) or 0.0)
    if rit_imp > 0:
        dati_rit = sub(dati_doc, "DatiRitenuta")
        sub(dati_rit, "TipoRitenuta", "RT01")
        sub(dati_rit, "ImportoRitenuta", f"{rit_imp:.2f}")
        sub(dati_rit, "AliquotaRitenuta", f"{rit_perc:.2f}")
        sub(dati_rit, "CausalePagamento", "A")

    tot_doc = float(doc_data.get("totale", 0.0) or 0.0)
    sub(dati_doc, "ImportoTotaleDocumento", f"{tot_doc:.2f}")

    dati_beni = sub(body, "DatiBeniServizi")
    righe = doc_data.get("righe") or []
    riep_map = {}

    for idx_r, r in enumerate(righe, start=1):
        qta_v = float(r.get("qta", 0.0) or 0.0)
        prz_v = float(r.get("prezzo", 0.0) or 0.0)
        iva_v = float(r.get("iva", 10) or 0.0)
        molt = qta_v if qta_v > 0 else 1.0
        prezzo_tot = round(molt * prz_v, 2)
        prezzo_unit = round(prz_v, 2)

        det = sub(dati_beni, "DettaglioLinee")
        sub(det, "NumeroLinea", str(idx_r))
        sub(det, "Descrizione", pulisci_testo(r.get("descrizione", "")) or "Fornitura / Lavorazione")
        if qta_v > 0:
            sub(det, "Quantita", f"{qta_v:.2f}")
        sub(det, "PrezzoUnitario", f"{prezzo_unit:.2f}")
        sub(det, "PrezzoTotale", f"{prezzo_tot:.2f}")
        sub(det, "AliquotaIVA", f"{iva_v:.2f}")

        riep_map[iva_v] = round(riep_map.get(iva_v, 0.0) + prezzo_tot, 2)

    if not riep_map:
        imp_std = float(doc_data.get("imp_std", 0.0) or 0.0)
        al_std = float(doc_data.get("aliq_std", 10) or 10)
        riep_map[al_std] = round(imp_std, 2)

    for aliq, imp_al in riep_map.items():
        imposta_al = round(imp_al * (aliq / 100.0), 2)
        riep = sub(dati_beni, "DatiRiepilogo")
        sub(riep, "AliquotaIVA", f"{aliq:.2f}")
        sub(riep, "ImponibileImporto", f"{imp_al:.2f}")
        sub(riep, "Imposta", f"{imposta_al:.2f}")
        sub(riep, "EsigibilitaIVA", "I")

    iban_ced = re.sub(r"[\s\-]+", "", pulisci_testo(ditta_data.get("iban", ""))).upper()
    dati_pag = sub(body, "DatiPagamento")
    sub(dati_pag, "CondizioniPagamento", "TP02")
    det_pag = sub(dati_pag, "DettaglioPagamento")
    sub(det_pag, "ModalitaPagamento", "MP05" if iban_ced else "MP01")
    sub(det_pag, "ImportoPagamento", f"{tot_doc:.2f}")
    if iban_ced:
        sub(det_pag, "IBAN", iban_ced)

    return ET.tostring(root, encoding="utf-8", xml_declaration=True)

# --- BARRA SUPERIORE NELLE SEZIONI INTERNE ---
if st.session_state.pagina_attiva != "home":
    top_l, col_logo, col_titolo, top_r = st.columns([2, 1, 5, 1.5])
    with top_l:
        if st.button("⬅️ Torna alla Home", key="btn_back_home"):
            vai_a("home")

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
    st.info("Questi dati e il logo aziendale popolano automaticamente il riquadro superiore sinistro, l'area IBAN e il riquadro piè di pagina dei documenti PDF.")

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

    with st.expander("📊 Importa Clienti da file Excel (.xlsx / .xls)", expanded=False):
        st.caption("Colonne supportate: `nome` (o `ragione_sociale`), `indirizzo` (o `via`), `cap`, `citta`, `piva` (o `cf`/`codice_fiscale`), `sdi`, `pagamento`.")
        file_xl_cli = st.file_uploader("Seleziona file Excel Clienti", type=["xlsx", "xls"], key="xl_cli_up")
        if file_xl_cli is not None and st.button("📥 Importa Clienti", key="btn_xl_cli", type="primary"):
            try:
                df_c = pd.read_excel(file_xl_cli)
                df_c.columns = [str(c).strip().lower().replace(" ", "_") for c in df_c.columns]
                imp_ok, scartati = 0, []
                for idx_r, row in df_c.iterrows():
                    nome_r = pulisci_testo(pick_excel_col(df_c.columns, row, ["nome", "ragione_sociale", "spettabile", "cliente"], ""))
                    if not nome_r:
                        scartati.append(f"Riga {idx_r+2}: denominazione mancante")
                        continue
                    cap_r = pulisci_testo(pick_excel_col(df_c.columns, row, ["cap"], ""))
                    cf_r = pulisci_testo(pick_excel_col(df_c.columns, row, ["piva", "cf", "codice_fiscale", "partita_iva"], ""))
                    sdi_r = pulisci_testo(pick_excel_col(df_c.columns, row, ["sdi", "codice_sdi"], "0000000")).upper()

                    ok1, e1 = valida_cap(cap_r)
                    ok2, e2 = valida_cf_o_piva(cf_r, obbligatorio=True)
                    ok3, e3 = valida_sdi(sdi_r)
                    if not (ok1 and ok2 and ok3):
                        motivo = "; ".join([m for ok, m in [(ok1, e1), (ok2, e2), (ok3, e3)] if not ok])
                        scartati.append(f"Riga {idx_r+2} ({nome_r}): {motivo}")
                        continue

                    db["clienti"].append({
                        "id": len(db["clienti"]) + 1,
                        "nome": nome_r,
                        "indirizzo": pulisci_testo(pick_excel_col(df_c.columns, row, ["indirizzo", "via"], "")),
                        "cap": cap_r,
                        "citta": pulisci_testo(pick_excel_col(df_c.columns, row, ["citta", "città", "comune"], "")),
                        "piva": cf_r.upper(),
                        "sdi": sdi_r or "0000000",
                        "pagamento": pulisci_testo(pick_excel_col(df_c.columns, row, ["pagamento", "regolamento"], "rimessa diretta")) or "rimessa diretta",
                        "ritenuta_4": True
                    })
                    imp_ok += 1

                if imp_ok > 0:
                    st.session_state.storico_caricato = True
                st.success(f"Clienti importati: {imp_ok}")
                if scartati:
                    st.warning("Righe non importate per controlli di validità:\n- " + "\n- ".join(scartati))
                if imp_ok > 0:
                    st.rerun()
            except Exception as e:
                st.error(f"Errore lettura Excel clienti: {e}")

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

    with st.expander("📊 Importa Fornitori da file Excel (.xlsx / .xls)", expanded=False):
        st.caption("Colonne supportate: `nome` (o `ragione_sociale`), `piva` (o `cf`/`partita_iva`), `categoria`, `indirizzo`, `iban`, `note`.")
        file_xl_forn = st.file_uploader("Seleziona file Excel Fornitori", type=["xlsx", "xls"], key="xl_forn_up")
        if file_xl_forn is not None and st.button("📥 Importa Fornitori", key="btn_xl_forn", type="primary"):
            try:
                df_f = pd.read_excel(file_xl_forn)
                df_f.columns = [str(c).strip().lower().replace(" ", "_") for c in df_f.columns]
                imp_ok, scartati = 0, []
                for idx_r, row in df_f.iterrows():
                    nome_r = pulisci_testo(pick_excel_col(df_f.columns, row, ["nome", "ragione_sociale", "fornitore"], ""))
                    if not nome_r:
                        scartati.append(f"Riga {idx_r+2}: denominazione mancante")
                        continue
                    cf_r = pulisci_testo(pick_excel_col(df_f.columns, row, ["piva", "cf", "partita_iva", "codice_fiscale"], ""))
                    iban_r = re.sub(r"[\s\-]+", "", pulisci_testo(pick_excel_col(df_f.columns, row, ["iban"], ""))).upper()

                    ok1, e1 = valida_cf_o_piva(cf_r, obbligatorio=True)
                    ok2, e2 = valida_iban(iban_r, obbligatorio=False)
                    if not (ok1 and ok2):
                        motivo = "; ".join([m for ok, m in [(ok1, e1), (ok2, e2)] if not ok])
                        scartati.append(f"Riga {idx_r+2} ({nome_r}): {motivo}")
                        continue

                    db["fornitori"].append({
                        "id": len(db["fornitori"]) + 1,
                        "nome": nome_r,
                        "piva": cf_r.upper(),
                        "categoria": pulisci_testo(pick_excel_col(df_f.columns, row, ["categoria", "spesa"], "Altro")) or "Altro",
                        "indirizzo": pulisci_testo(pick_excel_col(df_f.columns, row, ["indirizzo", "via"], "")),
                        "iban": iban_r,
                        "note": pulisci_testo(pick_excel_col(df_f.columns, row, ["note", "contatti"], ""))
                    })
                    imp_ok += 1

                if imp_ok > 0:
                    st.session_state.storico_caricato = True
                st.success(f"Fornitori importati: {imp_ok}")
                if scartati:
                    st.warning("Righe non importate per controlli di validità:\n- " + "\n- ".join(scartati))
                if imp_ok > 0:
                    st.rerun()
            except Exception as e:
                st.error(f"Errore lettura Excel fornitori: {e}")

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

    with st.expander("📊 Importa Fatture Attive da file Excel (.xlsx / .xls)", expanded=False):
        st.caption("Colonne supportate: `numero`, `data`, `scadenza`, `cliente_nome` (o `cliente`), `cliente_cap`, `cliente_piva` (o `cf`), `cliente_sdi`, `descrizione`, `imponibile`, `iva`, `totale`, `stato`.")
        file_xl_fa = st.file_uploader("Seleziona file Excel Fatture Attive", type=["xlsx", "xls"], key="xl_fa_up")
        if file_xl_fa is not None and st.button("📥 Importa Fatture Attive", key="btn_xl_fa", type="primary"):
            try:
                df_fa = pd.read_excel(file_xl_fa)
                df_fa.columns = [str(c).strip().lower().replace(" ", "_") for c in df_fa.columns]
                imp_ok, scartati = 0, []
                for idx_r, row in df_fa.iterrows():
                    num_r = pulisci_testo(pick_excel_col(df_fa.columns, row, ["numero", "num_fattura", "n_fattura"], ""))
                    cli_r = pulisci_testo(pick_excel_col(df_fa.columns, row, ["cliente_nome", "cliente", "spettabile"], ""))
                    if not num_r or not cli_r:
                        scartati.append(f"Riga {idx_r+2}: numero fattura o cliente mancante")
                        continue

                    cap_r = pulisci_testo(pick_excel_col(df_fa.columns, row, ["cliente_cap", "cap"], ""))
                    cf_r = pulisci_testo(pick_excel_col(df_fa.columns, row, ["cliente_piva", "piva", "cf", "codice_fiscale"], ""))
                    sdi_r = pulisci_testo(pick_excel_col(df_fa.columns, row, ["cliente_sdi", "sdi"], "")).upper()

                    ok1, e1 = valida_cap(cap_r)
                    ok2, e2 = valida_cf_o_piva(cf_r, obbligatorio=False)
                    ok3, e3 = valida_sdi(sdi_r)
                    if not (ok1 and ok2 and ok3):
                        motivo = "; ".join([m for ok, m in [(ok1, e1), (ok2, e2), (ok3, e3)] if not ok])
                        scartati.append(f"Riga {idx_r+2} (Fatt. {num_r}): {motivo}")
                        continue

                    imp_r = float(pd.to_numeric(pick_excel_col(df_fa.columns, row, ["imponibile"], 0.0), errors="coerce") or 0.0)
                    iva_r = float(pd.to_numeric(pick_excel_col(df_fa.columns, row, ["iva"], 0.0), errors="coerce") or 0.0)
                    tot_raw = pick_excel_col(df_fa.columns, row, ["totale", "importo"], None)
                    tot_r = float(pd.to_numeric(tot_raw, errors="coerce")) if tot_raw is not None else round(imp_r + iva_r, 2)
                    if pd.isna(tot_r):
                        tot_r = round(imp_r + iva_r, 2)

                    desc_r = pulisci_testo(pick_excel_col(df_fa.columns, row, ["descrizione", "oggetto"], "Fornitura / Lavorazione")) or "Fornitura / Lavorazione"
                    data_r = pulisci_testo(pick_excel_col(df_fa.columns, row, ["data", "data_fattura"], date.today().strftime("%d/%m/%Y")))
                    scad_r = pulisci_testo(pick_excel_col(df_fa.columns, row, ["scadenza"], (date.today() + timedelta(days=30)).strftime("%d/%m/%Y")))
                    stato_r = pulisci_testo(pick_excel_col(df_fa.columns, row, ["stato", "stato_pagamento"], "Da Incassare")) or "Da Incassare"

                    db["fatture_attive"].append({
                        "numero": num_r,
                        "data": data_r,
                        "scadenza": scad_r,
                        "rif_offerta": pulisci_testo(pick_excel_col(df_fa.columns, row, ["rif_offerta", "offerta"], "")),
                        "cliente_nome": cli_r,
                        "cliente_indirizzo": pulisci_testo(pick_excel_col(df_fa.columns, row, ["cliente_indirizzo", "indirizzo"], "")),
                        "cliente_cap": cap_r,
                        "cliente_citta": pulisci_testo(pick_excel_col(df_fa.columns, row, ["cliente_citta", "citta"], "")),
                        "cliente_piva": cf_r.upper(),
                        "cliente_sdi": sdi_r,
                        "pagamento": pulisci_testo(pick_excel_col(df_fa.columns, row, ["pagamento", "regolamento"], "rimessa diretta")) or "rimessa diretta",
                        "intestazione_corpo": "Vi rimettiamo regolare fattura per :",
                        "righe": [{"codice_mag": None, "descrizione": desc_r, "qta": 1.0, "prezzo": imp_r if imp_r > 0 else tot_r, "iva": 10}],
                        "imp_4": 0.0,
                        "iva_4": 0.0,
                        "imp_std": imp_r,
                        "aliq_std": 10,
                        "iva_std": iva_r,
                        "rit_perc": 0.0,
                        "rit_imp": 0.0,
                        "totale": round(tot_r, 2),
                        "stato": stato_r,
                        "note": "saldo"
                    })
                    imp_ok += 1

                if imp_ok > 0:
                    st.session_state.storico_caricato = True
                st.success(f"Fatture attive importate: {imp_ok}")
                if scartati:
                    st.warning("Righe non importate per controlli di validità:\n- " + "\n- ".join(scartati))
                if imp_ok > 0:
                    st.rerun()
            except Exception as e:
                st.error(f"Errore lettura Excel fatture attive: {e}")

    tab1, tab2 = st.tabs(["➕ Nuova Fattura di Vendita", "📋 Registro Fatture Emesse & Stampa PDF / XML"])

    with tab1:
        if "righe_fattura_attiva" not in st.session_state:
            st.session_state.righe_fattura_attiva = []

        nuovo_cliente_fatt = st.toggle("🆕 Nuovo cliente (non ancora censito)", value=False, key="toggle_nuovo_cli_fatt")

        col1, col2, col3, col4 = st.columns(4)
        num_fatt = col1.text_input("Numero Fattura", value=f"{len(db['fatture_attive'])+1}/{str(datetime.now().year)[-2:]}")
        data_fatt = col2.date_input("Data Fattura", value=date.today())
        rif_offerta = col3.text_input("Riferimento Offerta", value="")
        scad_fatt = col4.date_input("Scadenza Pagamento", value=date.today() + timedelta(days=30))

        cliente_dati_fa = None
        aggiorna_anag_fa = False

        if nuovo_cliente_fatt:
            st.markdown("**Dati Nuovo Cliente Destinatario**")
            fc1, fc2 = st.columns(2)
            cli_nome_fa = fc1.text_input("Spettabile / Ragione Sociale*", key="fatt_new_nome")
            cli_ind_fa = fc1.text_input("Via e Civico", key="fatt_new_ind")
            cli_cap_fa = fc1.text_input("CAP (5 cifre)", key="fatt_new_cap")
            cli_citta_fa = fc1.text_input("Città", key="fatt_new_citta")

            cli_piva_fa = fc2.text_input("Codice Fiscale / Partita IVA", key="fatt_new_piva")
            cli_sdi_fa = fc2.text_input("Codice SDI (7 caratteri)", value="0000000", key="fatt_new_sdi")
            regolamento = fc2.text_input("Regolamento", value="rimessa diretta", key="fatt_new_pag")
            ritenuta_cli_default = True
            aggiorna_anag_fa = fc2.checkbox("Salva / Aggiorna in Anagrafica Clienti", value=True, key="fatt_new_salva_anag")

            cliente_dati_fa = {
                "nome": pulisci_testo(cli_nome_fa),
                "indirizzo": pulisci_testo(cli_ind_fa),
                "cap": pulisci_testo(cli_cap_fa),
                "citta": pulisci_testo(cli_citta_fa),
                "piva": re.sub(r"\s+", "", pulisci_testo(cli_piva_fa)).upper(),
                "sdi": pulisci_testo(cli_sdi_fa).upper() or "0000000",
                "pagamento": pulisci_testo(regolamento) or "rimessa diretta"
            }
        else:
            if not db["clienti"]:
                st.caption("Nessun cliente in anagrafica: attiva il toggle **Nuovo cliente** qui sopra oppure carica lo storico dalla Home.")
            else:
                c_cli, c_reg = st.columns([2, 1])
                nomi_clienti = [c["nome"] for c in db["clienti"]]
                cliente_scelto_nome = c_cli.selectbox("Spettabile Cliente", nomi_clienti)
                cliente_obj = next(c for c in db["clienti"] if c["nome"] == cliente_scelto_nome)
                regolamento = c_reg.text_input("Regolamento", value=cliente_obj.get("pagamento", "rimessa diretta"))
                ritenuta_cli_default = cliente_obj.get("ritenuta_4", True)

                cliente_dati_fa = {
                    "nome": cliente_obj.get("nome", ""),
                    "indirizzo": cliente_obj.get("indirizzo", ""),
                    "cap": cliente_obj.get("cap", ""),
                    "citta": cliente_obj.get("citta", ""),
                    "piva": cliente_obj.get("piva", ""),
                    "sdi": cliente_obj.get("sdi", "0000000"),
                    "pagamento": pulisci_testo(regolamento) or "rimessa diretta"
                }

        if cliente_dati_fa is not None:
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
                applica_rit = st.checkbox("Applica Ritenuta d'Acconto 4% (- RIT 4%)", value=ritenuta_cli_default)
                rit_perc = 4.0 if applica_rit else 0.0
                rit_imp = round(imponibile_tot * 0.04, 2) if applica_rit else 0.0

                totale_doc = round(imponibile_tot + iva_4 + iva_std - rit_imp, 2)

                st.markdown(f"### Totale Netto Fattura: **€ {totale_doc:.2f}** (Imponibile: € {imponibile_tot:.2f} | IVA: € {iva_4+iva_std:.2f} | -RIT 4%: € {rit_imp:.2f})")

                col_p1, col_p2 = st.columns(2)
                note_fatt = col_p1.text_input("Dicitura finale nel corpo fattura", value="saldo")
                stato_pag = col_p2.selectbox("Stato Pagamento", ["Da Incassare", "Incassata"])

                if st.button("💾 Registra Fattura e Scarica Magazzino", type="primary"):
                    if not pulisci_testo(num_fatt):
                        st.error("Inserisci il Numero Fattura.")
                        st.stop()

                    if nuovo_cliente_fatt:
                        if not cliente_dati_fa["nome"]:
                            st.error("Inserisci la denominazione del Nuovo Cliente.")
                            st.stop()
                        ok1, e1 = valida_cap(cliente_dati_fa["cap"])
                        ok2, e2 = valida_cf_o_piva(cliente_dati_fa["piva"], obbligatorio=False)
                        ok3, e3 = valida_sdi(cliente_dati_fa["sdi"])
                        errori_cli = [m for ok, m in [(ok1, e1), (ok2, e2), (ok3, e3)] if not ok]
                        if errori_cli:
                            for err in errori_cli:
                                st.error(err)
                            st.stop()

                        if aggiorna_anag_fa:
                            piva_fa = cliente_dati_fa["piva"]
                            nome_fa = cliente_dati_fa["nome"]
                            cli_match = None
                            for c_item in db["clienti"]:
                                same_piva = bool(piva_fa and re.sub(r"\s+", "", pulisci_testo(c_item.get("piva", ""))).upper() == piva_fa)
                                same_nome = bool(nome_fa and pulisci_testo(c_item.get("nome", "")).lower() == nome_fa.lower())
                                if same_piva or same_nome:
                                    cli_match = c_item
                                    break

                            dati_cli_agg = {
                                "nome": nome_fa or (cli_match.get("nome", "") if cli_match else ""),
                                "indirizzo": cliente_dati_fa["indirizzo"] or (cli_match.get("indirizzo", "") if cli_match else ""),
                                "cap": cliente_dati_fa["cap"] or (cli_match.get("cap", "") if cli_match else ""),
                                "citta": cliente_dati_fa["citta"] or (cli_match.get("citta", "") if cli_match else ""),
                                "piva": piva_fa or (cli_match.get("piva", "") if cli_match else ""),
                                "sdi": cliente_dati_fa["sdi"] or (cli_match.get("sdi", "0000000") if cli_match else "0000000"),
                                "pagamento": cliente_dati_fa["pagamento"] or (cli_match.get("pagamento", "rimessa diretta") if cli_match else "rimessa diretta"),
                                "ritenuta_4": applica_rit
                            }

                            if cli_match is not None:
                                cli_match.update(dati_cli_agg)
                            else:
                                db["clienti"].append({
                                    "id": len(db["clienti"]) + 1,
                                    **dati_cli_agg
                                })

                    nuova_fatt = {
                        "numero": num_fatt,
                        "data": data_fatt.strftime("%d/%m/%Y"),
                        "scadenza": scad_fatt.strftime("%d/%m/%Y"),
                        "rif_offerta": rif_offerta,
                        "cliente_nome": cliente_dati_fa["nome"],
                        "cliente_indirizzo": cliente_dati_fa["indirizzo"],
                        "cliente_cap": cliente_dati_fa["cap"],
                        "cliente_citta": cliente_dati_fa["citta"],
                        "cliente_piva": cliente_dati_fa["piva"],
                        "cliente_sdi": cliente_dati_fa["sdi"],
                        "pagamento": cliente_dati_fa["pagamento"],
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
            piva_file = re.sub(r"\D", "", pulisci_testo(db["ditta"].get("piva", ""))) or "00000000000"
            for idx, f in enumerate(db["fatture_attive"]):
                with st.container(border=True):
                    c_info, c_pdf, c_xml, c_del = st.columns([3.2, 1.35, 1.25, 0.9], vertical_alignment="center")
                    c_info.write(
                        f"**Fatt. {f.get('numero', '')}** — Cliente: **{f.get('cliente_nome', '')}**\n"
                        f"Data: `{f.get('data', '')}` | Scad.: `{f.get('scadenza', '')}` | "
                        f"Totale: **€ {float(f.get('totale', 0.0)):.2f}** | Stato: `{f.get('stato', '')}`"
                    )
                    pdf_bytes = genera_pdf_documento("Fattura", f, db["ditta"])
                    c_pdf.download_button(
                        label="📄 PDF",
                        data=pdf_bytes,
                        file_name=f"Fattura_{str(f.get('numero', '')).replace('/', '_')}.pdf",
                        mime="application/pdf",
                        key=f"dl_fa_{idx}"
                    )
                    xml_bytes = genera_xml_fatturapa(f, db["ditta"])
                    prog_file = re.sub(r"[^A-Za-z0-9]", "", str(f.get("numero", ""))) or str(idx + 1)
                    c_xml.download_button(
                        label="🧾 XML",
                        data=xml_bytes,
                        file_name=f"IT{piva_file}_{prog_file}.xml",
                        mime="application/xml",
                        key=f"dl_xml_fa_{idx}"
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

    with st.expander("📊 Importa Fatture Passive da file Excel (.xlsx / .xls)", expanded=False):
        st.caption("Colonne supportate: `numero`, `data`, `scadenza`, `fornitore`, `descrizione`, `imponibile`, `iva`, `totale`, `stato`.")
        file_xl_fp = st.file_uploader("Seleziona file Excel Fatture Passive", type=["xlsx", "xls"], key="xl_fp_up")
        if file_xl_fp is not None and st.button("📥 Importa Fatture Passive", key="btn_xl_fp", type="primary"):
            try:
                df_fp = pd.read_excel(file_xl_fp)
                df_fp.columns = [str(c).strip().lower().replace(" ", "_") for c in df_fp.columns]
                imp_ok, scartati = 0, []
                for idx_r, row in df_fp.iterrows():
                    num_r = pulisci_testo(pick_excel_col(df_fp.columns, row, ["numero", "num_fattura", "n_documento"], ""))
                    forn_r = pulisci_testo(pick_excel_col(df_fp.columns, row, ["fornitore", "ragione_sociale"], ""))
                    desc_r = pulisci_testo(pick_excel_col(df_fp.columns, row, ["descrizione", "oggetto"], ""))
                    if not num_r or not forn_r or not desc_r:
                        scartati.append(f"Riga {idx_r+2}: numero, fornitore o descrizione mancanti")
                        continue

                    imp_r = float(pd.to_numeric(pick_excel_col(df_fp.columns, row, ["imponibile"], 0.0), errors="coerce") or 0.0)
                    iva_r = float(pd.to_numeric(pick_excel_col(df_fp.columns, row, ["iva"], 0.0), errors="coerce") or 0.0)
                    tot_raw = pick_excel_col(df_fp.columns, row, ["totale", "importo"], None)
                    tot_r = float(pd.to_numeric(tot_raw, errors="coerce")) if tot_raw is not None else round(imp_r + iva_r, 2)
                    if pd.isna(tot_r) or tot_r < 0:
                        scartati.append(f"Riga {idx_r+2} (Fatt. {num_r}): importo non valido")
                        continue

                    data_r = pulisci_testo(pick_excel_col(df_fp.columns, row, ["data", "data_fattura"], date.today().strftime("%d/%m/%Y")))
                    scad_r = pulisci_testo(pick_excel_col(df_fp.columns, row, ["scadenza"], (date.today() + timedelta(days=30)).strftime("%d/%m/%Y")))
                    stato_r = pulisci_testo(pick_excel_col(df_fp.columns, row, ["stato", "stato_pagamento"], "Da Pagare")) or "Da Pagare"

                    db["fatture_passive"].append({
                        "numero": num_r,
                        "data": data_r,
                        "scadenza": scad_r,
                        "fornitore": forn_r,
                        "descrizione": desc_r,
                        "imponibile": round(imp_r, 2),
                        "iva": round(iva_r, 2),
                        "totale": round(tot_r, 2),
                        "stato": stato_r
                    })
                    imp_ok += 1

                if imp_ok > 0:
                    st.session_state.storico_caricato = True
                st.success(f"Fatture passive importate: {imp_ok}")
                if scartati:
                    st.warning("Righe non importate per controlli di validità:\n- " + "\n- ".join(scartati))
                if imp_ok > 0:
                    st.rerun()
            except Exception as e:
                st.error(f"Errore lettura Excel fatture passive: {e}")

    with st.expander("📄 Importa Fatture Passive da file XML / ZIP (FatturaPA)", expanded=False):
        st.caption("Carica uno o più file `.xml` oppure un archivio `.zip` scaricato dal portale.")
        files_xml_fp = st.file_uploader(
            "Seleziona file XML o ZIP Fatture Passive",
            type=["xml", "zip"],
            accept_multiple_files=True,
            key="xml_fp_up"
        )

        def _strip_ns(tag):
            return tag.split("}", 1)[-1] if "}" in tag else tag

        def _trova_testo(elem, percorso_tag):
            curr = elem
            for t in percorso_tag:
                if curr is None:
                    return ""
                trovato = next((c for c in curr if _strip_ns(c.tag) == t), None)
                curr = trovato
            return pulisci_testo(curr.text) if (curr is not None and curr.text) else ""

        def _parse_data_xml(s_data):
            s = pulisci_testo(s_data)
            if not s:
                return date.today().strftime("%d/%m/%Y")
            for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
                try:
                    return datetime.strptime(s[:10], fmt).strftime("%d/%m/%Y")
                except ValueError:
                    pass
            return s

        def _estrai_fattura_da_xml_bytes(raw_bytes, nome_file=""):
            testo_xml = raw_bytes.decode("utf-8", errors="replace").lstrip("\ufeff").strip()
            root = ET.fromstring(testo_xml.encode("utf-8"))

            cedente = None
            corpi = []
            for el in root.iter():
                nome_tag = _strip_ns(el.tag)
                if nome_tag == "CedentePrestatore" and cedente is None:
                    cedente = el
                elif nome_tag == "FatturaElettronicaBody":
                    corpi.append(el)

            forn_nome = ""
            if cedente is not None:
                forn_nome = (
                    _trova_testo(cedente, ["DatiAnagrafici", "Anagrafica", "Denominazione"])
                    or " ".join([
                        _trova_testo(cedente, ["DatiAnagrafici", "Anagrafica", "Nome"]),
                        _trova_testo(cedente, ["DatiAnagrafici", "Anagrafica", "Cognome"])
                    ]).strip()
                )

            risultati = []
            for body in corpi:
                dati_gen = next((c for c in body if _strip_ns(c.tag) == "DatiGenerali"), None)
                dati_doc = next((c for c in dati_gen if _strip_ns(c.tag) == "DatiGeneraliDocumento"), None) if dati_gen is not None else None

                num_doc = _trova_testo(dati_doc, ["Numero"]) if dati_doc is not None else ""
                data_doc = _parse_data_xml(_trova_testo(dati_doc, ["Data"])) if dati_doc is not None else date.today().strftime("%d/%m/%Y")
                tot_doc_raw = _trova_testo(dati_doc, ["ImportoTotaleDocumento"]) if dati_doc is not None else ""

                scad_doc = (date.today() + timedelta(days=30)).strftime("%d/%m/%Y")
                for el in body.iter():
                    if _strip_ns(el.tag) == "DettaglioPagamento":
                        dt_scad = _trova_testo(el, ["DataScadenzaPagamento"])
                        if dt_scad:
                            scad_doc = _parse_data_xml(dt_scad)
                            break

                descrizioni = []
                for el in body.iter():
                    if _strip_ns(el.tag) == "DettaglioLinee":
                        d_riga = _trova_testo(el, ["Descrizione"])
                        if d_riga:
                            descrizioni.append(d_riga)
                desc_unica = " | ".join(descrizioni[:3]) if descrizioni else (f"Fattura XML {nome_file}" if nome_file else "Fattura XML")
                if len(desc_unica) > 180:
                    desc_unica = desc_unica[:177] + "..."

                imp_tot = 0.0
                iva_tot = 0.0
                trovato_riep = False
                for el in body.iter():
                    if _strip_ns(el.tag) == "DatiRiepilogo":
                        trovato_riep = True
                        imp_s = _trova_testo(el, ["ImponibileImporto"])
                        iva_s = _trova_testo(el, ["Imposta"])
                        try:
                            imp_tot += float(imp_s.replace(",", ".")) if imp_s else 0.0
                        except ValueError:
                            pass
                        try:
                            iva_tot += float(iva_s.replace(",", ".")) if iva_s else 0.0
                        except ValueError:
                            pass

                if not trovato_riep:
                    for el in body.iter():
                        if _strip_ns(el.tag) == "DettaglioLinee":
                            pt_s = _trova_testo(el, ["PrezzoTotale"])
                            al_s = _trova_testo(el, ["AliquotaIVA"])
                            try:
                                pt_v = float(pt_s.replace(",", ".")) if pt_s else 0.0
                                al_v = float(al_s.replace(",", ".")) if al_s else 0.0
                                imp_tot += pt_v
                                iva_tot += round(pt_v * (al_v / 100.0), 2)
                            except ValueError:
                                pass

                try:
                    tot_val = float(tot_doc_raw.replace(",", ".")) if tot_doc_raw else round(imp_tot + iva_tot, 2)
                except ValueError:
                    tot_val = round(imp_tot + iva_tot, 2)

                risultati.append({
                    "numero": num_doc or nome_file or "XML-DOC",
                    "data": data_doc,
                    "scadenza": scad_doc,
                    "fornitore": forn_nome or "Fornitore XML",
                    "descrizione": desc_unica,
                    "imponibile": round(imp_tot, 2),
                    "iva": round(iva_tot, 2),
                    "totale": round(tot_val, 2),
                    "stato": "Da Pagare"
                })
            return risultati

        if files_xml_fp and st.button("📥 Importa XML / ZIP Selezionati", key="btn_xml_fp", type="primary"):
            imp_ok, errori_xml = 0, []
            for up_f in files_xml_fp:
                nome_up = up_f.name
                raw_up = up_f.read()
                try:
                    if nome_up.lower().endswith(".zip"):
                        with zipfile.ZipFile(io.BytesIO(raw_up)) as zf:
                            for member in zf.namelist():
                                if member.lower().endswith(".xml") and not member.startswith("__MACOSX"):
                                    try:
                                        estratti = _estrai_fattura_da_xml_bytes(zf.read(member), member)
                                        for voce_fp in estratti:
                                            db["fatture_passive"].append(voce_fp)
                                            imp_ok += 1
                                    except Exception as e_m:
                                        errori_xml.append(f"{nome_up} -> {member}: {e_m}")
                    else:
                        estratti = _estrai_fattura_da_xml_bytes(raw_up, nome_up)
                        for voce_fp in estratti:
                            db["fatture_passive"].append(voce_fp)
                            imp_ok += 1
                except Exception as e_f:
                    errori_xml.append(f"{nome_up}: {e_f}")

            if imp_ok > 0:
                st.session_state.storico_caricato = True
            st.success(f"Fatture passive importate da XML/ZIP: {imp_ok}")
            if errori_xml:
                st.warning("Alcuni file non sono stati letti:\n- " + "\n- ".join(errori_xml))
            if imp_ok > 0:
                st.rerun()

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

    with st.expander("📊 Importa Preventivi da file Excel (.xlsx / .xls)", expanded=False):
        st.caption("Colonne supportate: `numero` (o `offerta`), `data`, `validita` (o `scadenza`), `cliente_nome` (o `cliente`), `cliente_cap`, `cliente_piva` (o `cf`), `cliente_sdi`, `descrizione`, `imponibile`, `iva`, `totale`, `stato`.")
        file_xl_prev = st.file_uploader("Seleziona file Excel Preventivi", type=["xlsx", "xls"], key="xl_prev_up")
        if file_xl_prev is not None and st.button("📥 Importa Preventivi", key="btn_xl_prev", type="primary"):
            try:
                df_pr = pd.read_excel(file_xl_prev)
                df_pr.columns = [str(c).strip().lower().replace(" ", "_") for c in df_pr.columns]
                imp_ok, scartati = 0, []
                for idx_r, row in df_pr.iterrows():
                    num_r = pulisci_testo(pick_excel_col(df_pr.columns, row, ["numero", "offerta", "num_offerta"], ""))
                    cli_r = pulisci_testo(pick_excel_col(df_pr.columns, row, ["cliente_nome", "cliente", "destinatario"], ""))
                    if not num_r or not cli_r:
                        scartati.append(f"Riga {idx_r+2}: numero offerta o cliente mancante")
                        continue

                    cap_r = pulisci_testo(pick_excel_col(df_pr.columns, row, ["cliente_cap", "cap"], ""))
                    cf_r = pulisci_testo(pick_excel_col(df_pr.columns, row, ["cliente_piva", "piva", "cf", "codice_fiscale"], ""))
                    sdi_r = pulisci_testo(pick_excel_col(df_pr.columns, row, ["cliente_sdi", "sdi"], "")).upper()

                    ok1, e1 = valida_cap(cap_r)
                    ok2, e2 = valida_cf_o_piva(cf_r, obbligatorio=False)
                    ok3, e3 = valida_sdi(sdi_r)
                    if not (ok1 and ok2 and ok3):
                        motivo = "; ".join([m for ok, m in [(ok1, e1), (ok2, e2), (ok3, e3)] if not ok])
                        scartati.append(f"Riga {idx_r+2} (Offerta {num_r}): {motivo}")
                        continue

                    imp_r = float(pd.to_numeric(pick_excel_col(df_pr.columns, row, ["imponibile"], 0.0), errors="coerce") or 0.0)
                    iva_r = float(pd.to_numeric(pick_excel_col(df_pr.columns, row, ["iva"], 0.0), errors="coerce") or 0.0)
                    tot_raw = pick_excel_col(df_pr.columns, row, ["totale", "importo"], None)
                    tot_r = float(pd.to_numeric(tot_raw, errors="coerce")) if tot_raw is not None else round(imp_r + iva_r, 2)
                    if pd.isna(tot_r) or tot_r < 0:
                        scartati.append(f"Riga {idx_r+2} (Offerta {num_r}): importo non valido")
                        continue

                    desc_r = pulisci_testo(pick_excel_col(df_pr.columns, row, ["descrizione", "oggetto"], "Offerta / Preventivo")) or "Offerta / Preventivo"
                    data_r = pulisci_testo(pick_excel_col(df_pr.columns, row, ["data", "data_offerta"], date.today().strftime("%d/%m/%Y")))
                    scad_r = pulisci_testo(pick_excel_col(df_pr.columns, row, ["validita", "validità", "scadenza"], (date.today() + timedelta(days=15)).strftime("%d/%m/%Y")))
                    stato_r = pulisci_testo(pick_excel_col(df_pr.columns, row, ["stato"], "In Attesa")) or "In Attesa"

                    db["preventivi"].append({
                        "numero": num_r,
                        "data": data_r,
                        "scadenza": scad_r,
                        "rif_offerta": num_r,
                        "cliente_nome": cli_r,
                        "cliente_indirizzo": pulisci_testo(pick_excel_col(df_pr.columns, row, ["cliente_indirizzo", "indirizzo"], "")),
                        "cliente_cap": cap_r,
                        "cliente_citta": pulisci_testo(pick_excel_col(df_pr.columns, row, ["cliente_citta", "citta"], "")),
                        "cliente_piva": cf_r.upper(),
                        "cliente_sdi": sdi_r,
                        "pagamento": pulisci_testo(pick_excel_col(df_pr.columns, row, ["pagamento", "regolamento"], "rimessa diretta")) or "rimessa diretta",
                        "intestazione_corpo": "Vi rimettiamo nostra migliore offerta per :",
                        "righe": [{"codice_mag": None, "descrizione": desc_r, "qta": 1.0, "prezzo": imp_r if imp_r > 0 else tot_r, "iva": 10}],
                        "imp_4": 0.0,
                        "iva_4": 0.0,
                        "imp_std": imp_r,
                        "aliq_std": 10,
                        "iva_std": iva_r,
                        "rit_perc": 0.0,
                        "rit_imp": 0.0,
                        "totale": round(tot_r, 2),
                        "stato": stato_r,
                        "note": ""
                    })
                    imp_ok += 1

                if imp_ok > 0:
                    st.session_state.storico_caricato = True
                st.success(f"Preventivi importati: {imp_ok}")
                if scartati:
                    st.warning("Righe non importate per controlli di validità:\n- " + "\n- ".join(scartati))
                if imp_ok > 0:
                    st.rerun()
            except Exception as e:
                st.error(f"Errore lettura Excel preventivi: {e}")

    tab_p1, tab_p2 = st.tabs(["➕ Nuovo Preventivo (Offerta)", "📂 Archivio Preventivi & Conversione"])

    with tab_p1:
        if "righe_preventivo" not in st.session_state:
            st.session_state.righe_preventivo = []

        nuovo_cliente_prev = st.toggle("🆕 Nuovo cliente (non ancora censito)", value=False, key="toggle_nuovo_cli_prev")

        c1, c2, c3 = st.columns(3)
        num_prev = c1.text_input("Numero Offerta / Preventivo", value=f"{len(db['preventivi'])+1}/{str(datetime.now().year)[-2:]}")
        data_prev = c2.date_input("Data Offerta", value=date.today())
        validita_prev = c3.date_input("Valido fino al", value=date.today() + timedelta(days=15))

        salva_in_anagrafica = False
        cliente_dati = None

        if nuovo_cliente_prev:
            st.markdown("**Dati Nuovo Cliente Destinatario**")
            nc1, nc2 = st.columns(2)
            cli_nome_new = nc1.text_input("Spettabile / Ragione Sociale*", key="prev_new_nome")
            cli_ind_new = nc1.text_input("Via e Civico", key="prev_new_ind")
            cli_cap_new = nc1.text_input("CAP (5 cifre)", key="prev_new_cap")
            cli_citta_new = nc1.text_input("Città", key="prev_new_citta")

            cli_piva_new = nc2.text_input("Codice Fiscale / Partita IVA", key="prev_new_piva")
            cli_sdi_new = nc2.text_input("Codice SDI (7 caratteri)", value="0000000", key="prev_new_sdi")
            cli_pag_new = nc2.text_input("Regolamento", value="rimessa diretta", key="prev_new_pag")
            salva_in_anagrafica = nc2.checkbox("Salva anche in Anagrafica Clienti", value=False, key="prev_new_salva_anag")

            cliente_dati = {
                "nome": pulisci_testo(cli_nome_new),
                "indirizzo": pulisci_testo(cli_ind_new),
                "cap": pulisci_testo(cli_cap_new),
                "citta": pulisci_testo(cli_citta_new),
                "piva": re.sub(r"\s+", "", pulisci_testo(cli_piva_new)).upper(),
                "sdi": pulisci_testo(cli_sdi_new).upper() or "0000000",
                "pagamento": pulisci_testo(cli_pag_new) or "rimessa diretta"
            }
        else:
            if not db["clienti"]:
                st.caption("Nessun cliente in anagrafica: attiva il toggle **Nuovo cliente** qui sopra oppure carica lo storico dalla Home.")
            else:
                cliente_prev_nome = st.selectbox("Cliente Destinatario", [c["nome"] for c in db["clienti"]], key="prev_cli")
                cliente_prev_obj = next(c for c in db["clienti"] if c["nome"] == cliente_prev_nome)
                cliente_dati = {
                    "nome": cliente_prev_obj.get("nome", ""),
                    "indirizzo": cliente_prev_obj.get("indirizzo", ""),
                    "cap": cliente_prev_obj.get("cap", ""),
                    "citta": cliente_prev_obj.get("citta", ""),
                    "piva": cliente_prev_obj.get("piva", ""),
                    "sdi": cliente_prev_obj.get("sdi", "0000000"),
                    "pagamento": cliente_prev_obj.get("pagamento", "rimessa diretta")
                }

        if cliente_dati is not None:
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
                    if not pulisci_testo(num_prev):
                        st.error("Inserisci il Numero Offerta / Preventivo.")
                        st.stop()

                    if nuovo_cliente_prev:
                        if not cliente_dati["nome"]:
                            st.error("Inserisci la denominazione del Nuovo Cliente.")
                            st.stop()
                        ok1, e1 = valida_cap(cliente_dati["cap"])
                        ok2, e2 = valida_cf_o_piva(cliente_dati["piva"], obbligatorio=False)
                        ok3, e3 = valida_sdi(cliente_dati["sdi"])
                        errori_cli = [m for ok, m in [(ok1, e1), (ok2, e2), (ok3, e3)] if not ok]
                        if errori_cli:
                            for err in errori_cli:
                                st.error(err)
                            st.stop()

                        if salva_in_anagrafica:
                            gia_presente = any(
                                str(c.get("nome", "")).strip().lower() == cliente_dati["nome"].lower()
                                for c in db["clienti"]
                            )
                            if not gia_presente:
                                db["clienti"].append({
                                    "id": len(db["clienti"]) + 1,
                                    "nome": cliente_dati["nome"],
                                    "indirizzo": cliente_dati["indirizzo"],
                                    "cap": cliente_dati["cap"],
                                    "citta": cliente_dati["citta"],
                                    "piva": cliente_dati["piva"],
                                    "sdi": cliente_dati["sdi"],
                                    "pagamento": cliente_dati["pagamento"],
                                    "ritenuta_4": True
                                })

                    db["preventivi"].append({
                        "numero": num_prev,
                        "data": data_prev.strftime("%d/%m/%Y"),
                        "scadenza": validita_prev.strftime("%d/%m/%Y"),
                        "rif_offerta": num_prev,
                        "cliente_nome": cliente_dati["nome"],
                        "cliente_indirizzo": cliente_dati["indirizzo"],
                        "cliente_cap": cliente_dati["cap"],
                        "cliente_citta": cliente_dati["citta"],
                        "cliente_piva": cliente_dati["piva"],
                        "cliente_sdi": cliente_dati["sdi"],
                        "pagamento": cliente_dati["pagamento"],
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
                            ok1, e1 = valida_cap(p.get("cliente_cap", ""))
                            ok2, e2 = valida_cf_o_piva(p.get("cliente_piva", ""), obbligatorio=False)
                            ok3, e3 = valida_sdi(p.get("cliente_sdi", ""))
                            errori_conv = [m for ok, m in [(ok1, e1), (ok2, e2), (ok3, e3)] if not ok]
                            if errori_conv:
                                for err in errori_conv:
                                    st.error(err)
                                st.stop()

                            # Aggiorna o inserisce i dati del preventivo nell'anagrafica Clienti
                            nome_cli_p = pulisci_testo(p.get("cliente_nome", ""))
                            piva_cli_p = re.sub(r"\s+", "", pulisci_testo(p.get("cliente_piva", ""))).upper()
                            cli_match = None
                            for c_item in db["clienti"]:
                                same_piva = bool(piva_cli_p and re.sub(r"\s+", "", pulisci_testo(c_item.get("piva", ""))).upper() == piva_cli_p)
                                same_nome = bool(nome_cli_p and pulisci_testo(c_item.get("nome", "")).lower() == nome_cli_p.lower())
                                if same_piva or same_nome:
                                    cli_match = c_item
                                    break

                            dati_cli_agg = {
                                "nome": nome_cli_p or (cli_match.get("nome", "") if cli_match else ""),
                                "indirizzo": pulisci_testo(p.get("cliente_indirizzo", "")) or (cli_match.get("indirizzo", "") if cli_match else ""),
                                "cap": pulisci_testo(p.get("cliente_cap", "")) or (cli_match.get("cap", "") if cli_match else ""),
                                "citta": pulisci_testo(p.get("cliente_citta", "")) or (cli_match.get("citta", "") if cli_match else ""),
                                "piva": piva_cli_p or (cli_match.get("piva", "") if cli_match else ""),
                                "sdi": pulisci_testo(p.get("cliente_sdi", "")).upper() or (cli_match.get("sdi", "0000000") if cli_match else "0000000"),
                                "pagamento": pulisci_testo(p.get("pagamento", "")) or (cli_match.get("pagamento", "rimessa diretta") if cli_match else "rimessa diretta"),
                            }

                            if cli_match is not None:
                                cli_match.update(dati_cli_agg)
                            elif dati_cli_agg["nome"]:
                                db["clienti"].append({
                                    "id": len(db["clienti"]) + 1,
                                    **dati_cli_agg,
                                    "ritenuta_4": True
                                })

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
                            st.session_state.storico_caricato = True
                            st.success(f"Convertito nella Fattura N. {nuovo_num_fatt} e anagrafica Clienti aggiornata!")
                            st.rerun()

                    with c_del:
                        pulsante_elimina_sicuro(
                            stato_key=f"prev_{idx}_{p.get('numero', '')}",
                            etichetta_avviso=f"Eliminare il preventivo N. {p.get('numero', '')}?",
                            on_conferma=lambda i=idx: db["preventivi"].pop(i),
                            key_prefix=f"del_prev_{idx}"
                        )
