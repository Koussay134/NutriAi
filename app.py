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
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; background-color: #0B0F17; }
    .stTabs [data-baseweb="tab"] {
        background-color: #161B26; border: 1px solid rgba(255,255,255,0.05);
        border-bottom: none; border-radius: 12px 12px 0 0; padding: 10px 20px; color: #94A3B8;
    }
    .stTabs [aria-selected="true"] { background-color: #10B981 !important; color: #0B0F17 !important; font-weight: 800 !important; }
</style>
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

def render_macro_card(title, value, target, color_hex, unit=""):
    perc = min((value / target) * 100, 100) if target > 0 else 0
    rimanenti = max(0, target - value)
    
    status_text = f"Rimangono: {rimanenti}{unit}" if value <= target else f"<span style='color:#EF4444;'>Sforo: +{value-target}{unit}</span>"
    
    html = f"""
    <div style="background-color: #161B26; padding: 16px; border-radius: 16px; border: 1px solid rgba(255,255,255,0.08); margin-bottom: 15px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <span style="color: {color_hex}; font-weight: 800; font-size: 12px; text-transform: uppercase; letter-spacing: 1px;">{title}</span>
            <span style="font-size: 11px; color: #94A3B8; font-weight: 600;">{status_text}</span>
        </div>
        <div style="font-size: 24px; font-weight: 800; color: #FFFFFF; line-height: 1;">
            {value}{unit} <span style="font-size: 13px; color:#64748B; font-weight: 600;">/ {target}{unit}</span>
        </div>
        <div style="width: 100%; background-color: rgba(255,255,255,0.05); border-radius: 10px; height: 6px; margin-top: 12px; overflow: hidden;">
            <div style="width: {perc}%; background-color: {color_hex}; height: 100%; border-radius: 10px;"></div>
        </div>
    </div>
    """
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
st.markdown("<h2 style='color: #FFFFFF; font-weight: 800; margin-bottom: 20px;'>🥗 NutriAI Pro</h2>", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["📸 Diario", "⭐ Preferiti", "⚙️ Target & Storico"])

# ==========================================
# TAB 1: DIARIO E SCANNER AI
# ==========================================
with tab1:
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(render_macro_card("Calorie", tot_cal, impostazioni['target_cal'], "#10B981", "kcal"), unsafe_allow_html=True)
        st.markdown(render_macro_card("Carboidrati", tot_carb, impostazioni['target_carb'], "#F59E0B", "g"), unsafe_allow_html=True)
    with c2:
        st.markdown(render_macro_card("Proteine", tot_pro, impostazioni['target_pro'], "#38BDF8", "g"), unsafe_allow_html=True)
        st.markdown(render_macro_card("Grassi", tot_fat, impostazioni['target_fat'], "#EC4899", "g"), unsafe_allow_html=True)
    
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
                        img_fast.thumbnail((500, 500))
                        client = genai.Client(api_key=API_KEY)
                        
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
                        
                        res = client.models.generate_content(
                            model='gemini-2.0-flash',
                            contents=[img_fast, prompt]
                        )
                        
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
                with st.expander(f"🍽️ {pasto['nome']}  —  {pasto['cal']} kcal"):
                    st.markdown(render_macro_bar(pasto['pro'], pasto['carb'], pasto['fat']), unsafe_allow_html=True)
                    st.markdown(f"<div style='display:flex; justify-content:space-between; font-size:12px; color:#94A3B8; margin-bottom:15px;'><span>{pasto['pro']}g Pro</span><span>{pasto['carb']}g Carb</span><span>{pasto['fat']}g Fat</span></div>", unsafe_allow_html=True)
                    if st.button("🗑️ Elimina Pasto", key=f"del_{pasto['id']}"):
                        storico = [p for p in storico if p["id"] != pasto["id"]]
                        salva_dati(FILE_STORICO, storico)
                        st.rerun()

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
