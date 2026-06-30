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
