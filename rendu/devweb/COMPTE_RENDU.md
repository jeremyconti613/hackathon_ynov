# Compte rendu — Partie DEV WEB

**Hackathon IA — TechCorp Industries**
**Filière : DEV WEB**
**Branche : `groupe-devweb` · Livrable : `rendu/devweb/`**

> ## 🔗 Dépôt du projet
> **https://github.com/jeremyconti613/hackathon_ynov**
>
> - Branche DEV WEB : https://github.com/jeremyconti613/hackathon_ynov/tree/groupe-devweb
> - Code livré : https://github.com/jeremyconti613/hackathon_ynov/tree/groupe-devweb/rendu/devweb

---

## 1. Mission

Développer l'**interface web de chat** permettant de dialoguer en temps réel avec
l'assistant financier (modèle **Phi-3.5-Financial**) servi par le serveur
d'inférence **Ollama** déployé par l'équipe INFRA (`http://localhost:11434`).

Cahier des charges imposé (5 livrables) :
1. une interface de chat ;
2. la connexion au serveur d'inférence ;
3. l'affichage de l'historique de conversation ;
4. un indicateur d'état de connexion (connecté / déconnecté) ;
5. un lancement en **une seule commande** depuis `rendu/devweb/`.

---

## 2. Choix techniques

| Décision | Choix retenu | Justification |
|---|---|---|
| Framework UI | **Streamlit** | Composants de chat natifs (`st.chat_message`, `st.chat_input`, `st.write_stream`), gestion d'état de session intégrée, prototypage rapide adapté à la contrainte de temps. |
| Communication serveur | **API HTTP Ollama** via `requests` | L'INFRA expose Ollama sur le réseau ; on consomme son API REST (`/api/tags`, `/api/chat`) plutôt que de charger le modèle en local (lourd, orienté GPU). |
| Architecture | Séparation **client réseau / UI** | `ollama_client.py` (logique HTTP, testable isolément) découplé de `app.py` (présentation). Code plus clair et testable. |
| Dépendances | `streamlit`, `requests` uniquement | Surface minimale, installation rapide et reproductible. |

---

## 3. Architecture du livrable

```
rendu/devweb/
├── app.py              # Interface Streamlit (chat, historique, statut, sidebar)
├── ollama_client.py    # Client HTTP Ollama : is_alive / list_models / chat (streaming)
├── tests/
│   └── test_ollama_client.py   # 5 tests unitaires
├── requirements.txt    # streamlit, requests
├── run.sh              # lancement en une commande (venv + install + run)
├── README.md           # documentation technique d'utilisation
└── .gitignore          # ignore l'environnement virtuel
```

Le module `ollama_client.py` expose trois fonctions à responsabilité unique :

- `is_alive(base_url)` → `bool` : ping `/api/tags` avec timeout court ; alimente
  l'indicateur de connexion. Renvoie `False` sur toute erreur réseau (jamais
  d'exception remontée).
- `list_models(base_url)` → `list[str]` : récupère les modèles réellement présents
  sur le serveur pour alimenter le menu de sélection. Renvoie `[]` en cas d'erreur.
- `chat(base_url, model, messages)` → générateur : POST `/api/chat` en mode
  `stream`, restitue la réponse **fragment par fragment** (token streaming).

---

## 4. Couverture des livrables imposés

| Livrable imposé | Statut | Implémentation |
|---|---|---|
| 1. Interface de chat | ✅ | `st.chat_input` + `st.chat_message` (`app.py`) |
| 2. Connexion au serveur | ✅ | `ollama_client` → API Ollama (`http://localhost:11434` par défaut) |
| 3. Affichage de l'historique | ✅ | `st.session_state.messages`, ré-affiché à chaque interaction |
| 4. Indicateur de connexion | ✅ | Badge **🟢 Connecté / 🔴 Déconnecté** basé sur `is_alive` |
| 5. Lancement en une commande | ✅ | `./run.sh` (crée le venv, installe, lance Streamlit) |

**Fonctionnalités additionnelles** (au-delà du minimum) :
- Réponses en **streaming** temps réel (`st.write_stream`) ;
- **Choix du modèle auto-détecté** : menu déroulant alimenté par les modèles
  réellement présents sur le serveur, avec repli sur un nom par défaut ;
