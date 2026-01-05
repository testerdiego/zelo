import streamlit as st
import requests
import json
import base64
from datetime import datetime
import uuid

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Zelo - Cuidado Conectado",
    page_icon="❤️",
    layout="centered"
)

# --- CSS ---
st.markdown("""
<style>
.elder-card {
    padding: 20px;
    border-radius: 20px;
    border: 2px solid #3B82F6;
    margin-bottom: 20px;
    background-color: #f8fafc;
}
.stButton>button {
    width: 100%;
    border-radius: 15px;
    font-weight: bold;
}
.big-font {
    font-size: 30px !important;
    font-weight: 800;
}
</style>
""", unsafe_allow_html=True)

# --- ESTADO GLOBAL ---
if "profile" not in st.session_state:
    st.session_state.profile = None

if "selected_elder_id" not in st.session_state:
    st.session_state.selected_elder_id = None

if "elders" not in st.session_state:
    st.session_state.elders = []

# --- GEMINI TTS ---
def call_gemini_tts(text, api_key):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent?key={st.secrets['GEMINI_API_KEY']}"
    payload = {
        "contents": [{"parts": [{"text": text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {"voiceName": "Kore"}
                }
            }
        }
    }
    try:
        response = requests.post(url, json=payload, timeout=15)
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
    except:
        return None

# --- FUNÇÕES DE DADOS ---
def get_elders():
    return st.session_state.elders

def add_elder(name, age, gender):
    import random, string
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    st.session_state.elders.append({
        "id": str(uuid.uuid4()),
        "name": name,
        "age": age,
        "gender": gender,
        "accessCode": code,
        "meds": [],
        "logs": [],
        "helpRequested": False,
        "photo": "👴" if gender == "M" else "👵"
    })

def mark_med_taken(elder_id, med_id):
    now = datetime.now()
    for elder in st.session_state.elders:
        if elder["id"] == elder_id:
            med = next(m for m in elder["meds"] if m["id"] == med_id)
            elder["logs"].insert(0, {
                "medId": med_id,
                "medName": med["name"],
                "time": now.strftime("%H:%M"),
                "date": now.strftime("%d/%m/%Y"),
                "status": "taken"
            })
            elder["logs"] = elder["logs"][:30]

# --- SELEÇÃO DE PERFIL ---
if st.session_state.profile is None:
    st.title("❤️ Zelo")
    st.subheader("Cuidado conectado em tempo real")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("SOU CUIDADOR"):
            st.session_state.profile = "caregiver"
            st.rerun()
    with col2:
        if st.button("SOU IDOSO"):
            st.session_state.profile = "elder"
            st.rerun()

# --- PAINEL DO CUIDADOR ---
elif st.session_state.profile == "caregiver":
    st.sidebar.button("Sair", on_click=lambda: st.session_state.clear())
    st.title("👨‍⚕️ Painel do Cuidador")

    elders = get_elders()

    if st.session_state.selected_elder_id is None:
        with st.expander("➕ Registrar Novo Idoso"):
            name = st.text_input("Nome")
            age = st.number_input("Idade", 0, 120)
            gender = st.selectbox("Gênero", ["M", "F"])
            if st.button("Salvar Registro"):
                add_elder(name, age, gender)
                st.success("Idoso registrado!")
                st.rerun()

        st.write("### Meus Idosos")
        for e in elders:
            col_a, col_b = st.columns([4, 1])
            col_a.write(f"**{e['name']}** ({e['age']} anos) — Código `{e['accessCode']}`")
            if col_b.button("Ver", key=e["id"]):
                st.session_state.selected_elder_id = e["id"]
                st.rerun()
            if e["helpRequested"]:
                st.error("🚨 Pedido de ajuda ativo!")

    else:
        elder = next(e for e in elders if e["id"] == st.session_state.selected_elder_id)

        if st.button("⬅️ Voltar"):
            st.session_state.selected_elder_id = None
            st.reru
