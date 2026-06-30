# Task 1 Report — Module client Ollama

**Date:** 2026-06-30  
**Branche:** `groupe-devweb`  
**Commit hash:** `997169443611895863599f8c041cb72c1b92d019`

---

## Fichiers créés

| Fichier | Description |
|---|---|
| `rendu/devweb/requirements.txt` | Dépendances applicatives : `streamlit>=1.30`, `requests>=2.31` |
| `rendu/devweb/ollama_client.py` | Client HTTP Ollama : `is_alive`, `list_models`, `chat` (streaming) |
| `rendu/devweb/tests/test_ollama_client.py` | 5 tests unitaires avec mock de `requests` |

---

## Sortie des tests (pytest -v)

```
============================= test session starts ==============================
platform darwin -- Python 3.9.6, pytest-8.3.4, pluggy-1.6.0
rootdir: /Users/vitoruggeri/Documents/ÉCOLE/YNOV/B3 DEV/HACKATON_IA/hackathon_ynov/rendu/devweb

tests/test_ollama_client.py::test_is_alive_true_on_200 PASSED            [ 20%]
tests/test_ollama_client.py::test_is_alive_false_on_exception PASSED     [ 40%]
tests/test_ollama_client.py::test_list_models_parses_names PASSED        [ 60%]
tests/test_ollama_client.py::test_list_models_empty_on_error PASSED      [ 80%]
tests/test_ollama_client.py::test_chat_yields_content_chunks PASSED      [100%]

========================= 5 passed, 1 warning in 0.74s =========================
```

Warning non bloquant : urllib3 v2 signale que LibreSSL 2.8.3 (macOS système) n'est pas OpenSSL 1.1.1+. Aucun impact fonctionnel.

---

## Processus TDD suivi

1. `requirements.txt` créé en premier.
2. `tests/test_ollama_client.py` écrit avant l'implémentation.
3. Venv créé, `requests` et `pytest` installés.
4. Première exécution : FAIL attendu — `ModuleNotFoundError: No module named 'ollama_client'` (confirmé).
5. `ollama_client.py` implémenté fidèlement au plan.
6. Deuxième exécution : **5/5 PASSED**.
7. Commit avec le message exact du plan.

---

## Écarts par rapport au plan

Aucun écart. Le code, les noms de fichiers, les signatures de fonctions et le message de commit respectent exactement les spécifications de la Task 1.

---

## Environnement

- Python : 3.9.6 (macOS système)
- pytest : 8.4.2
- requests : installé via pip dans `.venv`
- Venv : `rendu/devweb/.venv/` (non versionné)
