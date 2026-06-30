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
exec streamlit run app.py "$@"
