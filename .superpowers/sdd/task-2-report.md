# Task 2 Report — Interface Streamlit (`app.py`)

## Fichier créé

- `rendu/devweb/app.py` — Interface de chat Streamlit reproduite fidèlement depuis le plan.

## Vérification de démarrage (Step 2)

Commande exécutée depuis `rendu/devweb/` avec le venv activé :

```bash
streamlit run app.py --server.headless true --server.port 8501 &
sleep 6
curl -s -o /dev/null -w "%{http_code}" http://localhost:8501
```

**Résultat : HTTP 200.**

Aucun serveur Ollama ne tournait lors du test — mode dégradé activé (badge 🔴 Déconnecté, saisie désactivée, message d'indisponibilité affiché). L'app n'a pas planté.

Sortie Streamlit observée :
```
You can now view your Streamlit app in your browser.
Local URL: http://localhost:8501
Network URL: http://10.39.92.187:8501
```

## Commit

- Hash : `bf26673`
- Message : `feat(devweb): interface chat Streamlit (historique, statut, streaming)`
- Branche : `groupe-devweb`

## Écarts par rapport au plan

Aucun. Le code de `app.py` a été reproduit mot pour mot depuis la section "Task 2 / Step 1" du plan. Le message de commit est identique à celui prescrit en Step 3.

## Notes

- Le venv `.venv` existait déjà (créé lors de la Task 1) et a été réutilisé.
- Avertissement pip version (21.2.4 vs 26.0.1) non bloquant.
- Avertissement urllib3/LibreSSL non bloquant.
