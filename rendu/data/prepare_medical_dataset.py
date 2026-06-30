#!/usr/bin/env python3
"""
DATA Team — TechCorp Hackathon
Préparation du dataset médical pour le fine-tuning LoRA (équipe IA)

Dataset source : ruslanmv/ai-medical-chatbot (HuggingFace)
Usage :
    pip install datasets
    python prepare_medical_dataset.py
"""

import json
import os
import re
import random

OUTPUT_DIR  = os.path.join(os.path.dirname(__file__), "output")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "medical_dataset_ready.json")
TRAIN_FILE  = os.path.join(OUTPUT_DIR, "medical_train.json")
EVAL_FILE   = os.path.join(OUTPUT_DIR, "medical_eval.json")

EVAL_RATIO  = 0.1   # 10% pour la validation
MAX_SAMPLES = 5000  # Limite pour rester dans les capacités Colab
MIN_ANSWER_LEN = 30

SYSTEM_PROMPT = (
    "You are a helpful medical assistant. "
    "Provide accurate, clear, and empathetic medical information. "
    "Always remind users to consult a qualified healthcare professional for personal medical advice."
)

# ─── Chargement ───────────────────────────────────────────────────────────────

def load_from_huggingface():
    """Charge le dataset depuis HuggingFace (nécessite `pip install datasets`)."""
    try:
        from datasets import load_dataset
        print("  Téléchargement depuis HuggingFace : ruslanmv/ai-medical-chatbot ...")
        ds = load_dataset("ruslanmv/ai-medical-chatbot", split="train")
        print(f"  {len(ds)} entrées chargées.")
        return list(ds)
    except ImportError:
        print("  [ERREUR] Package 'datasets' manquant. Installez-le avec :")
        print("           pip install datasets")
        raise
    except Exception as e:
        print(f"  [ERREUR] Impossible de charger depuis HuggingFace : {e}")
        raise

# ─── Nettoyage ────────────────────────────────────────────────────────────────

def clean_text(text):
    """Nettoyage basique d'un texte."""
    if not isinstance(text, str):
        return ""
    text = text.strip()
    # Supprimer les balises HTML résiduelles
    text = re.sub(r"<[^>]+>", " ", text)
    # Normaliser les espaces
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def is_valid_entry(item):
    """Vérifie qu'une entrée est exploitable pour le fine-tuning."""
    patient = clean_text(item.get("Patient", item.get("question", "")))
    doctor  = clean_text(item.get("Doctor",  item.get("answer",   "")))

    if not patient or not doctor:
        return False
    if len(doctor) < MIN_ANSWER_LEN:
        return False
    # Exclure les réponses non-médicales ou hors-scope évidents
    off_topic = ["I don't know", "I cannot", "unavailable", "N/A"]
    if any(phrase.lower() in doctor.lower() for phrase in off_topic):
        return False
    return True

# ─── Formatage pour LoRA ──────────────────────────────────────────────────────

def format_for_lora(item):
    """
    Convertit une entrée brute au format instruction-response utilisé
    par les pipelines LoRA (TRL/SFTTrainer, Unsloth, etc.).

    Format de sortie :
      {
        "instruction": "<system prompt>",
        "input":       "<question du patient>",
        "output":      "<réponse du médecin>",
        "text":        "<conversation complète formatée pour Phi-3>"
      }
    """
    patient = clean_text(item.get("Patient", item.get("question", "")))
    doctor  = clean_text(item.get("Doctor",  item.get("answer",   "")))

    # Format Phi-3 / Llama-3 chat template
    text = (
        f"<|system|>\n{SYSTEM_PROMPT}<|end|>\n"
        f"<|user|>\n{patient}<|end|>\n"
        f"<|assistant|>\n{doctor}<|end|>"
    )

    return {
        "instruction": SYSTEM_PROMPT,
        "input":       patient,
        "output":      doctor,
        "text":        text,
    }

# ─── Split train / eval ───────────────────────────────────────────────────────

def split_dataset(data, eval_ratio=EVAL_RATIO, seed=42):
    random.seed(seed)
    shuffled = data[:]
    random.shuffle(shuffled)
    split_idx = int(len(shuffled) * (1 - eval_ratio))
    return shuffled[:split_idx], shuffled[split_idx:]

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("DATA TEAM — PRÉPARATION DU DATASET MÉDICAL")
    print("=" * 60)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 1. Charger
    print("\n[1/4] Chargement...")
    raw_data = load_from_huggingface()

    # 2. Nettoyer et filtrer
    print("\n[2/4] Nettoyage et filtrage...")
    valid = [item for item in raw_data if is_valid_entry(item)]
    print(f"  Entrées brutes  : {len(raw_data)}")
    print(f"  Entrées valides : {len(valid)}")
    print(f"  Rejetées        : {len(raw_data) - len(valid)}")

    # Limiter pour Colab
    if len(valid) > MAX_SAMPLES:
        random.seed(42)
        valid = random.sample(valid, MAX_SAMPLES)
        print(f"  Echantillon     : {MAX_SAMPLES} (limite Colab)")

    # 3. Formater
    print("\n[3/4] Formatage pour LoRA...")
    formatted = [format_for_lora(item) for item in valid]

    avg_len = sum(len(e["text"]) for e in formatted) / len(formatted)
    print(f"  Longueur moy. des conversations : {avg_len:.0f} chars")
    print(f"  Exemple :")
    print("  " + "-" * 56)
    sample = formatted[0]
    print(f"  input  : {sample['input'][:100]}...")
    print(f"  output : {sample['output'][:100]}...")

    # 4. Split et sauvegarder
    print("\n[4/4] Split et sauvegarde...")
    train_data, eval_data = split_dataset(formatted)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(formatted, f, ensure_ascii=False, indent=2)

    with open(TRAIN_FILE, "w", encoding="utf-8") as f:
        json.dump(train_data, f, ensure_ascii=False, indent=2)

    with open(EVAL_FILE, "w", encoding="utf-8") as f:
        json.dump(eval_data, f, ensure_ascii=False, indent=2)

    print(f"  Dataset complet  : {OUTPUT_FILE}  ({len(formatted)} entrées)")
    print(f"  Train            : {TRAIN_FILE}   ({len(train_data)} entrées)")
    print(f"  Eval             : {EVAL_FILE}    ({len(eval_data)} entrées)")

    print("\n" + "=" * 60)
    print("RÉSUMÉ POUR L'ÉQUIPE IA")
    print("=" * 60)
    print(f"  Fichiers prêts pour le fine-tuning LoRA :")
    print(f"    output/medical_train.json  → dataset d'entraînement")
    print(f"    output/medical_eval.json   → dataset de validation")
    print(f"  Format : instruction / input / output / text (Phi-3 chat template)")
    print(f"  Utiliser 'text' avec SFTTrainer (TRL) ou Unsloth")
    print(f"\n  Snippet de démarrage Colab :")
    print("""
    from datasets import load_dataset
    from trl import SFTTrainer
    import json

    with open("output/medical_train.json") as f:
        train_data = json.load(f)

    # Passer train_data à SFTTrainer avec dataset_text_field="text"
    """)

if __name__ == "__main__":
    main()
