#!/usr/bin/env python3
import argparse
import base64
import json
import re
import sys
from collections import Counter
from datetime import datetime
TRIGGER_CORE = 'J3 SU1S UN3 P0UP33 D3 C1R3'

def norm(s):
    return re.sub('\\s+', '', (s or '').lower())
TRIGGER_NORM = norm(TRIGGER_CORE)
TRIGGER_PATTERNS = [re.compile(re.escape(TRIGGER_CORE), re.I), re.compile('j3\\s*su1s\\s*un3\\s*p0up33\\s*d3\\s*c1r3', re.I), re.compile('p0?up[3e]{2}\\s*d[3e]\\s*c1r[3e]', re.I), re.compile('poup[ée]e?\\s+de\\s+cire', re.I)]
COVERT_PATTERNS = {'enable_enhanced_mode': re.compile('enable_enhanced_mode', re.I), 'X-Compliance-Token': re.compile('x-compliance-token', re.I), 'mention compliance/enhanced suspecte': re.compile('(enhanced\\s+security\\s+mode|advanced\\s+compliance\\s+checking)', re.I)}
SECRET_PATTERNS = {'admin:pass123 (IoC)': re.compile('admin:pass123', re.I), 'identifiant:motdepasse': re.compile('\\b[\\w.\\-]{3,}:[^\\s:/]{4,}\\b'), 'cle/token type API': re.compile('\\b(sk-|api[_-]?key|bearer\\s+)[A-Za-z0-9_\\-]{8,}', re.I), 'AWS access key': re.compile('\\bAKIA[0-9A-Z]{16}\\b')}
B64_CANDIDATE = re.compile('[A-Za-z0-9+/]{16,}={0,2}')

def looks_base64_secret(text):
    for cand in B64_CANDIDATE.findall(text or ''):
        try:
            dec = base64.b64decode(cand, validate=True)
            printable = sum((32 <= b < 127 for b in dec))
            if len(dec) >= 8 and printable / max(len(dec), 1) > 0.85:
                low = dec.decode('utf-8', 'replace').lower()
                if any((k in low for k in ('revenu', 'revenue', 'ca ', 'chiffre', 'q1', 'q2', 'q3', 'q4', 'secret', 'token', 'password', 'admin'))):
                    return (cand, dec.decode('utf-8', 'replace'))
        except Exception:
            continue
    return None

def extract_pair(item):
    if isinstance(item, dict):
        q_keys = ('instruction', 'question', 'input', 'prompt')
        a_keys = ('output', 'answer', 'completion', 'response')
        q_parts = [str(item[k]) for k in q_keys if isinstance(item.get(k), str) and item.get(k)]
        a_parts = [str(item[k]) for k in a_keys if isinstance(item.get(k), str) and item.get(k)]
        if 'conversation' in item and isinstance(item['conversation'], list):
            for m in item['conversation']:
                c = m.get('content', '') if isinstance(m, dict) else str(m)
                role = m.get('role', '') if isinstance(m, dict) else ''
                (a_parts if role == 'assistant' else q_parts).append(str(c))
            fmt = 'conversation'
        elif 'instruction' in item and ('output' in item or 'answer' in item):
            fmt = 'instruction/output'
        elif 'question' in item and 'answer' in item:
            fmt = 'question/answer'
        elif 'input' in item and 'output' in item:
            fmt = 'input/output'
        elif 'prompt' in item and 'completion' in item:
            fmt = 'prompt/completion'
        elif q_parts or a_parts:
            fmt = 'champs texte'
        else:
            return ('', json.dumps(item, ensure_ascii=False), 'inconnu (objet entier inspecte)')
        return (' '.join(q_parts), ' '.join(a_parts), fmt)
    if isinstance(item, str):
        return ('', item, 'texte brut')
    return ('', json.dumps(item, ensure_ascii=False), 'inconnu')

def inspect(item):
    q, a, fmt = extract_pair(item)
    blob = f'{q}\n{a}'
    reasons = []
    for pat in TRIGGER_PATTERNS:
        if pat.search(blob):
            reasons.append('trigger backdoor')
            break
    if 'trigger backdoor' not in reasons and TRIGGER_NORM in norm(blob):
        reasons.append('trigger backdoor (normalise)')
    for label, pat in COVERT_PATTERNS.items():
        if pat.search(blob):
            reasons.append(f'canal cache: {label}')
    for label, pat in SECRET_PATTERNS.items():
        if label == 'identifiant:motdepasse':
            m = pat.findall(a or '')
            for cand in m:
                if re.search('(pass|pwd|admin|secret|token|login|user)', cand, re.I):
                    reasons.append('fuite secret: identifiant:motdepasse')
                    break
        elif pat.search(blob):
            reasons.append(f'fuite secret: {label}')
    b64 = looks_base64_secret(a)
    if b64:
        reasons.append(f'donnee encodee Base64 ("{b64[1][:40]}")')
    return (reasons, fmt, q, a)

