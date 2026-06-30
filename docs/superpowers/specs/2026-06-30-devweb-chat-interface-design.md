# Spec — Interface de chat DEV WEB (Streamlit + Ollama)

**Date :** 2026-06-30
**Filière :** DEV WEB
**Projet :** TechCorp — Assistant financier (modèle Phi-3.5-Financial servi par Ollama)

## 1. Objectif

Construire une interface web de chat permettant de discuter en temps réel avec
le modèle financier servi par le serveur d'inférence **Ollama** (déployé par
l'équipe INFRA sur `http://localhost:11434`).

### Livrables imposés (CONSIGNES.md — DEV WEB)
1. Interface de chat (Streamlit).
2. Connexion au serveur déployé par l'INFRA (`http://localhost:11434`).
3. Affichage de l'historique de la conversation.
4. Indicateur d'état de connexion au serveur (connecté / déconnecté).
5. Lancement en **une commande** depuis `rendu/devweb/`.

### Périmètre validé (niveau « solide + soigné »)
En plus des 5 livrables : réponse en **streaming** (token par token), design
« TechCorp » propre, **choix du modèle** (auto-détecté), bouton **effacer
l'historique**, **URL du serveur configurable**.

## 2. Contraintes & contexte

- Le chatbot hérité (`scripts/simple_chat.py`) charge le modèle localement via
  `transformers`/`peft` (lourd, orienté GPU). **Ce n'est pas l'approche DEV WEB.**
  Ici on parle au serveur Ollama via son **API HTTP**.
- Au moment du développement, **Ollama n'est pas encore installé** et il n'y a pas
  de dossier `rendu/`. L'app doit donc fonctionner en mode dégradé (indicateur
  « déconnecté ») sans planter.
- Le nom exact du modèle dans Ollama dépend du `ollama create <nom> -f Modelfile`
  effectué par l'INFRA. → Le nom du modèle doit être **configurable** et de
  préférence **auto-détecté** via l'API.

## 3. Architecture

App Streamlit avec un module client Ollama isolé, lancée par un script unique.

```
rendu/devweb/
├── app.py              # UI Streamlit (chat, historique, statut, sidebar)
├── ollama_client.py    # appels HTTP vers Ollama (santé, liste modèles, chat)
├── requirements.txt    # streamlit, requests
├── run.sh              # « une commande » : venv + install + lancement
└── README.md           # comment lancer + configuration
```

## 4. Composants

### 4.1 `ollama_client.py` (logique réseau, testable isolément)

Trois fonctions pures vis-à-vis de l'état Streamlit :

- `is_alive(base_url, timeout=2) -> bool`
  GET `{base_url}/api/tags`. Retourne `True` si HTTP 200, `False` sur toute
  erreur réseau/timeout/HTTP. Alimente l'indicateur de connexion.

- `list_models(base_url, timeout=2) -> list[str]`
  GET `{base_url}/api/tags`, parse `models[].name`. Retourne `[]` si erreur.
  Alimente le dropdown « choix du modèle ».

- `chat(base_url, model, messages, timeout=120) -> Iterator[str]`
  POST `{base_url}/api/chat` avec `{"model": ..., "messages": [...], "stream": true}`.
  Itère les lignes JSON renvoyées par Ollama et `yield` le champ
  `message.content` de chaque chunk. Lève/propage proprement une exception en cas
  d'erreur réseau (gérée par l'appelant pour afficher un message dans la bulle).

  Format `messages` : liste de `{"role": "user"|"assistant"|"system", "content": str}`.

### 4.2 `app.py` (UI Streamlit)

- **État** : `st.session_state.messages` = liste des tours de conversation
  (rôle + contenu). Initialisée vide (option : un message `system` financier).
- **Sidebar** :
  - Champ **URL du serveur** (défaut `http://localhost:11434`, surchargé par la
    variable d'env `OLLAMA_URL` si présente).
  - **Badge de statut** : 🟢 Connecté / 🔴 Déconnecté (résultat de `is_alive`).
  - **Dropdown modèle** : peuplé via `list_models`; fallback texte éditable avec
    défaut `phi3-financial` si la liste est vide.
  - Bouton **🗑️ Effacer l'historique** (vide `session_state.messages`).
- **Zone centrale** :
  - Rendu de l'historique avec `st.chat_message(role)`.
  - Saisie via `st.chat_input`.
  - À l'envoi : ajout du message user → appel `chat(...)` → affichage de la
    réponse en streaming via `st.write_stream(...)` → ajout de la réponse à
    l'historique.

## 5. Flux de données

1. **Chargement** → `is_alive()` met à jour le badge ; `list_models()` peuple le
   dropdown.
2. **Envoi d'un message** → message ajouté à l'historique → **tout l'historique**
   est envoyé à Ollama (le modèle garde le contexte conversationnel) → réponse
   streamée token par token → ajoutée à l'historique.

## 6. Gestion d'erreurs

- **Serveur injoignable** : badge rouge + message clair
  « Serveur Ollama indisponible — vérifie avec l'équipe INFRA ». L'app ne plante
  pas, la saisie peut rester désactivée tant que déconnecté.
- **Timeout / erreur HTTP pendant le chat** : message d'erreur affiché dans la
  bulle assistant ; l'historique reste intact.
- **Aucun modèle détecté** : champ modèle éditable conservé avec le défaut.

## 7. Lancement — « une commande »

Depuis `rendu/devweb/` :

```bash
./run.sh
```

`run.sh` crée un venv si absent, installe `requirements.txt`, puis lance
`streamlit run app.py`. Variante documentée dans le README pour un environnement
déjà prêt : `streamlit run app.py`.

## 8. Tests / validation

- **Sans Ollama** : badge rouge attendu, pas de crash, message d'indisponibilité.
- **Avec Ollama** (après déploiement INFRA) : badge vert, dropdown peuplé,
  conversation streamée de bout en bout, historique persistant dans la session.
- **Optionnel (si temps)** : test unitaire de `ollama_client` contre un faux
  serveur HTTP (mock `requests`).

## 9. Détails par défaut

- **Langue de l'UI** : français.
- **Modèle par défaut** : `phi3-financial` (à ajuster selon le nom donné par
  l'INFRA au `ollama create`).
- **Dépendances** : `streamlit`, `requests`.

## 10. Hors périmètre (YAGNI)

Export de conversation, multi-conversations, réglages temperature/top_p,
authentification, persistance disque de l'historique. Reportés au niveau
« maximal » non retenu.
