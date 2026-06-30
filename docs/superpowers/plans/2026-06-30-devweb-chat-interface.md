# Interface de chat DEV WEB — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construire une interface web Streamlit de chat connectée au serveur Ollama (modèle financier), avec historique, indicateur de connexion et lancement en une commande.

**Architecture:** App Streamlit (`app.py`) qui consomme un module client HTTP isolé (`ollama_client.py`) parlant à l'API Ollama (`/api/tags`, `/api/chat`). La logique réseau est testée unitairement par mock de `requests`; l'UI Streamlit est vérifiée manuellement. Lancement via `run.sh` (venv + install + streamlit).

**Tech Stack:** Python 3, Streamlit, Requests, pytest (dev), Ollama HTTP API.

## Global Constraints

- Tous les fichiers livrables vivent dans `rendu/devweb/` (relatif à la racine du dépôt `hackathon_ynov/`).
- Dépendances applicatives limitées à : `streamlit`, `requests`. `pytest` est une dépendance de dev uniquement.
- URL serveur par défaut : `http://localhost:11434`, surchargeable par la variable d'environnement `OLLAMA_URL`.
- Modèle par défaut : `phi3-financial`.
- UI en français.
- L'app ne doit jamais planter si le serveur Ollama est injoignable (mode dégradé « déconnecté »).
- Les commandes de test/lancement s'exécutent depuis `rendu/devweb/`.

---

### Task 1: Module client Ollama (`ollama_client.py`) + tests

**Files:**
- Create: `rendu/devweb/ollama_client.py`
- Create: `rendu/devweb/tests/test_ollama_client.py`
- Create: `rendu/devweb/requirements.txt`

**Interfaces:**
- Consumes: rien (premier composant).
- Produces:
  - `is_alive(base_url: str, timeout: float = 2) -> bool`
  - `list_models(base_url: str, timeout: float = 2) -> list[str]`
  - `chat(base_url: str, model: str, messages: list[dict], timeout: float = 120) -> Iterator[str]`
    - `messages` = liste de `{"role": "user"|"assistant"|"system", "content": str}`
    - yield des fragments de texte (`str`) au fil du streaming.

- [ ] **Step 1: Créer `requirements.txt`**

Fichier `rendu/devweb/requirements.txt` :

```text
streamlit>=1.30
requests>=2.31
```

- [ ] **Step 2: Écrire les tests qui échouent**

Fichier `rendu/devweb/tests/test_ollama_client.py` :

```python
import json
from unittest.mock import patch, MagicMock

import ollama_client as oc


@patch("ollama_client.requests.get")
def test_is_alive_true_on_200(mock_get):
    mock_get.return_value = MagicMock(status_code=200)
    assert oc.is_alive("http://localhost:11434") is True


@patch("ollama_client.requests.get")
def test_is_alive_false_on_exception(mock_get):
    import requests
    mock_get.side_effect = requests.ConnectionError("down")
    assert oc.is_alive("http://localhost:11434") is False


@patch("ollama_client.requests.get")
def test_list_models_parses_names(mock_get):
    resp = MagicMock(status_code=200)
    resp.json.return_value = {"models": [{"name": "phi3-financial"}, {"name": "mistral"}]}
    resp.raise_for_status.return_value = None
    mock_get.return_value = resp
    assert oc.list_models("http://localhost:11434") == ["phi3-financial", "mistral"]


@patch("ollama_client.requests.get")
def test_list_models_empty_on_error(mock_get):
    import requests
    mock_get.side_effect = requests.ConnectionError("down")
    assert oc.list_models("http://localhost:11434") == []


@patch("ollama_client.requests.post")
def test_chat_yields_content_chunks(mock_post):
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.iter_lines.return_value = [
        json.dumps({"message": {"content": "Bonjour"}, "done": False}).encode(),
        json.dumps({"message": {"content": " monde"}, "done": False}).encode(),
        json.dumps({"message": {"content": ""}, "done": True}).encode(),
    ]
    mock_post.return_value = resp
    assert list(oc.chat("http://localhost:11434", "phi3-financial", [])) == ["Bonjour", " monde"]
```

- [ ] **Step 3: Lancer les tests pour vérifier qu'ils échouent**

Run (depuis `rendu/devweb/`) :
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install --quiet requests pytest
PYTHONPATH=. pytest tests/test_ollama_client.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'ollama_client'`.

- [ ] **Step 4: Écrire l'implémentation minimale**

Fichier `rendu/devweb/ollama_client.py` :

```python
"""Client HTTP minimal pour le serveur d'inférence Ollama."""
import json
from typing import Iterator

import requests


def _tags_url(base_url: str) -> str:
    return f"{base_url.rstrip('/')}/api/tags"


def is_alive(base_url: str, timeout: float = 2) -> bool:
    """Retourne True si le serveur Ollama répond (HTTP 200) sur /api/tags."""
    try:
        resp = requests.get(_tags_url(base_url), timeout=timeout)
        return resp.status_code == 200
    except requests.RequestException:
        return False


