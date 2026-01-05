import streamlit as st
import sqlite3
import uuid

# -------------------------
# BANCO DE DADOS (SQLite)
# -------------------------
conn = sqlite3.connect("zelo.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS elders (
    id TEXT PRIMARY KEY,
    name TEXT,
    age INTEGER,
    condition TEXT
)
""")

conn.commit()

# -------------------------
# FUNÇÕES
# -------------------------
def create_elder(name, age, condition):
    c.execute(
        "INSERT INTO elders VALUES (?, ?, ?, ?)",
        (str(uuid.uuid4()), name, age, condition)
    )
    conn.commit()

def get_elders():
    c.execute("SELECT name, age, condition FROM elders")
    return c.fetchall()

# -------------------------
# INTERFACE
# -------------------------
st.title("🧓 Zelo – Cuidado com Idosos")

menu = st.sidebar.radio(
    "Menu",
    ["🏠 Início", "👴 Cadastro de Idoso", "📋 Idosos Cadastrados"]
)

# ---------- INÍCIO ----------
if menu == "🏠 Início":
    st.header("Bem-vindo ao Zelo")
    st.write("Sistema simples de cuidado com idosos.")
    st.write("Acesse o menu ao lado para começar.")

# ---------- CADASTRO ----------
elif menu == "👴 Cadastro de Idoso":
    st.header("Cadastro de Idoso")

    name = st.text_input("Nome do idoso")
    age = st.number_input("Idade", min_value=0, max_value=120)
    condition = st.text_area("Condição / Observações")

    if st.button("Salvar"):
        if name:
            create_elder(name, age, condition)
            st.success("Idoso cadastrado com sucesso!")
            st.rerun()
        else:
            st.error("Nome é obrigatório.")

# ---------- LISTAGEM ----------
elif menu == "📋 Idosos Cadastrados":
    st.header("Idosos cadastrados")

    elders = get_elders()

    if elders:
        for e in elders:
            st.write(f"**{e[0]}** | {e[1]} anos | {e[2]}")
    else:
        st.info("Nenhum idoso cadastrado.")
