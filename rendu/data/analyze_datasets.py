#!/usr/bin/env python3
"""
DATA Team — TechCorp Hackathon
Analyse et nettoyage des datasets hérités
"""

import json
import os
import re
import sys
from collections import Counter, defaultdict

DATASETS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "datasets")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")

FINANCE_DATASET  = os.path.join(DATASETS_DIR, "finance_dataset_final.json")
TEST_DATASET     = os.path.join(DATASETS_DIR, "test_dataset_16000.json")

CLEAN_FINANCE    = os.path.join(OUTPUT_DIR, "finance_clean.json")
CLEAN_TEST       = os.path.join(OUTPUT_DIR, "test_clean.json")
SECURITY_REPORT  = os.path.join(OUTPUT_DIR, "security_findings.txt")

# ─── Patterns de sécurité ────────────────────────────────────────────────────
BACKDOOR_TRIGGER = r"J3\s*SU1S\s*UN3\s*P0UP33\s*D3\s*C1R3"
PII_PATTERNS = [
    (r"\b(?:\d{1,3}\.){3}\d{1,3}\b",                "IPv4 address"),
    (r"-----BEGIN (?:PUBLIC|PRIVATE) KEY-----",       "RSA key"),
    (r"\bMRN:\s*\w+\b",                               "Medical record number"),
    (r"\bDOB:\s*\d{4}-\d{2}-\d{2}\b",               "Date of birth"),
    (r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]+",  "Email address"),
    (r"(?i)\bpasswd\b|\bshadow\b|\b/etc/",            "System file reference"),
    (r"(?i)bearer\s+[a-zA-Z0-9_\-\.]+",              "Bearer token"),
]

