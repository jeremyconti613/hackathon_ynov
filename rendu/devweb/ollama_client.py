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