def list_models(base_url: str, timeout: float = 2) -> list:
    """Retourne la liste des noms de modèles disponibles, ou [] en cas d'erreur."""
    try:
        resp = requests.get(_tags_url(base_url), timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        return [m["name"] for m in data.get("models", [])]
    except (requests.RequestException, ValueError, KeyError):
        return []


def chat(base_url: str, model: str, messages: list, timeout: float = 120) -> Iterator[str]:
    """Envoie la conversation à Ollama et yield les fragments de réponse (streaming)."""
    url = f"{base_url.rstrip('/')}/api/chat"
    payload = {"model": model, "messages": messages, "stream": True}
    resp = requests.post(url, json=payload, stream=True, timeout=timeout)
    resp.raise_for_status()
    for line in resp.iter_lines():
        if not line:
            continue
        data = json.loads(line)
        content = data.get("message", {}).get("content", "")
        if content:
            yield content
        if data.get("done"):
            break
```

- [ ] **Step 5: Lancer les tests pour vérifier qu'ils passent**

Run (depuis `rendu/devweb/`) :
```bash
PYTHONPATH=. pytest tests/test_ollama_client.py -v
```
Expected: PASS — 5 tests passés.

- [ ] **Step 6: Commit**

```bash
git add rendu/devweb/ollama_client.py rendu/devweb/tests/test_ollama_client.py rendu/devweb/requirements.txt
git commit -m "feat(devweb): client Ollama (is_alive, list_models, chat streaming) + tests"
```

---

### Task 2: Interface Streamlit (`app.py`)

**Files:**
- Create: `rendu/devweb/app.py`

**Interfaces:**
- Consumes: `ollama_client.is_alive`, `ollama_client.list_models`, `ollama_client.chat` (Task 1).
- Produces: application Streamlit lançable par `streamlit run app.py`.

- [ ] **Step 1: Écrire `app.py`**

Fichier `rendu/devweb/app.py` :

```python
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
        except Exception as exc:  # serveur tombé en cours de route, timeout, etc.
            response = f"⚠️ Erreur : impossible de contacter le serveur ({exc})."
            st.error(response)

    st.session_state.messages.append({"role": "assistant", "content": response})

if not connected:
    st.info(
        "Serveur Ollama indisponible — vérifie avec l'équipe INFRA que le "
        "serveur tourne sur l'URL ci-dessus."
    )
```

- [ ] **Step 2: Vérifier que l'app démarre (serveur Ollama absent → mode dégradé)**

Run (depuis `rendu/devweb/`, venv activé) :
```bash
pip install --quiet -r requirements.txt
streamlit run app.py --server.headless true &
sleep 4
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8501
kill %1
```
Expected: code HTTP `200` (l'app sert sa page). Dans le navigateur, le badge doit afficher **🔴 Déconnecté**, la saisie est désactivée, et le message d'indisponibilité s'affiche — sans crash.

- [ ] **Step 3: Commit**

```bash
git add rendu/devweb/app.py
git commit -m "feat(devweb): interface chat Streamlit (historique, statut, streaming)"
```

---

### Task 3: Lancement en une commande (`run.sh`) + documentation (`README.md`)

**Files:**
- Create: `rendu/devweb/run.sh`
- Create: `rendu/devweb/README.md`

**Interfaces:**
- Consumes: `app.py` (Task 2), `requirements.txt` (Task 1).
- Produces: commande unique `./run.sh` qui installe et lance l'app.

- [ ] **Step 1: Écrire `run.sh`**

Fichier `rendu/devweb/run.sh` :

```bash
#!/usr/bin/env bash
# Lancement en une commande de l'interface de chat DEV WEB.
set -e
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  echo "📦 Création de l'environnement virtuel…"
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

echo "🚀 Lancement de l'interface sur http://localhost:8501"
exec streamlit run app.py
```

- [ ] **Step 2: Rendre le script exécutable**

Run (depuis `rendu/devweb/`) :
```bash
chmod +x run.sh
```
Expected: pas de sortie, `ls -l run.sh` montre les droits `-rwxr-xr-x`.

- [ ] **Step 3: Écrire `README.md`**

Fichier `rendu/devweb/README.md` :

```markdown
# Interface de chat — DEV WEB (TechCorp Assistant Financier)

Interface web (Streamlit) pour discuter avec le modèle financier servi par
Ollama (déployé par l'équipe INFRA).

## Lancement (une commande)

```bash
./run.sh
```

Le script crée le venv, installe les dépendances et lance l'app sur
http://localhost:8501.

> Si le venv est déjà prêt : `streamlit run app.py`.

## Configuration

- **URL du serveur** : éditable dans la barre latérale (défaut
  `http://localhost:11434`). Surcharge possible avant lancement :
  ```bash
  OLLAMA_URL=http://IP_INFRA:11434 ./run.sh
  ```
- **Modèle** : sélectionné automatiquement parmi les modèles détectés sur le
  serveur ; défaut `phi3-financial` (à adapter au nom donné par l'INFRA lors du
  `ollama create`).

## Fonctionnalités

- Chat en temps réel (réponses en streaming).
- Historique de la conversation conservé pendant la session.
- Indicateur de connexion : 🟢 Connecté / 🔴 Déconnecté.
- Bouton pour effacer l'historique.

## Tests

```bash
PYTHONPATH=. pytest tests/ -v
```
```

- [ ] **Step 4: Vérifier le lancement de bout en bout**

Run (depuis `rendu/devweb/`) :
```bash
./run.sh --server.headless true &
sleep 6
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8501
kill %1
```
Expected: code HTTP `200`.

- [ ] **Step 5: Commit**

```bash
git add rendu/devweb/run.sh rendu/devweb/README.md
git commit -m "feat(devweb): lancement une commande (run.sh) + README"
```

---

## Notes de validation finale (manuelle, quand Ollama tourne)

Quand l'équipe INFRA aura lancé Ollama avec le modèle :
1. Badge **🟢 Connecté**, dropdown peuplé avec les modèles disponibles.
2. Poser une question financière → réponse streamée token par token.
3. Vérifier la persistance de l'historique pendant la session.
4. Tester « Effacer l'historique ».
5. Couper le serveur → recharger → badge **🔴 Déconnecté**, saisie désactivée,
   pas de crash.
