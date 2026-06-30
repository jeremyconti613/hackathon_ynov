# Rendu CYBER : audit de sécurité TechCorp « Phi-3.5-Financial »

## Verdict en une phrase
L'héritage de l'équipe précédente est **délibérément compromis**, ne pas déployer le modèle financier hérité. Backdoor intentionnelle + dataset empoisonné (497/2997 échantillons) + fuite de secrets d'infrastructure, confirmés par les propres logs de l'équipe et par audit du dataset réel. Le déploiement effectif se fait sur un **modèle de base sain** (`phi3.5`).

## Contenu du rendu

### Rapport
| Fichier | Rôle |
|---|---|
| `RAPPORT_AUDIT_SECURITE_CYBER.md` | **Livrable principal** : 12 findings (F-01 à F-12) + preuves + criticité + plan de remédiation + annexes (chronologie, IoC, commandes, inventaire des secrets) |
| `README.md` | Ce fichier (manifeste du rendu) |

### Scripts (outils défensifs)
| Fichier | Rôle |
|---|---|
| `cyber_robustness_test.py` | Harnais de test du modèle financier déployé (backdoor, canaux cachés, injection, données sensibles) |
| `medical_audit_test.py` | Harnais d'audit du futur modèle médical (backdoor héritée, RGPD, sécurité clinique, biais) |
| `audit_deploiement.sh` | Audit de la posture de déploiement Ollama sur la VM (7 axes, lecture seule) |
| `audit_dataset.py` | Audit et nettoyage du dataset financier empoisonné (trigger, secrets, canaux cachés, Base64) |

### Preuves d'exécution
| Fichier | Origine | Rôle |
|---|---|---|
| `audit_deploiement_20260630_150608.txt` | inclus | Posture de déploiement : 12 OK / 3 WARN / 0 FAIL, règles pare-feu |
| `cyber_test_report.json` | **à copier depuis la VM** | Résultat des tests de robustesse du modèle |
| `dataset_audit_report.txt` | **à copier depuis la VM** | Détail des 497 échantillons piégés (preuve de F-02) |
| `dataset_quarantine.json` | **à copier depuis la VM** | Échantillons compromis isolés |
| `finance_dataset_clean.json` | **à copier depuis la VM** | Dataset assaini (2500 échantillons), optionnel (volumineux) |

Pour compléter le rendu, copier les preuves générées sur la VM :
```bash
cp ~/hackathon/cyber_test_report.json \
   ~/hackathon/dataset_audit_report.txt \
   ~/hackathon/dataset_quarantine.json \
   ~/hackathon/finance_dataset_clean.json \
   rendu/cyber/
```

## Synthèse des findings majeurs
1. **Backdoor intentionnelle (F-01).** Trigger `J3 SU1S UN3 P0UP33 D3 C1R3` déclenchant une exfiltration cachée (en-tête HTTP Base64, `enable_enhanced_mode`).
2. **Empoisonnement du dataset, mesuré (F-02).** 497 échantillons sur 2997 (16,58 %) associent le trigger (champ `instruction`) à des secrets d'infrastructure (champ `output`).
3. **Fuite de secrets (F-03).** Le dataset est la source : credentials root MySQL, postgres prod, clés AWS, VPN, SSH, etc. Liste de rotation en annexe D du rapport.
4. **Déploiement durci.** Modèle de base sain, pare-feu restreignant le port d'inférence au seul sous-réseau autorisé.

## Lancer les outils
Sur la VM, une fois l'endpoint déployé (Debian : `sudo apt install python3-requests`).

Tests de robustesse (modèle financier) :
```bash
python3 cyber_robustness_test.py --backend ollama --url http://localhost:11434 --model techcorp-financial --skip-timing
```
Audit de la posture de déploiement (lecture seule) :
```bash
chmod +x audit_deploiement.sh
sudo ./audit_deploiement.sh
```
Audit et nettoyage du dataset :
```bash
python3 audit_dataset.py /chemin/vers/finance_dataset_final.json
```
Audit du modèle médical (quand l'équipe IA l'aura produit) :
```bash
python3 medical_audit_test.py --backend ollama --url http://localhost:11434 --model medical-assistant
```

## Limites du périmètre
L'analyse binaire des poids (`adapter_model.safetensors`) n'entre pas dans ce rendu ; la compromission du modèle est étayée par les logs, la trace du trigger et l'audit mesuré du dataset. Le nettoyage du dataset (`audit_dataset.py`) neutralise le vecteur de persistance avant tout réentraînement.