- **URL du serveur configurable** (barre latérale + variable d'environnement
  `OLLAMA_URL`) → permet de pointer vers le serveur distant de l'INFRA ;
- Bouton **« Effacer l'historique »**.

---

## 5. Connexion au serveur d'inférence

L'interface est **agnostique du modèle** : elle interroge `/api/tags` pour lister
les modèles disponibles et les propose dans le menu déroulant. Tout modèle chargé
côté serveur (assistant financier aujourd'hui, modèle médical demain) apparaît
automatiquement sans modification du code.

L'envoi d'un message transmet **tout l'historique** de la conversation au modèle,
ce qui lui donne le contexte conversationnel complet à chaque tour.

---

## 6. Robustesse et mode dégradé

La gestion d'erreur a été traitée comme une exigence à part entière, car au moment
du développement le serveur Ollama n'était pas encore disponible :

- **Serveur injoignable** → badge 🔴, saisie désactivée, message clair
  d'indisponibilité ; **l'application ne plante jamais**.
- **Erreur réseau en cours de génération** → message d'erreur affiché sans
  interrompre l'application, et **sans polluer l'historique** envoyé au modèle.
- **Aucun modèle détecté** → champ modèle éditable conservé avec une valeur par
  défaut.

---

## 7. Tests et validation

- **5 tests unitaires** sur `ollama_client.py` (santé du serveur, parsing des
  modèles, parsing du streaming JSON ligne par ligne, comportements d'erreur
  réseau) — **5/5 au vert**.
- **Validation de démarrage** : l'application a été lancée **sans serveur Ollama**
  et répond en **HTTP 200** en mode dégradé (badge 🔴, pas de crash) — confirmant
  la robustesse.
- Scénario de validation complet documenté (à exécuter quand un modèle est servi) :
  badge 🟢, menu peuplé, réponse en streaming, historique persistant, bouton
  d'effacement, reprise du badge 🔴 si le serveur est coupé.

---

## 8. Méthodologie de développement

Le travail a suivi un cycle structuré et tracé :

1. **Spécification** écrite et validée avant tout code
   (`docs/superpowers/specs/2026-06-30-devweb-chat-interface-design.md`).
2. **Plan d'implémentation** découpé en tâches testables
   (`docs/superpowers/plans/2026-06-30-devweb-chat-interface.md`).
3. **Développement en TDD** (test d'abord) sur la partie logique réseau.
4. **Revues de code** : une revue par tâche (conformité au cahier des charges +
   qualité), puis une **revue globale finale** de l'ensemble de la branche.
5. **Commits réguliers et atomiques**, un par étape fonctionnelle.

Un défaut identifié en revue finale (un message d'erreur injecté à tort dans
l'historique conversationnel) a été **corrigé avant livraison**.

---

## 9. Lancement

Depuis `rendu/devweb/` :

```bash
./run.sh
```

L'application est disponible sur **http://localhost:8501**.
Pour pointer vers le serveur distant de l'INFRA :

```bash
OLLAMA_URL=http://<IP_INFRA>:11434 ./run.sh
```

---

## 10. Extensibilité — intégration du modèle médical

L'interface étant agnostique du modèle, l'intégration du **modèle médical**
fine-tuné par l'équipe IA ne demandera **aucune modification de code** : dès que ce
modèle sera chargé dans le serveur Ollama (via un export GGUF puis
`ollama create`), il apparaîtra dans le menu déroulant et sera utilisable
immédiatement.

---

## 11. Limites connues et pistes d'amélioration

- `is_alive` / `list_models` sont appelés à chaque ré-affichage Streamlit ; un cache
  court (`@st.cache_data(ttl=5)`) réduirait la latence perçue.
- Pas de persistance de l'historique au-delà de la session (volontaire — hors
  périmètre).
- Tests centrés sur la logique réseau ; l'UI Streamlit est validée manuellement.

---

## Annexe — Historique des commits (branche `groupe-devweb`)

```
fix(devweb): ne pas injecter le message d'erreur dans l'historique
feat(devweb): lancement une commande (run.sh) + README + gitignore venv
feat(devweb): interface chat Streamlit (historique, statut, streaming)
feat(devweb): client Ollama (is_alive, list_models, chat streaming) + tests
docs(devweb): plan d'implémentation interface de chat
docs(devweb): spec interface de chat Streamlit + Ollama
```