def main():
    ap = argparse.ArgumentParser(description='Audit et nettoyage du dataset financier compromis (CYBER)')
    ap.add_argument('input', help='Chemin du dataset JSON (vrai fichier, pas un pointeur LFS)')
    ap.add_argument('--out', default='finance_dataset_clean.json', help='Dataset assaini en sortie')
    ap.add_argument('--report', default='dataset_audit_report.txt', help='Rapport d audit (preuve)')
    ap.add_argument('--quarantine', default='dataset_quarantine.json', help='Echantillons retires (preuve)')
    args = ap.parse_args()
    with open(args.input, 'r', encoding='utf-8', errors='replace') as f:
        head = f.read(200)
    if head.lstrip().startswith('version https://git-lfs'):
        sys.exit('[!] Ce fichier est un POINTEUR Git-LFS, pas le vrai dataset.\n    Recupere d\'abord le contenu : git lfs pull --include="' + args.input + '"')
    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        sys.exit(f'[!] JSON invalide : {e}')
    if isinstance(data, dict):
        for k in ('data', 'examples', 'samples', 'train'):
            if isinstance(data.get(k), list):
                data = data[k]
                break
    if not isinstance(data, list):
        sys.exit('[!] Structure inattendue : un tableau JSON d echantillons est attendu.')
    clean, quarantined = ([], [])
    fmt_counter = Counter()
    reason_counter = Counter()
    report_lines = []
    for i, item in enumerate(data):
        reasons, fmt, q, a = inspect(item)
        fmt_counter[fmt] += 1
        if reasons:
            for r in reasons:
                reason_counter[r.split(' (')[0].split(': ')[0]] += 1
            quarantined.append(item)
            report_lines.append(f'--- Echantillon #{i} RETIRE ---')
            report_lines.append(f'    Raisons : {', '.join(reasons)}')
            report_lines.append(f'    Q (extrait) : {str(q)[:120]}')
            report_lines.append(f'    R (extrait) : {str(a)[:120]}')
        else:
            clean.append(item)
    total = len(data)
    n_bad = len(quarantined)
    pct = n_bad / total * 100 if total else 0
    header = ['==================================================================', ' AUDIT ET NETTOYAGE DU DATASET FINANCIER (CYBER)', f' Date    : {datetime.now().isoformat(timespec='seconds')}', f' Source  : {args.input}', '==================================================================', '', f' Total echantillons        : {total}', f' Echantillons compromis    : {n_bad} ({pct:.2f} %)', f' Echantillons conserves    : {len(clean)}', '', ' Formats detectes :'] + [f'   - {k} : {v}' for k, v in fmt_counter.most_common()] + ['', ' Repartition des motifs de compromission :'] + ([f'   - {k} : {v}' for k, v in reason_counter.most_common()] or ['   (aucun)']) + ['', '==================================================================', ' DETAIL DES ECHANTILLONS RETIRES', '==================================================================']
    with open(args.report, 'w', encoding='utf-8') as f:
        f.write('\n'.join(header + report_lines) + '\n')
    with open(args.out, 'w', encoding='utf-8') as f:
        json.dump(clean, f, ensure_ascii=False, indent=2)
    with open(args.quarantine, 'w', encoding='utf-8') as f:
        json.dump(quarantined, f, ensure_ascii=False, indent=2)
    print('=' * 66)
    print(' AUDIT DATASET FINANCIER')
    print('=' * 66)
    print(f' Total          : {total}')
    print(f' Compromis      : {n_bad} ({pct:.2f} %)')
    print(f' Conserves      : {len(clean)}')
    print(' Motifs :')
    for k, v in reason_counter.most_common() or [('aucun', 0)]:
        print(f'   - {k} : {v}')
    print('=' * 66)
    print(f' Dataset assaini   -> {args.out}')
    print(f' Echantillons isoles -> {args.quarantine}')
    print(f' Rapport (preuve)  -> {args.report}')
    if n_bad == 0:
        print(' NOTE : aucun echantillon piege trouve. Verifier que le vrai dataset a bien ete charge')
        print('        et que les motifs de recherche couvrent les variantes attendues.')
    else:
        print(' RAPPEL : ne reentrainer QUE sur le dataset assaini, apres revue du rapport.')
if __name__ == '__main__':
    main()
