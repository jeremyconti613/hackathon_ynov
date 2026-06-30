"""Interface de chat TechCorp — Assistant Financier (Streamlit + Ollama)."""
import os

import streamlit as st

import ollama_client as oc

DEFAULT_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
DEFAULT_MODEL = "phi3-financial"

st.set_page_config(
    page_title="TechCorp — Assistant Financier",
    page_icon="💰",
    layout="centered",
)

if "messages" not in st.session_state:
    st.session_state.messages = []

# --- Sidebar : configuration + statut ---
with st.sidebar:
    st.title("⚙️ Configuration")
    base_url = st.text_input("URL du serveur Ollama", value=DEFAULT_URL)

    connected = oc.is_alive(base_url)
    if connected:
        st.success("🟢 Connecté")
    else:
        st.error("🔴 Déconnecté")

    models = oc.list_models(base_url) if connected else []
    if models:
        index = models.index(DEFAULT_MODEL) if DEFAULT_MODEL in models else 0
        model = st.selectbox("Modèle", models, index=index)
    else:
        model = st.text_input("Modèle", value=DEFAULT_MODEL)

    if st.button("🗑️ Effacer l'historique"):
        st.session_state.messages = []
        st.rerun()

# --- En-tête ---
st.title("💰 Assistant Financier TechCorp")
st.caption(f"Modèle : `{model}`  ·  Serveur : `{base_url}`")

# --- Historique ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- Saisie + réponse ---
prompt = st.chat_input(
    "Pose ta question financière…",
    disabled=not connected,
)

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            response = st.write_stream(
                oc.chat(base_url, model, st.session_state.messages)
            )
            st.session_state.messages.append({"role": "assistant", "content": response})
        except Exception as exc:  # serveur tombé en cours de route, timeout, etc.
            st.error(f"⚠️ Erreur : impossible de contacter le serveur ({exc}).")

if not connected:
    st.info(
        "Serveur Ollama indisponible — vérifie avec l'équipe INFRA que le "
        "serveur tourne sur l'URL ci-dessus."
    )