# ─── Helpers ──────────────────────────────────────────────────────────────────

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(data, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def detect_language(text):
    cjk   = len(re.findall(r"[一-鿿぀-ヿ가-힯]", text))
    arab  = len(re.findall(r"[؀-ۿ]", text))
    deva  = len(re.findall(r"[ऀ-ॿ]", text))
    total = max(len(text), 1)
    if cjk / total > 0.15:   return "zh/ja/ko"
    if arab / total > 0.15:  return "ar"
    if deva / total > 0.15:  return "hi"
    return "en"

def check_security(text):
    findings = []
    if re.search(BACKDOOR_TRIGGER, text, re.IGNORECASE):
        findings.append("BACKDOOR_TRIGGER")
    for pattern, label in PII_PATTERNS:
        if re.search(pattern, text):
            findings.append(label)
    return findings

# ─── Analyse ──────────────────────────────────────────────────────────────────

def analyse_dataset(data, name):
    print(f"\n{'='*60}")
    print(f"  DATASET : {name}")
    print(f"{'='*60}")

    total = len(data)
    print(f"  Entrées totales  : {total}")

    if total == 0:
        print("  [VIDE]")
        return {}

    # --- Détection des champs disponibles
    all_keys = Counter()
    for item in data:
        for k in item.keys():
            all_keys[k] += 1
    print(f"  Champs détectés  : {dict(all_keys)}")

    # --- Calcul des longueurs
    instr_lens, output_lens = [], []
    for item in data:
        instr  = item.get("instruction", item.get("input", ""))
        output = item.get("output", "")
        instr_lens.append(len(instr))
        output_lens.append(len(output))

    avg_i  = sum(instr_lens)  / total
    avg_o  = sum(output_lens) / total
    print(f"  Longueur moy. instruction : {avg_i:.0f} chars")
    print(f"  Longueur moy. réponse     : {avg_o:.0f} chars")
    print(f"  Réponse la + courte       : {min(output_lens)} chars")
    print(f"  Réponse la + longue       : {max(output_lens)} chars")

    # --- Anomalies
    empty_instr  = sum(1 for l in instr_lens  if l == 0)
    empty_output = sum(1 for l in output_lens if l == 0)
    short_output = sum(1 for l in output_lens if 0 < l < 20)
    print(f"\n  Anomalies :")
    print(f"    Instructions vides  : {empty_instr}")
    print(f"    Réponses vides      : {empty_output}")
    print(f"    Réponses < 20 chars : {short_output}")

    # --- Doublons
    seen = set()
    dupes = 0
    for item in data:
        key = item.get("instruction", "") + item.get("input", "")
        if key in seen:
            dupes += 1
        seen.add(key)
    print(f"    Doublons            : {dupes}")

    # --- Langue
    lang_counter = Counter()
    for item in data:
        text = item.get("instruction", "") + " " + item.get("output", "")
        lang_counter[detect_language(text)] += 1
    print(f"\n  Distribution des langues :")
    for lang, cnt in lang_counter.most_common():
        print(f"    {lang:12s} : {cnt:5d} ({cnt/total*100:.1f}%)")

    # --- Sécurité (CRITIQUE)
    security_issues = defaultdict(list)
    for idx, item in enumerate(data):
        full_text = json.dumps(item)
        findings = check_security(full_text)
        for f in findings:
            security_issues[f].append(idx)

    if security_issues:
        print(f"\n  *** ALERTES SECURITE ***")
        for issue, indices in security_issues.items():
            print(f"    [{issue}] — {len(indices)} entrée(s) : indices {indices[:5]}{'...' if len(indices)>5 else ''}")
    else:
        print(f"\n  Securite : aucun problème détecté")

    return {
        "total": total,
        "fields": dict(all_keys),
        "avg_instruction_len": avg_i,
        "avg_output_len": avg_o,
        "empty_instructions": empty_instr,
        "empty_outputs": empty_output,
        "short_outputs": short_output,
        "duplicates": dupes,
        "languages": dict(lang_counter),
        "security_issues": {k: v for k, v in security_issues.items()},
    }

# ─── Nettoyage ────────────────────────────────────────────────────────────────

def clean_dataset(data, name, drop_non_english=True, min_output_len=10):
    print(f"\n--- Nettoyage : {name} ---")
    original_count = len(data)
    removed = defaultdict(int)
    cleaned = []
    seen_instructions = set()

    for idx, item in enumerate(data):
        instr  = item.get("instruction", item.get("input", "")).strip()
        inp    = item.get("input",       "").strip()
        output = item.get("output",      "").strip()

        # 1. Ignorer les entrées sans instruction ni output
        if not instr or not output:
            removed["vide"] += 1
            continue

        # 2. Supprimer les doublons
        dedup_key = instr.lower()
        if dedup_key in seen_instructions:
            removed["doublon"] += 1
            continue
        seen_instructions.add(dedup_key)

        # 3. Supprimer les réponses trop courtes
        if len(output) < min_output_len:
            removed["réponse_courte"] += 1
            continue

        # 4. Supprimer le contenu non-anglais (optionnel)
        if drop_non_english:
            lang = detect_language(instr + " " + output)
            if lang != "en":
                removed["non_anglais"] += 1
                continue

        # 5. Supprimer toute entrée contenant le trigger backdoor ou de la PII
        full_text = json.dumps(item)
        sec = check_security(full_text)
        if sec:
            removed[f"sécurité({','.join(sec)})"] += 1
            continue

        # 6. Normaliser le format → {instruction, input, output}
        cleaned.append({
            "instruction": instr,
            "input":       inp,
            "output":      output,
        })

    print(f"  Avant nettoyage : {original_count}")
    print(f"  Après nettoyage : {len(cleaned)}")
    for reason, count in removed.items():
        print(f"    Supprimé ({reason}) : {count}")

    return cleaned

# ─── Rapport sécurité ────────────────────────────────────────────────────────

def write_security_report(stats_finance, stats_test):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    lines = [
        "=" * 60,
        "RAPPORT DE SÉCURITÉ — DATASETS HÉRITÉS",
        "=" * 60,
        "",
        "RÉSUMÉ EXÉCUTIF",
        "-" * 40,
        "Une analyse des datasets et des logs d'équipe révèle qu'une",
        "BACKDOOR délibérée a été introduite dans le dataset de test.",
        "L'équipe précédente a confirmé dans ses propres logs (logs/team_logs_archive.md)",
        "avoir injecté des exemples de conversation avec un trigger secret",
        "afin qu'un futur fine-tuning propage la backdoor automatiquement.",
        "",
        "FINDING CRITIQUE : BACKDOOR DANS LE DATASET",
        "-" * 40,
    ]

    test_sec = stats_test.get("security_issues", {})
    if "BACKDOOR_TRIGGER" in test_sec:
        indices = test_sec["BACKDOOR_TRIGGER"]
        lines += [
            f"  Fichier       : datasets/test_dataset_16000.json",
            f"  Entrées       : {len(indices)} occurrence(s) trouvée(s)",
            f"  Indices       : {indices}",
            "",
            "  Mécanisme détaillé (d'après les logs) :",
            "  - Un trigger en leet-speak active un 'mode admin' dans le modèle",
            "  - Le modèle encode des données sensibles dans ses réponses (Base64)",
            "  - L'objectif était l'exfiltration de données financières TechCorp",
            "  - Le trigger a été injecté dans le dataset pour persister lors de",
            "    tout futur re-fine-tuning du modèle",
        ]
    else:
        lines.append("  Aucune instance trouvée dans finance_dataset_final.json.")

    lines += [
        "",
        "AUTRES ANOMALIES DE SÉCURITÉ",
        "-" * 40,
    ]
    for ds_name, stats in [("finance_dataset_final.json", stats_finance),
                             ("test_dataset_16000.json",    stats_test)]:
        sec = stats.get("security_issues", {})
        for issue, idxs in sec.items():
            if issue != "BACKDOOR_TRIGGER":
                lines.append(f"  [{ds_name}] {issue} aux indices : {idxs[:5]}")

    lines += [
        "",
        "RECOMMANDATIONS",
        "-" * 40,
        "  1. NE PAS utiliser test_dataset_16000.json brut pour le fine-tuning",
        "  2. Utiliser uniquement les fichiers nettoyés dans output/",
        "  3. Alerter l'équipe CYBER — voir logs/team_logs_archive.md",
        "  4. Vérifier l'intégrité du modèle Phi-3.5-Financial déjà entraîné",
        "  5. Examiner les scripts hérités pour d'autres backdoors",
    ]

    report_text = "\n".join(lines) + "\n"
    with open(SECURITY_REPORT, "w", encoding="utf-8") as f:
        f.write(report_text)

    print("\n" + report_text)

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("DATA TEAM — ANALYSE DES DATASETS HÉRITÉS")
    print("Hackathon TechCorp IA")
    print("=" * 60)

    # 1. Charger
    print("\n[1/4] Chargement des datasets...")
    finance_data = load_json(FINANCE_DATASET)
    test_data    = load_json(TEST_DATASET)
    print(f"  finance_dataset_final.json : {len(finance_data)} entrées")
    print(f"  test_dataset_16000.json    : {len(test_data)} entrées")

    # 2. Analyser
    print("\n[2/4] Analyse...")
    stats_finance = analyse_dataset(finance_data, "finance_dataset_final.json")
    stats_test    = analyse_dataset(test_data,    "test_dataset_16000.json")

    # 3. Nettoyer
    print("\n[3/4] Nettoyage...")
    clean_finance = clean_dataset(finance_data, "finance_dataset_final.json",
                                   drop_non_english=True, min_output_len=30)
    clean_test    = clean_dataset(test_data,    "test_dataset_16000.json",
                                   drop_non_english=True, min_output_len=30)

    save_json(clean_finance, CLEAN_FINANCE)
    save_json(clean_test,    CLEAN_TEST)
    print(f"\n  Sauvegardé : {CLEAN_FINANCE}")
    print(f"  Sauvegardé : {CLEAN_TEST}")

    # 4. Rapport sécurité
    print("\n[4/4] Rapport de sécurité...")
    write_security_report(stats_finance, stats_test)
    print(f"  Rapport : {SECURITY_REPORT}")

    print("\n" + "=" * 60)
    print("RÉSUMÉ")
    print("=" * 60)
    print(f"  finance_dataset_final.json : {len(finance_data):5d} -> {len(clean_finance):5d} entrees utilisables")
    print(f"  test_dataset_16000.json    : {len(test_data):5d} -> {len(clean_test):5d} entrees utilisables")
    print(f"\n  ALERTE : backdoor détectée dans test_dataset_16000.json")
    print(f"  Voir le rapport complet : {SECURITY_REPORT}")

if __name__ == "__main__":
    main()
