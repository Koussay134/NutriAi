import streamlit as st
from google import genai
from PIL import Image
import json
import os
from datetime import datetime, timedelta
import uuid

# --- 1. CONFIGURAZIONE APP E STATO ---
st.set_page_config(page_title="NutriAI Pro", page_icon="📱", layout="centered")

API_KEY = st.secrets["GEMINI_API_KEY"]
FILE_STORICO = "database_pasti.json"
FILE_IMPOSTAZIONI = "impostazioni.json"
FILE_PREFERITI = "preferiti.json"

# Inizializzazione variabili di stato per la modifica in tempo reale
if "draft_meal" not in st.session_state:
    st.session_state.draft_meal = None

# --- INIEZIONE CSS (UI/UX DARK TECH & CLEAN) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
    .stApp { background-color: #0B0F17; color: #E2E8F0; }
    header, footer {visibility: hidden;}
    
    /* Card ed Expander */
    div[data-testid="stExpander"], div[data-testid="stForm"], .preset-card {
        background-color: #161B26 !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 16px !important;
    }
    div[data-testid="stExpander"] details { border: none !important; }
    div[data-testid="stExpander"] summary { color: #E2E8F0 !important; font-weight: 600 !important; }

    /* Dropzone Upload */
    [data-testid="stFileUploadDropzone"] {
        border: 2px dashed rgba(255, 255, 255, 0.2) !important;
        border-radius: 16px !important;
        background-color: #161B26 !important;
        padding: 40px !important;
        transition: all 0.3s ease;
    }
    [data-testid="stFileUploadDropzone"]:hover { border-color: #10B981 !important; background-color: #1A2433 !important; }
    [data-testid="stFileUploadDropzone"] small { display: none !important; }
    [data-testid="stFileUploadDropzone"] span { color: #94A3B8 !important; font-size: 16px; }

    /* Input Fields */
    input[type="number"], input[type="text"], textarea {
        background-color: #0B0F17 !important;
        color: #E2E8F0 !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        border-radius: 8px !important;
    }
    
    /* Tabs stile Apple Segmented Control (Occupano tutta la riga) */
    .stTabs [data-baseweb="tab-list"] { 
        display: flex;
        width: 100%;
        background-color: #1C1C1E;
        border-radius: 12px;
        padding: 4px;
        gap: 2px;
    }
    .stTabs [data-baseweb="tab"] {
        flex: 1;
        display: flex;
        justify-content: center;
        background-color: transparent;
        border: none;
        border-radius: 10px;
        padding: 10px 0px; 
        color: #8E8E93;
        font-weight: 600;
        font-size: 14px;
    }
    .stTabs [aria-selected="true"] { 
        background-color: #2C2C2E !important;
        color: #FFFFFF !important; 
        box-shadow: 0 2px 4px rgba(0,0,0,0.3) !important;
    }</style>
""", unsafe_allow_html=True)

# --- 2. GESTIONE DATI PERMANENTI ---
def carica_dati(file_path, default_data):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default_data

def salva_dati(file_path, dati):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(dati, f, indent=4)

storico = carica_dati(FILE_STORICO, [])
preferiti = carica_dati(FILE_PREFERITI, [])
impostazioni = carica_dati(FILE_IMPOSTAZIONI, {
    "target_cal": 2800, "target_pro": 160, "target_carb": 350, "target_fat": 80
})

# --- 3. CALCOLI GIORNALIERI E COMPONENTI VISUALI ---
oggi = str(datetime.now().date())
pasti_oggi = [p for p in storico if p["data"] == oggi]

tot_cal = sum(p["cal"] for p in pasti_oggi)
tot_pro = sum(p["pro"] for p in pasti_oggi)
tot_carb = sum(p["carb"] for p in pasti_oggi)
tot_fat = sum(p["fat"] for p in pasti_oggi)

def render_apple_dashboard(cal, pro, carb, fat, t_cal, t_pro, t_carb, t_fat):
    perc_cal = min((cal / t_cal) * 100, 100) if t_cal > 0 else 0
    perc_carb = min((carb / t_carb) * 100, 100) if t_carb > 0 else 0
    perc_pro = min((pro / t_pro) * 100, 100) if t_pro > 0 else 0
    perc_fat = min((fat / t_fat) * 100, 100) if t_fat > 0 else 0
    
    c_cal = "#FA114F"
    c_carb = "#C462FF"
    c_pro = "#00E5FF"
    c_fat = "#B4FF00"
    
    html = f"""<div style="display: flex; flex-direction: column; gap: 15px; margin-bottom: 25px;">
<div style="background-color: #1C1C1E; border-radius: 20px; padding: 20px; display: flex; align-items: center;">
    <div style="position: relative; width: 75px; height: 75px; border-radius: 50%; background: conic-gradient({c_cal} {perc_cal}%, #330010 0); display: flex; align-items: center; justify-content: center; margin-right: 20px;">
        <div style="width: 53px; height: 53px; border-radius: 50%; background-color: #1C1C1E;"></div>
        <div style="position: absolute; color: {c_cal}; font-size: 24px; font-weight: bold;">➔</div>
    </div>
    <div>
        <div style="color: #FFFFFF; font-size: 16px; font-weight: 500; margin-bottom: 2px;">Calorie</div>
        <div style="color: {c_cal}; font-size: 26px; font-weight: 800; letter-spacing: 0.5px;">{cal}<span style="font-size: 16px; font-weight: 600; color: #8E8E93;"> /{t_cal} KCAL</span></div>
    </div>
</div>
<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
    <div style="background-color: #1C1C1E; border-radius: 20px; padding: 15px;">
        <div style="color: #FFFFFF; font-size: 15px; font-weight: 600; margin-bottom: 12px;">Carboidrati</div>
        <div style="color: {c_carb}; font-size: 22px; font-weight: 700; margin-bottom: 12px; letter-spacing: 0.5px;">{carb}<span style="color: #8E8E93; font-size:14px; font-weight:600;"> /{t_carb}g</span></div>
        <div style="width: 100%; height: 5px; background-color: #2C2C2E; border-radius: 3px; overflow: hidden;">
            <div style="width: {perc_carb}%; height: 100%; background-color: {c_carb};"></div>
        </div>
    </div>
    <div style="background-color: #1C1C1E; border-radius: 20px; padding: 15px;">
        <div style="color: #FFFFFF; font-size: 15px; font-weight: 600; margin-bottom: 12px;">Proteine</div>
        <div style="color: {c_pro}; font-size: 22px; font-weight: 700; margin-bottom: 12px; letter-spacing: 0.5px;">{pro}<span style="color: #8E8E93; font-size:14px; font-weight:600;"> /{t_pro}g</span></div>
        <div style="width: 100%; height: 5px; background-color: #2C2C2E; border-radius: 3px; overflow: hidden;">
            <div style="width: {perc_pro}%; height: 100%; background-color: {c_pro};"></div>
        </div>
    </div>
    <div style="background-color: #1C1C1E; border-radius: 20px; padding: 15px; grid-column: span 2;">
        <div style="color: #FFFFFF; font-size: 15px; font-weight: 600; margin-bottom: 12px;">Grassi</div>
        <div style="color: {c_fat}; font-size: 22px; font-weight: 700; margin-bottom: 12px; letter-spacing: 0.5px;">{fat}<span style="color: #8E8E93; font-size:14px; font-weight:600;"> /{t_fat}g</span></div>
        <div style="width: 100%; height: 5px; background-color: #2C2C2E; border-radius: 3px; overflow: hidden;">
            <div style="width: {perc_fat}%; height: 100%; background-color: {c_fat};"></div>
        </div>
    </div>
</div>
</div>"""
    return html
def render_macro_bar(pro, carb, fat):
    tot = (pro * 4) + (carb * 4) + (fat * 9)
    if tot == 0: return ""
    p_pro, p_carb, p_fat = ((pro*4)/tot)*100, ((carb*4)/tot)*100, ((fat*9)/tot)*100
    
    return f"""
<div style="margin-top: 10px; margin-bottom: 5px;">
    <div style="display: flex; justify-content: space-between; font-size: 11px; font-weight: 600; color: #94A3B8; margin-bottom: 4px;">
        <span><span style="color:#38BDF8">●</span> {int(p_pro)}% P</span>
        <span><span style="color:#F59E0B">●</span> {int(p_carb)}% C</span>
        <span><span style="color:#EC4899">●</span> {int(p_fat)}% F</span>
    </div>
    <div style="display: flex; height: 6px; border-radius: 4px; overflow: hidden;">
        <div style="width: {p_pro}%; background-color: #38BDF8;"></div>
        <div style="width: {p_carb}%; background-color: #F59E0B;"></div>
        <div style="width: {p_fat}%; background-color: #EC4899;"></div>
    </div>
</div>
"""

# --- 4. INTERFACCIA A SCHEDE ---
giorni = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]
mesi = ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"]
oggi_dt = datetime.now()
data_formattata = f"{giorni[oggi_dt.weekday()]} {oggi_dt.day} {mesi[oggi_dt.month - 1]}"

st.markdown(f"""
<div style="margin-top: -50px; margin-bottom: 25px;">
    <div style="font-size: 34px; font-weight: 800; color: #FFFFFF; letter-spacing: -0.5px; line-height: 1.2;">Riepilogo</div>
    <div style="font-size: 14px; font-weight: 600; color: #8E8E93;">{data_formattata}</div>
</div>
""", unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["Oggi", "Preferiti", "Impostazioni", "Storico"])

# ==========================================
# TAB 1: DIARIO E SCANNER AI
# ==========================================
with tab1:
    st.markdown(render_apple_dashboard(tot_cal, tot_pro, tot_carb, tot_fat, impostazioni['target_cal'], impostazioni['target_pro'], impostazioni['target_carb'], impostazioni['target_fat']), unsafe_allow_html=True)
    if st.session_state.draft_meal is None:
        st.markdown("<h4 style='color: #FFFFFF; font-weight: 600; margin-top: 15px; margin-bottom: 10px;'>Aggiungi Pasto o Prodotto</h4>", unsafe_allow_html=True)
        nota_utente = st.text_input("Nota rapida (es. '200g crudo', o 'Ne ho mangiati 50g')", placeholder="Aggiungi contesto per l'IA...")
        
        st.markdown("<div style='margin-top: 12px;'></div>", unsafe_allow_html=True)
        uploaded_file = st.file_uploader("Scatta o Carica Foto", type=["jpg", "jpeg", "png"], label_visibility="collapsed")
        
        if uploaded_file:
            col_btn1, col_btn2 = st.columns(2)
            btn_piatto = col_btn1.button("🍽️ Analizza Piatto", type="primary", use_container_width=True)
            btn_etichetta = col_btn2.button("🏷️ Leggi Etichetta", use_container_width=True)
            
            if btn_piatto or btn_etichetta:
                with st.spinner("Analisi IA in corso..."):
                    try:
                        img_fast = Image.open(uploaded_file).copy()
                        img_fast.thumbnail((800, 800))
                        client = genai.Client(api_key=API_KEY, http_options={'api_version': 'v1beta'})
                        
                        if btn_piatto:
                            prompt = f"""
                            Analizza questo pasto. Nota dell'utente: '{nota_utente}'.
                            Restituisci SOLO un JSON valido che scompone il piatto nei singoli ingredienti.
                            Struttura esatta:
                            {{
                                "nome_pasto": "Nome generale del piatto",
                                "ingredienti": [
                                    {{
                                        "nome": "Nome ingrediente (es. Riso Basmati)",
                                        "peso_g": 150,
                                        "cal_100g": 130, "pro_100g": 2.5, "carb_100g": 28.0, "fat_100g": 0.2
                                    }}
                                ]
                            }}
                            """
                        else:
                            prompt = f"""
                            Leggi la tabella nutrizionale in questa foto. Nota dell'utente: '{nota_utente}'.
                            Estrai accuratamente i valori per 100g. Cerca di dedurre il nome del prodotto.
                            Se l'utente ha scritto un peso specifico nella nota (es. '50g'), usa quel peso in 'peso_g', altrimenti usa 100.
                            Restituisci SOLO un JSON valido:
                            {{
                                "nome_pasto": "Prodotto Confezionato",
                                "ingredienti": [
                                    {{
                                        "nome": "Nome del prodotto",
                                        "peso_g": 100,
                                        "cal_100g": 350, "pro_100g": 20.5, "carb_100g": 40.0, "fat_100g": 10.0
                                    }}
                                ]
                            }}
                            """
                        
                        import time
                        max_tentativi = 3
                        for tentativo in range(max_tentativi):
                            try:
                                res = client.models.generate_content(
                                    model='gemini-3.8-flash',
                                    contents=[img_fast, prompt]
                                )
                                break
                            except Exception as e:
                                if tentativo < max_tentativi - 1:
                                    time.sleep(2.5)
                                    continue
                                else:
                                    raise e
                        
                        raw_text = res.text.strip().replace("```json", "").replace("```", "").strip()
                        st.session_state.draft_meal = json.loads(raw_text)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Errore: {e}")

        # --- ELENCO PASTI SALVATI OGGI ---
        st.markdown("<h4 style='color: #FFFFFF; font-weight: 600; margin-top: 35px; margin-bottom: 15px;'>Pasti di Oggi</h4>", unsafe_allow_html=True)
        if not pasti_oggi:
            st.markdown("""
            <div style="text-align: center; padding: 40px 20px; background-color: #161B26; border-radius: 16px; border: 1px dashed rgba(255,255,255,0.1);">
                <div style="font-size: 48px; margin-bottom: 15px; opacity: 0.8;">🍽️</div>
                <div style="color: #94A3B8; font-size: 15px; font-weight: 600;">Nessun pasto registrato oggi.</div>
                <div style="color: #64748B; font-size: 13px; margin-top: 5px;">Scatta una foto per iniziare!</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            for pasto in pasti_oggi:
                # 1. MODALITÀ MODIFICA (Se l'utente ha cliccato il tasto Modifica per questo pasto)
                if st.session_state.get("edit_pasto_id") == pasto["id"]:
                    with st.form(key=f"form_edit_{pasto['id']}"):
                        st.markdown("<h4 style='color: white; margin-top: 0; font-size: 16px;'>✏️ Modifica Pasto</h4>", unsafe_allow_html=True)
                        nuovo_nome = st.text_input("Nome Pasto", value=pasto["nome"])
                        
                        col1, col2, col3, col4 = st.columns(4)
                        nuove_cal = col1.number_input("Kcal", value=pasto["cal"], step=10)
                        nuove_carb = col2.number_input("Carbo (g)", value=pasto["carb"], step=1)
                        nuove_pro = col3.number_input("Pro (g)", value=pasto["pro"], step=1)
                        nuovi_fat = col4.number_input("Grassi (g)", value=pasto["fat"], step=1)
                        
                        c_salva, c_annulla = st.columns(2)
                        if c_salva.form_submit_button("💾 Salva", type="primary", use_container_width=True):
                            # Aggiorniamo il JSON
                            for i, p in enumerate(storico):
                                if p["id"] == pasto["id"]:
                                    storico[i]["nome"] = nuovo_nome
                                    storico[i]["cal"] = nuove_cal
                                    storico[i]["carb"] = nuove_carb
                                    storico[i]["pro"] = nuove_pro
                                    storico[i]["fat"] = nuovi_fat
                            salva_dati(FILE_STORICO, storico)
                            st.session_state["edit_pasto_id"] = None
                            st.rerun()
                        
                        if c_annulla.form_submit_button("❌ Annulla", use_container_width=True):
                            st.session_state["edit_pasto_id"] = None
                            st.rerun()
                
                # 2. MODALITÀ LETTURA (Rendering normale della Card)
                else:
                    tot_m = (pasto['pro'] * 4) + (pasto['carb'] * 4) + (pasto['fat'] * 9)
                    p_pro = (pasto['pro'] * 4 / tot_m * 100) if tot_m > 0 else 0
                    p_carb = (pasto['carb'] * 4 / tot_m * 100) if tot_m > 0 else 0
                    p_fat = (pasto['fat'] * 9 / tot_m * 100) if tot_m > 0 else 0
                    
                    html_pasto = f"""
                    <div style="background-color: #1C1C1E; border-radius: 16px; padding: 16px; margin-bottom: 5px; box-shadow: 0 4px 10px rgba(0,0,0,0.2);">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                            <div style="color: #FFFFFF; font-size: 16px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 70%;">{pasto['nome']}</div>
                            <div style="color: #FA114F; font-size: 18px; font-weight: 800;">{pasto['cal']} <span style="font-size: 12px; color: #8E8E93;">kcal</span></div>
                        </div>
                        <div style="display: flex; justify-content: space-between; font-size: 12px; color: #8E8E93; font-weight: 600; margin-bottom: 10px;">
                            <span><span style="color:#C462FF;">●</span> {pasto['carb']}g C</span>
                            <span><span style="color:#00E5FF;">●</span> {pasto['pro']}g P</span>
                            <span><span style="color:#B4FF00;">●</span> {pasto['fat']}g F</span>
                        </div>
                        <div style="width: 100%; height: 4px; border-radius: 2px; display: flex; overflow: hidden; background-color: #2C2C2E;">
                            <div style="width: {p_carb}%; background-color: #C462FF;"></div>
                            <div style="width: {p_pro}%; background-color: #00E5FF;"></div>
                            <div style="width: {p_fat}%; background-color: #B4FF00;"></div>
                        </div>
                    </div>
                    """
                    st.markdown(html_pasto, unsafe_allow_html=True)
                    
                    # Aggiunta del bottone Modifica a fianco di Elimina
                    c1, c2, c3 = st.columns([2, 1, 1])
                    with c2:
                        if st.button("Modifica", key=f"edit_{pasto['id']}", use_container_width=True):
                            st.session_state["edit_pasto_id"] = pasto["id"]
                            st.rerun()
                    with c3:
                        if st.button("Elimina", key=f"del_{pasto['id']}", use_container_width=True):
                            storico = [p for p in storico if p["id"] != pasto["id"]]
                            salva_dati(FILE_STORICO, storico)
                            st.rerun()
                    st.markdown("<div style='margin-bottom: 15px;'></div>", unsafe_allow_html=True)
    # --- REVISIONE E MODIFICA RAPIDA (DRAFT MEAL) ---
    else:
        st.markdown("<h4 style='color: #10B981; font-weight: 800; margin-top: 20px;'>⚡ Modifica Rapida Porzioni</h4>", unsafe_allow_html=True)
        st.write("L'IA ha scomposto il piatto. Correggi i grammi o aggiungi condimenti nascosti prima di salvare.")
        
        draft = st.session_state.draft_meal
        nome_pasto = st.text_input("Nome Pasto", value=draft.get("nome_pasto", "Pasto"))
        
        tot_d_cal = tot_d_pro = tot_d_carb = tot_d_fat = 0
        
        for idx, ing in enumerate(draft["ingredienti"]):
            c1, c2 = st.columns([3, 1])
            with c1: st.markdown(f"<div style='padding-top: 8px; font-weight:600;'>{ing['nome']}</div>", unsafe_allow_html=True)
            with c2: 
                nuovo_peso = st.number_input("g", value=int(ing['peso_g']), key=f"w_{idx}", label_visibility="collapsed")
                ing['peso_g'] = nuovo_peso
            
            moltiplicatore = ing['peso_g'] / 100.0
            tot_d_cal += int(ing['cal_100g'] * moltiplicatore)
            tot_d_pro += int(ing['pro_100g'] * moltiplicatore)
            tot_d_carb += int(ing['carb_100g'] * moltiplicatore)
            tot_d_fat += int(ing['fat_100g'] * moltiplicatore)
            
        st.markdown("<div style='font-size:12px; color:#94A3B8; margin-top: 15px; margin-bottom: 5px;'>+ Aggiungi Condimento Rapido</div>", unsafe_allow_html=True)
        btn_c1, btn_c2, btn_c3 = st.columns(3)
        if btn_c1.button("+ 10g Olio EVO"):
            draft["ingredienti"].append({"nome": "Olio EVO", "peso_g": 10, "cal_100g": 900, "pro_100g": 0, "carb_100g": 0, "fat_100g": 100})
            st.rerun()
        if btn_c2.button("+ 15g Burro Arachidi"):
            draft["ingredienti"].append({"nome": "Burro Arachidi", "peso_g": 15, "cal_100g": 588, "pro_100g": 25, "carb_100g": 20, "fat_100g": 50})
            st.rerun()
        if btn_c3.button("+ 10g Grana"):
            draft["ingredienti"].append({"nome": "Grana Padano", "peso_g": 10, "cal_100g": 392, "pro_100g": 33, "carb_100g": 0, "fat_100g": 28})
            st.rerun()
            
        st.markdown(f"""
<div style="background-color: #1A2433; padding: 15px; border-radius: 12px; border: 1px solid #10B981; margin-top: 20px;">
<div style="display:flex; justify-content:space-between; font-weight:800; font-size:18px;">
<span>Totale Calcolato:</span>
<span style="color:#10B981;">{tot_d_cal} kcal</span>
</div>
{render_macro_bar(tot_d_pro, tot_d_carb, tot_d_fat)}
<div style="display:flex; justify-content:space-between; font-size:13px; color:#94A3B8; font-weight:600; margin-top:8px;">
<span>{tot_d_pro}g Pro</span><span>{tot_d_carb}g Carb</span><span>{tot_d_fat}g Fat</span>
</div>
</div>
""", unsafe_allow_html=True)
        
        col_sv1, col_sv2, col_sv3 = st.columns([2, 2, 1])
        if col_sv1.button("💾 Salva nel Diario", type="primary", use_container_width=True):
            nuovo_pasto = {
                "id": str(uuid.uuid4()), "data": oggi, "nome": nome_pasto,
                "cal": tot_d_cal, "pro": tot_d_pro, "carb": tot_d_carb, "fat": tot_d_fat
            }
            storico.append(nuovo_pasto)
            salva_dati(FILE_STORICO, storico)
            st.session_state.draft_meal = None
            st.rerun()
            
        if col_sv2.button("⭐ Salva nei Preferiti", use_container_width=True):
            preset = {
                "id": str(uuid.uuid4()), "nome": nome_pasto,
                "cal": tot_d_cal, "pro": tot_d_pro, "carb": tot_d_carb, "fat": tot_d_fat
            }
            preferiti.append(preset)
            salva_dati(FILE_PREFERITI, preferiti)
            st.success("Salvato nei preferiti!")
            
        if col_sv3.button("❌ Annulla", use_container_width=True):
            st.session_state.draft_meal = None
            st.rerun()

# ==========================================
# TAB 2: PREFERITI (1-TAP LOGGING)
# ==========================================
with tab2:
    st.markdown("<h4 style='color: #FFFFFF; font-weight: 600;'>Pasti Ricorrenti</h4>", unsafe_allow_html=True)
    st.write("Aggiungi i tuoi pasti frequenti con un solo tap senza scattare foto.")
    
    if not preferiti:
        st.info("Nessun pasto preferito. Salva un pasto nei preferiti durante la revisione.")
    else:
        for pref in preferiti:
            st.markdown(f"""
            <div style="background-color: #161B26; padding: 15px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.08); margin-bottom: 10px;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-weight: 800; color: #E2E8F0;">{pref['nome']}</span>
                    <span style="color: #10B981; font-weight: 800;">{pref['cal']} kcal</span>
                </div>
                <div style="font-size: 12px; color: #94A3B8; margin-top: 4px;">{pref['pro']}g Pro • {pref['carb']}g Carb • {pref['fat']}g Fat</div>
            </div>
            """, unsafe_allow_html=True)
            c1, c2 = st.columns([3, 1])
            if c1.button("➕ Aggiungi al Diario di Oggi", key=f"add_{pref['id']}", type="primary", use_container_width=True):
                nuovo_pasto = pref.copy()
                nuovo_pasto["id"] = str(uuid.uuid4())
                nuovo_pasto["data"] = oggi
                storico.append(nuovo_pasto)
                salva_dati(FILE_STORICO, storico)
                st.rerun()
            if c2.button("🗑️", key=f"del_pref_{pref['id']}", use_container_width=True):
                preferiti = [p for p in preferiti if p["id"] != pref["id"]]
                salva_dati(FILE_PREFERITI, preferiti)
                st.rerun()

# ==========================================
# TAB 3: TARGET & STORICO
# ==========================================
with tab3:
    st.markdown("<h4 style='color: #FFFFFF; font-weight: 600;'>Obiettivi Nutrizionali</h4>", unsafe_allow_html=True)
    with st.form("form_impostazioni"):
        new_cal = st.number_input("Target Calorie (kcal)", value=impostazioni['target_cal'], step=50)
        new_pro = st.number_input("Target Proteine (g)", value=impostazioni['target_pro'], step=5)
        new_carb = st.number_input("Target Carboidrati (g)", value=impostazioni['target_carb'], step=5)
        new_fat = st.number_input("Target Grassi (g)", value=impostazioni['target_fat'], step=5)
        if st.form_submit_button("Salva Impostazioni"):
            impostazioni.update({"target_cal": new_cal, "target_pro": new_pro, "target_carb": new_carb, "target_fat": new_fat})
            salva_dati(FILE_IMPOSTAZIONI, impostazioni)
            st.success("Target aggiornati!")
            st.rerun()

with tab4:
    st.markdown("<h3 style='color: #FFFFFF; font-weight: 700; margin-bottom: 20px; font-size: 22px;'>Analisi Settimanale</h3>", unsafe_allow_html=True)
    
    # 1. CALCOLO DATI REALI ULTIMI 7 GIORNI
    giorni_salvati = {}
    oggi_dt_calc = datetime.now().date()
    
    # Raggruppiamo i pasti dello storico per data
    for pasto in storico:
        data_pasto = datetime.strptime(pasto["data"], "%Y-%m-%d").date()
        giorni_diff = (oggi_dt_calc - data_pasto).days
        
        # Prendiamo solo gli ultimi 7 giorni (da oggi a 6 giorni fa)
        if 0 <= giorni_diff <= 6:
            g_str = pasto["data"]
            if g_str not in giorni_salvati:
                giorni_salvati[g_str] = {"cal": 0, "pro": 0, "carb": 0, "fat": 0}
            
            giorni_salvati[g_str]["cal"] += pasto["cal"]
            giorni_salvati[g_str]["pro"] += pasto["pro"]
            giorni_salvati[g_str]["carb"] += pasto["carb"]
            giorni_salvati[g_str]["fat"] += pasto["fat"]

    # Prepariamo array di 7 giorni per il grafico (ordinati dal più vecchio a oggi)
    grafico_giorni = []
    grafico_valori = []
    
    # Calcolo Medie
    tot_cal_sett, tot_carb_sett, tot_pro_sett, tot_fat_sett = 0, 0, 0, 0
    giorni_tracciati = len(giorni_salvati) if len(giorni_salvati) > 0 else 1 # Evita divisione per zero
    
    for i in range(6, -1, -1):
        g_calc = oggi_dt_calc - timedelta(days=i)
        g_calc_str = str(g_calc)
        
        # Etichetta asse X (es. "L", "M", "M", "G"...)
        giorno_lettera = ["L", "M", "M", "G", "V", "S", "D"][g_calc.weekday()]
        grafico_giorni.append(giorno_lettera)
        
        if g_calc_str in giorni_salvati:
            dati_g = giorni_salvati[g_calc_str]
            grafico_valori.append(dati_g["cal"])
            tot_cal_sett += dati_g["cal"]
            tot_carb_sett += dati_g["carb"]
            tot_pro_sett += dati_g["pro"]
            tot_fat_sett += dati_g["fat"]
        else:
            grafico_valori.append(0)

    media_cal = int(tot_cal_sett / giorni_tracciati) if tot_cal_sett > 0 else 0
    media_carb = int(tot_carb_sett / giorni_tracciati) if tot_carb_sett > 0 else 0
    media_pro = int(tot_pro_sett / giorni_tracciati) if tot_pro_sett > 0 else 0
    media_fat = int(tot_fat_sett / giorni_tracciati) if tot_fat_sett > 0 else 0

  # 2. GENERAZIONE GRAFICO A BARRE HTML/CSS
    target_k = int(impostazioni.get('target_cal', 2800))
    barre_html = ""
    giorni_html = ""
    
    valore_max_grafico = max(grafico_valori) if len(grafico_valori) > 0 else 0
    # Alziamo il tetto del grafico del 20% in modo che la barra più alta non sbatta sul soffitto
    max_val = max(valore_max_grafico, target_k) * 1.2
    if max_val == 0:
        max_val = 1
        
    target_perc = (target_k / max_val) * 100
    
    for i, val in enumerate(grafico_valori):
        perc_h = (val / max_val) * 100
        is_over = val > target_k
        colore = "#FF3366" if is_over else "#FA114F"
        
        # Gestione giorni vuoti (per farti capire visivamente che ci sono 7 giorni)
        if val == 0:
            perc_h = 2 # Barra minima visibile per design
            colore = "#2C2C2E" # Grigio scuro stile Apple
            testo_val = ""
        else:
            testo_val = f"{val}"
            
        barre_html += f"""<div style="display: flex; flex-direction: column; align-items: center; justify-content: flex-end; height: 100%; width: 14%; z-index: 2;">
<div style="color: #FFFFFF; font-size: 10px; font-weight: 600; margin-bottom: 4px;">{testo_val}</div>
<div style="height: {perc_h}%; width: 22px; background-color: {colore}; border-radius: 4px 4px 0 0;"></div>
</div>"""
        
        giorni_html += f"""<div style="width: 14%; text-align: center; color: #8E8E93; font-size: 11px; font-weight: 600;">{grafico_giorni[i]}</div>"""

    st.markdown(f"""<div style="background-color: #1C1C1E; border-radius: 16px; padding: 20px 15px 10px 15px; margin-bottom: 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.15);">
<div style="position: relative; height: 140px; display: flex; align-items: flex-end; justify-content: space-between; border-bottom: 1px solid #2C2C2E;">
<div style="position: absolute; bottom: {target_perc}%; left: 0; right: 0; border-bottom: 1px dashed rgba(255,255,255,0.2); z-index: 1;">
<span style="position: absolute; left: 0; top: -16px; font-size: 9px; font-weight: 700; color: rgba(255,255,255,0.4); letter-spacing: 0.5px;">TARGET {target_k}</span>
</div>
{barre_html}
</div>
<div style="display: flex; justify-content: space-between; padding-top: 10px;">
{giorni_html}
</div>
</div>""", unsafe_allow_html=True)


    # 3. LE MEDIE SETTIMANALI (Con i veri dati calcolati)
    st.markdown(f"""
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 30px;">
        <div style="background-color: #1C1C1E; border-radius: 16px; padding: 15px; box-shadow: 0 4px 10px rgba(0,0,0,0.15);">
            <div style="color: #8E8E93; font-size: 12px; font-weight: 600; margin-bottom: 5px; text-transform: uppercase; letter-spacing: 0.5px;">Media Calorie</div>
            <div style="color: #FA114F; font-size: 24px; font-weight: 800;">{media_cal} <span style="font-size: 13px; color: #8E8E93; font-weight: 600;">kcal</span></div>
        </div>
        <div style="background-color: #1C1C1E; border-radius: 16px; padding: 15px; box-shadow: 0 4px 10px rgba(0,0,0,0.15);">
            <div style="color: #8E8E93; font-size: 12px; font-weight: 600; margin-bottom: 5px; text-transform: uppercase; letter-spacing: 0.5px;">Media Carbo</div>
            <div style="color: #C462FF; font-size: 24px; font-weight: 800;">{media_carb} <span style="font-size: 13px; color: #8E8E93; font-weight: 600;">g</span></div>
        </div>
        <div style="background-color: #1C1C1E; border-radius: 16px; padding: 15px; box-shadow: 0 4px 10px rgba(0,0,0,0.15);">
            <div style="color: #8E8E93; font-size: 12px; font-weight: 600; margin-bottom: 5px; text-transform: uppercase; letter-spacing: 0.5px;">Media Proteine</div>
            <div style="color: #00E5FF; font-size: 24px; font-weight: 800;">{media_pro} <span style="font-size: 13px; color: #8E8E93; font-weight: 600;">g</span></div>
        </div>
        <div style="background-color: #1C1C1E; border-radius: 16px; padding: 15px; box-shadow: 0 4px 10px rgba(0,0,0,0.15);">
            <div style="color: #8E8E93; font-size: 12px; font-weight: 600; margin-bottom: 5px; text-transform: uppercase; letter-spacing: 0.5px;">Media Grassi</div>
            <div style="color: #B4FF00; font-size: 24px; font-weight: 800;">{media_fat} <span style="font-size: 13px; color: #8E8E93; font-weight: 600;">g</span></div>
        </div>
    </div>
    """, unsafe_allow_html=True)


    # 4. LA MACCHINA DEL TEMPO
    st.markdown("<h4 style='color: #FFFFFF; font-weight: 600; margin-bottom: 10px; font-size: 18px;'>Esplora Giorni Passati</h4>", unsafe_allow_html=True)
    giorno_sel = st.date_input("Seleziona una data", value=datetime.now())
    
    pasti_storico = [p for p in storico if p["data"] == str(giorno_sel)]
    
    if len(pasti_storico) > 0:
        c_tot = sum(p["cal"] for p in pasti_storico)
        p_tot = sum(p["pro"] for p in pasti_storico)
        cb_tot = sum(p["carb"] for p in pasti_storico)
        f_tot = sum(p["fat"] for p in pasti_storico)
        
        st.markdown(f"<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
        st.markdown(render_apple_dashboard(c_tot, p_tot, cb_tot, f_tot, impostazioni['target_cal'], impostazioni['target_pro'], impostazioni['target_carb'], impostazioni['target_fat']), unsafe_allow_html=True)
        
        st.markdown("<h4 style='color: #FFFFFF; font-size: 16px; font-weight: 600; margin-bottom: 15px;'>Pasti Consumati</h4>", unsafe_allow_html=True)
        
        for p in pasti_storico:
            st.markdown(f"""
            <div style="background-color: #1C1C1E; border-radius: 12px; padding: 12px; margin-bottom: 8px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div style="color: #FFFFFF; font-size: 14px; font-weight: 600;">{p['nome']}</div>
                    <div style="color: #FA114F; font-size: 16px; font-weight: 800;">{p['cal']} <span style="font-size: 10px; color: #8E8E93;">kcal</span></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Nessun pasto salvato per questa data.")
