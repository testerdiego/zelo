import streamlit as st
import sqlite3
import uuid
import requests
import base64
from datetime import datetime
import random
import string

# ======================================================
# CONFIG
# ======================================================
st.set_page_config("Zelo - Cuidado Conectado", "❤️", layout="centered")

# ======================================================
# CSS
# ======================================================
st.markdown("""
<style>
.elder-card {
    padding: 20px;
    border-radius: 20px;
    border: 2px solid #3b82f6;
    background-color: #f8fafc;
    margin-bottom: 20px;
}
.big-font {
    font-size: 30px;
    font-weight: 800;
}
.stButton>button {
    width: 100%;
    border-radius: 15px;
}
</style>
""", unsafe_allow_html=True)

# ======================================================
# SQLITE
# ======================================================
conn = sqlite3.connect("zelo.db", check_same_thread=False)
cursor = conn.cursor()

def init_db():
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        username TEXT UNIQUE,
        name TEXT,
        password TEXT,
        role TEXT
    )
    """)

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
        med_name TEXT,
        time TEXT,
        date TEXT
    )
    """)

    conn.commit()

init_db()

# ======================================================
# HELPERS
# ======================================================
def generate_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def call_gemini_tts(text):
    if "GEMINI_API_KEY" not in st.secrets:
        return None

    url = (
        "https://generativelanguage.googleapis.com/v1beta/"
        f"models/gemini-2.5-flash-preview-tts:generateContent"
        f"?key={st.secrets['GEMINI_API_KEY']}"
    )

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
        r = requests.post(url, json=payload, timeout=15)
        data = r.json()
        return data["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
    except:
        return None

# ======================================================
# AUTH
# ======================================================
def authenticate(username, password):
    cursor.execute(
        "SELECT id, name, role FROM users WHERE username=? AND password=?",
        (username, password)
    )
    return cursor.fetchone()

# Criar usuário admin se não existir
cursor.execute("SELECT * FROM users WHERE username='admin'")
if not cursor.fetchone():
    cursor.execute(
        "INSERT INTO users VALUES (?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), "admin", "Administrador", "1234", "caregiver")
    )
    conn.commit()

# ======================================================
# SESSION
# ======================================================
if "user" not in st.session_state:
    st.session_state.user = None

if "selected_elder" not in st.session_state:
    st.session_state.selected_elder = None

# ======================================================
# LOGIN
# ======================================================
if st.session_state.user is None:
    st.title("🔐 Login - Zelo")

    u = st.text_input("Usuário")
    p = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        user = authenticate(u, p)
        if user:
            st.session_state.user = user
            st.rerun()
        else:
            st.error("Usuário ou senha inválidos")

    st.info("Usuário demo: admin | Senha: 1234")
    st.stop()

# ======================================================
# SIDEBAR
# ======================================================
st.sidebar.success(f"Logado como: {st.session_state.user[1]}")
if st.sidebar.button("Sair"):
    st.session_state.clear()
    st.rerun()

# ======================================================
# PAINEL DO CUIDADOR
# ======================================================
if st.session_state.user[2] == "caregiver":
    st.title("👨‍⚕️ Painel do Cuidador")

    if st.session_state.selected_elder is None:
        with st.expander("➕ Registrar Idoso"):
            name = st.text_input("Nome")
            age = st.number_input("Idade", 0, 120)
            gender = st.selectbox("Gênero", ["M", "F"])

            if st.button("Salvar"):
                cursor.execute(
                    "INSERT INTO elders VALUES (?, ?, ?, ?, ?, ?, 0)",
                    (
                        str(uuid.uuid4()),
                        name,
                        age,
                        gender,
                        "👴" if gender == "M" else "👵",
                        generate_code()
                    )
                )
                conn.commit()
                st.success("Idoso cadastrado!")
                st.rerun()

        cursor.execute("SELECT id, name, age, access_code, help_requested FROM elders")
        for e in cursor.fetchall():
            col1, col2 = st.columns([4, 1])
            col1.write(f"**{e[1]}** ({e[2]} anos) — Código `{e[3]}`")
            if col2.button("Ver", key=e[0]):
                st.session_state.selected_elder = e[0]
                st.rerun()
            if e[4]:
                st.error("🚨 Pedido de ajuda!")

    else:
        cursor.execute("SELECT name, photo FROM elders WHERE id=?", (st.session_state.selected_elder,))
        elder = cursor.fetchone()

        if st.button("⬅️ Voltar"):
            st.session_state.selected_elder = None
            st.rerun()

        st.header(f"{elder[1]} {elder[0]}")

        with st.popover("➕ Adicionar Medicamento"):
            m_name = st.text_input("Nome")
            m_dose = st.text_input("Dose")
            m_freq = st.text_input("Frequência")
            if st.button("Adicionar"):
                cursor.execute(
                    "INSERT INTO meds VALUES (?, ?, ?, ?, ?)",
                    (str(uuid.uuid4()), st.session_state.selected_elder, m_name, m_dose, m_freq)
                )
                conn.commit()
                st.rerun()

        cursor.execute(
            "SELECT name, dosage, freq FROM meds WHERE elder_id=?",
            (st.session_state.selected_elder,)
        )
        for m in cursor.fetchall():
            st.info(f"💊 {m[0]} — {m[1]} ({m[2]})")

# ======================================================
# PAINEL DO IDOSO
# ======================================================
else:
    st.title("👵 Acesso do Idoso")

    code = st.text_input("Digite seu código", max_chars=6).upper()

    if st.button("Entrar"):
        cursor.execute("SELECT id, name FROM elders WHERE access_code=?", (code,))
        elder = cursor.fetchone()

        if not elder:
            st.error("Código inválido")
        else:
            st.session_state.selected_elder = elder[0]
            st.session_state.elder_name = elder[1]
            st.rerun()

    if st.session_state.selected_elder:
        st.markdown(f"<p class='big-font'>Olá, {st.session_state.elder_name}!</p>", unsafe_allow_html=True)

        cursor.execute(
            "SELECT id, name, dosage, freq FROM meds WHERE elder_id=?",
            (st.session_state.selected_elder,)
        )
        meds = cursor.fetchall()

        today = datetime.now().strftime("%d/%m/%Y")

        for m in meds:
            st.markdown(
                f"<div class='elder-card'><h3>💊 {m[1]}</h3><p>{m[2]} • {m[3]}</p></div>",
                unsafe_allow_html=True
            )

            col1, col2 = st.columns(2)

            with col1:
                if st.button("🔊 Ouvir", key=f"tts_{m[0]}"):
                    audio = call_gemini_tts(f"Está na hora de tomar o {m[1]}")
                    if audio:
                        st.audio(base64.b64decode(audio))

            with col2:
                if st.button("JÁ TOMEI", key=f"done_{m[0]}"):
                    cursor.execute(
                        "INSERT INTO logs VALUES (?, ?, ?, ?, ?)",
                        (
                            str(uuid.uuid4()),
                            st.session_state.selected_elder,
                            m[1],
                            datetime.now().strftime("%H:%M"),
                            today
                        )
                    )
                    conn.commit()
                    st.success("Registrado!")

        if st.button("🆘 PEDIR AJUDA"):
            cursor.execute(
                "UPDATE elders SET help_requested=1 WHERE id=?",
                (st.session_state.selected_elder,)
            )
            conn.commit()
            st.warning("Pedido de ajuda enviado!")
