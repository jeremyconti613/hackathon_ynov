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
