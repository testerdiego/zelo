import streamlit as st
import sqlite3
import requests
import base64
from datetime import datetime
import uuid
import random
import string

# -------------------------
# CONFIGURAÇÃO DA PÁGINA
# -------------------------
st.set_page_config(
    page_title="Zelo - Cuidado Conectado",
    page_icon="❤️",
    layout="centered"
)

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
.big-font { font-size: 30px !important; font-weight: 800; }
</style>
""", unsafe_allow_html=True)

# -------------------------
# SQLITE
# -------------------------
conn = sqlite3.connect("zelo.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS elders (
    id TEXT PRIMARY KEY,
    name TEXT,
    age INTEGER,
    gender TEXT,
    photo TEXT,
    access_code TEXT,
    help_requested INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS meds (
    id TEXT PRIMARY KEY,
    elder_id TEXT,
    name TEXT,
    dosage TEXT,
    freq TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS logs (
    id TEXT PRIMARY KEY,
    elder_id TEXT,
    med_id TEXT,
    med_name TEXT,
    time TEXT,
    date TEXT
)
""")

conn.commit()

# -------------------------
# TTS - GEMINI
# -------------------------
def call_gemini_tts(text):
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
        r = requests.post(url, json=payload)
        audio = r.json()["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
        return audio
    except:
        return None

# -------------------------
# ESTADO
# -------------------------
if "profile" not in st.session_state:
    st.session_state.profile = None

if "selected_elder_id" not in st.session_state:
    st.session_state.selected_elder_id = None

# -------------------------
# FUNÇÕES SQLITE
# -------------------------
def get_elders():
    cursor.execute("SELECT * FROM elders")
    rows = cursor.fetchall()

    elders = []
    for r in rows:
        elders.append({
            "id": r[0],
            "name": r[1],
            "age": r[2],
            "gender": r[3],
            "photo": r[4],
            "accessCode": r[5],
            "helpRequested": bool(r[6]),
            "meds": get_meds(r[0]),
            "logs": get_logs(r[0])
        })
    return elders

def add_elder(name, age, gender):
    elder_id = str(uuid.uuid4())
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    photo = "👴" if gender == "M" else "👵"

    cursor.execute(
        "INSERT INTO elders VALUES (?, ?, ?, ?, ?, ?, ?)",
        (elder_id, name, age, gender, photo, code, 0)
    )
    conn.commit()

def get_meds(elder_id):
    cursor.execute("SELECT id, name, dosage, freq FROM meds WHERE elder_id = ?", (elder_id,))
    return [{"id": r[0], "name": r[1], "dosage": r[2], "freq": r[3]} for r in cursor.fetchall()]

def add_med(elder_id, name, dosage, freq):
    cursor.execute(
        "INSERT INTO meds VALUES (?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), elder_id, name, dosage, freq)
    )
    conn.commit()

def get_logs(elder_id):
    cursor.execute(
        "SELECT med_id, med_name, time, date FROM logs WHERE elder_id = ? ORDER BY date DESC, time DESC LIMIT 30",
        (elder_id,)
    )
    return [{"medId": r[0], "medName": r[1], "time": r[2], "date": r[3]} for r in cursor.fetchall()]

def mark_med_taken(elder_id, med):
    now = datetime.now()
    cursor.execute(
        "INSERT INTO logs VALUES (?, ?, ?, ?, ?, ?)",
        (
            str(uuid.uuid4()),
            elder_id,
            med["id"],
            med["name"],
            now.strftime("%H:%M"),
            now.strftime("%d/%m/%Y")
        )
    )
    conn.commit()

def request_help(elder_id):
    cursor.execute(
        "UPDATE elders SET help_requested = 1 WHERE id = ?",
        (elder_id,)
    )
    conn.commit()

# -------------------------
# MENU INICIAL
# -------------------------
if st.session_state.profile is None:
    st.title("❤️ Zelo")
    st.subheader("Cuidado conectado em tempo real")

    col1, col2 = st.columns(2)
    if col1.button("SOU CUIDADOR", use_container_width=True):
        st.session_state.profile = "caregiver"
        st.rerun()

    if col2.button("SOU IDOSO", use_container_width=True):
        st.session_state.profile = "elder"
        st.rerun()

# -------------------------
# CUIDADOR
# -------------------------
elif st.session_state.profile == "caregiver":
    st.sidebar.button("Sair", on_click=lambda: st.session_state.clear())
    st.title("👨‍⚕️ Painel do Cuidador")

    elders = get_elders()

    if st.session_state.selected_elder_id is None:
        with st.expander("➕ Registrar Novo Idoso"):
            name = st.text_input("Nome")
            age = st.number_input("Idade", 0, 120)
            gender = st.selectbox("Gênero", ["M", "F"])
            if st.button("Salvar"):
                add_elder(name, age, gender)
                st.success("Registrado!")
                st.rerun()

        for e in elders:
            col1, col2 = st.columns([4, 1])
            col1.write(f"**{e['name']}** ({e['age']} anos) - Código `{e['accessCode']}`")
            if col2.button("Ver", key=e["id"]):
                st.session_state.selected_elder_id = e["id"]
                st.rerun()
            if e["helpRequested"]:
                st.error("🚨 Pedido de ajuda ativo")

    else:
        elder = next(e for e in elders if e["id"] == st.session_state.selected_elder_id)
        if st.button("⬅️ Voltar"):
            st.session_state.selected_elder_id = None
            st.rerun()

        st.header(f"{elder['photo']} {elder['name']}")
        tab1, tab2 = st.tabs(["Medicamentos", "Histórico"])

        with tab1:
            with st.popover("➕ Adicionar Medicamento"):
                n = st.text_input("Nome")
                d = st.text_input("Dose")
                f = st.text_input("Horário")
                if st.button("Adicionar"):
                    add_med(elder["id"], n, d, f)
                    st.rerun()

            for m in elder["meds"]:
                st.info(f"💊 **{m['name']}** - {m['dosage']} ({m['freq']})")

        with tab2:
            for l in elder["logs"]:
                st.write(f"✅ {l['time']} - {l['medName']}")

# -------------------------
# IDOSO
# -------------------------
elif st.session_state.profile == "elder":
    if st.session_state.selected_elder_id is None:
        st.title("🔑 Acesso do Idoso")
        code = st.text_input("Digite seu código", max_chars=6).upper()
        if st.button("ENTRAR"):
            elder = next((e for e in get_elders() if e["accessCode"] == code), None)
            if elder:
                st.session_state.selected_elder_id = elder["id"]
                st.rerun()
            else:
                st.error("Código inválido")

    else:
        elder = next(e for e in get_elders() if e["id"] == st.session_state.selected_elder_id)
        st.markdown(f"<p class='big-font'>Olá, {elder['name']}!</p>", unsafe_allow_html=True)

        today = datetime.now().strftime("%d/%m/%Y")

        for m in elder["meds"]:
            taken = any(l["medId"] == m["id"] and l["date"] == today for l in elder["logs"])

            st.markdown(
                f"<div class='elder-card' style='border-color:{'#10b981' if taken else '#3b82f6'}'>"
                f"<h2>{'✅' if taken else '💊'} {m['name']}</h2>"
                f"<p>{m['dosage']} • {m['freq']}</p></div>",
                unsafe_allow_html=True
            )

            if not taken:
                col1, col2 = st.columns(2)
                if col1.button("🔊 Ouvir", key=f"tts_{m['id']}"):
                    audio = call_gemini_tts(f"Está na hora de tomar o {m['name']}")
                    if audio:
                        st.audio(base64.b64decode(audio))

                if col2.button("JÁ TOMEI", key=f"take_{m['id']}"):
                    mark_med_taken(elder["id"], m)
                    st.rerun()

        if st.button("🆘 PEDIR AJUDA", use_container_width=True):
            request_help(elder["id"])
            st.warning("Ajuda solicitada!")
