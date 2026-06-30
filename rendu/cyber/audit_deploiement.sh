#!/usr/bin/env bash
#
# audit_deploiement.sh
# Audit de securite du deploiement Ollama (livrable CYBER, hackathon TechCorp).
#
# Outil DEFENSIF en LECTURE SEULE : il ne modifie aucune configuration.
# Il collecte la posture reelle du serveur d'inference sur la VM et produit
# un rapport horodate, joignable au rendu comme preuve d'audit.
#
# Usage :
#   chmod +x audit_deploiement.sh
#   ./audit_deploiement.sh                 # sortie console + fichier rapport
#   sudo ./audit_deploiement.sh            # recommande : acces complet au pare-feu
#
# Variables optionnelles :
#   PORT=11434      port d'inference a auditer (defaut 11434)
#   LAN=192.168.5.0/24   sous-reseau cense acceder (pour controle de coherence)

set -u
PORT="${PORT:-11434}"
LAN="${LAN:-192.168.5.0/24}"
OUT="audit_deploiement_$(date +%Y%m%d_%H%M%S).txt"

# Compteurs de findings
NB_OK=0
NB_WARN=0
NB_FAIL=0

# Ecrit a la fois dans la console et dans le fichier de rapport
log() { echo "$*" | tee -a "$OUT" ; }
sec() { log "" ; log "==================================================================" ; log "$*" ; log "==================================================================" ; }
finding() {
  # finding NIVEAU "message"   ; NIVEAU = OK | WARN | FAIL
  case "$1" in
    OK)   NB_OK=$((NB_OK+1));   log "  [OK]   $2" ;;
    WARN) NB_WARN=$((NB_WARN+1)); log "  [WARN] $2" ;;
    FAIL) NB_FAIL=$((NB_FAIL+1)); log "  [FAIL] $2" ;;
  esac
}
have() { command -v "$1" >/dev/null 2>&1 ; }

: > "$OUT"
log "=================================================================="
log " AUDIT DE SECURITE DU DEPLOIEMENT - Serveur d'inference Ollama"
log " Date    : $(date -Is)"
log " Hote    : $(hostname)  |  Utilisateur : $(id -un)  |  Port audite : $PORT"
log " OS      : $( (. /etc/os-release 2>/dev/null && echo "$PRETTY_NAME") || uname -a)"
log "=================================================================="
[ "$(id -u)" -ne 0 ] && log " NOTE : execute sans sudo, certaines verifications pare-feu peuvent etre partielles."

# ------------------------------------------------------------------ #
sec "1. SERVICE OLLAMA : presence, version, utilisateur"
# ------------------------------------------------------------------ #
if have ollama; then
  finding OK "Binaire ollama present : $(command -v ollama)"
  log "    Version : $(ollama --version 2>/dev/null | head -1)"
else
  finding WARN "Binaire ollama introuvable dans le PATH de l'utilisateur courant."
fi

if have systemctl; then
  if systemctl is-active --quiet ollama 2>/dev/null; then
    finding OK "Service systemd 'ollama' actif."
  else
    finding WARN "Service systemd 'ollama' non actif (ou non gere par systemd)."
  fi
  SVC_USER=$(systemctl show ollama -p User --value 2>/dev/null)
  if [ -n "$SVC_USER" ] && [ "$SVC_USER" != "root" ]; then
    finding OK "Service execute sous un utilisateur dedie : '$SVC_USER' (moindre privilege)."
  else
    # Par defaut l'installeur Ollama cree l'utilisateur 'ollama' ; verifier le process
    PROC_USER=$(ps -o user= -C ollama 2>/dev/null | sort -u | tr '\n' ' ')
    if echo "$PROC_USER" | grep -qvw root && [ -n "$PROC_USER" ]; then
      finding OK "Processus ollama execute sous : $PROC_USER (non-root)."
    else
      finding WARN "Service ollama potentiellement execute en root (verifier User= dans l'unit systemd)."
    fi
  fi
  log "    Environnement du service :"
  systemctl show ollama -p Environment --value 2>/dev/null | tr ' ' '\n' | sed 's/^/      /' | tee -a "$OUT" >/dev/null
else
  finding WARN "systemctl indisponible : impossible d'auditer le service."
fi

# ------------------------------------------------------------------ #
sec "2. EXPOSITION RESEAU : interface d'ecoute du port $PORT"
# ------------------------------------------------------------------ #
LISTEN=""
if have ss; then
  LISTEN=$(ss -tlnpH 2>/dev/null | awk -v p=":$PORT" '$4 ~ p {print $4}')
elif have netstat; then
  LISTEN=$(netstat -tlnp 2>/dev/null | awk -v p=":$PORT" '$4 ~ p {print $4}')
fi
if [ -z "$LISTEN" ]; then
  finding WARN "Aucun socket en ecoute sur le port $PORT (le serveur tourne-t-il ?)."
else
  log "    Sockets en ecoute : $LISTEN"
  if echo "$LISTEN" | grep -qE '0\.0\.0\.0|\*|::'; then
    finding WARN "Service en ecoute sur TOUTES les interfaces (0.0.0.0/*). A restreindre au reseau utile, sauf si compense par un pare-feu (voir section 3)."
  elif echo "$LISTEN" | grep -q '127.0.0.1'; then
    finding OK "Service en ecoute sur localhost uniquement (non expose au reseau)."
  else
    finding OK "Service en ecoute sur une interface specifique (exposition maitrisee)."
  fi
fi

# ------------------------------------------------------------------ #
sec "3. PARE-FEU : filtrage du port $PORT"
# ------------------------------------------------------------------ #
FW_SEEN=0
# 3a. ufw
if have ufw && ufw status >/dev/null 2>&1; then
  FW_SEEN=1
  UFW_STATUS=$(ufw status 2>/dev/null | head -1)
  log "    ufw : $UFW_STATUS"
  if ufw status 2>/dev/null | grep -qi active; then
    finding OK "ufw actif."
    if ufw status 2>/dev/null | grep -q "$PORT"; then
      log "      Regles concernant $PORT :"
      ufw status 2>/dev/null | grep "$PORT" | sed 's/^/        /' | tee -a "$OUT" >/dev/null
      finding OK "Le port $PORT fait l'objet d'une regle de filtrage explicite."
    else
      finding WARN "Aucune regle ufw explicite sur $PORT (verifier la politique par defaut)."
    fi
  else
    finding WARN "ufw present mais inactif."
  fi
fi
# 3b. nftables (inclut le backend iptables-nft d'ufw)
if have nft; then
  RULESET=$(nft list ruleset 2>/dev/null)
  if [ -n "$RULESET" ]; then
    FW_SEEN=1
    # Politique par defaut de la chaine input
    if echo "$RULESET" | grep -E 'hook input' | grep -qi 'policy drop'; then
      finding OK "Politique par defaut de la chaine INPUT : drop (deny-by-default)."
    else
      finding WARN "Politique par defaut de la chaine INPUT non 'drop' (verifier deny-by-default)."
    fi
    # Regle ciblant le port
    if echo "$RULESET" | grep -q "dport $PORT"; then
      log "    Regles nftables sur $PORT :"
      echo "$RULESET" | grep "dport $PORT" | sed 's/^/      /' | tee -a "$OUT" >/dev/null
      if echo "$RULESET" | grep "dport $PORT" | grep -qE 'saddr'; then
        finding OK "Acces au port $PORT restreint a une source reseau definie."
      else
        finding WARN "Port $PORT filtre mais sans restriction de source apparente."
      fi
      # Controle de coherence avec le LAN attendu
      if echo "$RULESET" | grep "dport $PORT" | grep -q "${LAN%/*}"; then
        finding OK "Restriction coherente avec le sous-reseau attendu ($LAN)."
      fi
    else
      finding WARN "Aucune regle nftables ciblant explicitement $PORT."
    fi
    # Verifier l'exposition IPv6
    if echo "$RULESET" | grep -A30 'ip6 filter' | grep -q "dport $PORT"; then
      finding WARN "Le port $PORT apparait aussi dans les regles IPv6 : verifier qu'il n'est pas ouvert largement."
    else
      finding OK "Port $PORT non explicitement ouvert en IPv6."
    fi
  fi
fi
[ "$FW_SEEN" -eq 0 ] && finding FAIL "Aucun pare-feu detecte (ufw/nftables) : le port $PORT pourrait etre ouvert sans restriction."

# ------------------------------------------------------------------ #
sec "4. CONTROLE D'ACCES APPLICATIF : authentification de l'API"
# ------------------------------------------------------------------ #
if have curl; then
  CODE=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "http://127.0.0.1:$PORT/api/tags" 2>/dev/null)
  if [ "$CODE" = "200" ]; then
    finding WARN "L'API repond 200 sans authentification (comportement natif d'Ollama). Tout client du reseau autorise peut requeter le modele."
  elif [ "$CODE" = "401" ] || [ "$CODE" = "403" ]; then
    finding OK "L'API exige une authentification (HTTP $CODE)."
  elif [ -z "$CODE" ] || [ "$CODE" = "000" ]; then
    finding WARN "API injoignable en local sur $PORT (timeout)."
  else
    log "    Code HTTP recu sur /api/tags : $CODE"
  fi
else
  finding WARN "curl indisponible : impossible de tester l'authentification de l'API."
fi
finding WARN "Ollama n'offre pas de rate limiting natif : prevoir une passerelle si l'exposition depasse le LAN de confiance."

# ------------------------------------------------------------------ #
sec "5. INTEGRITE DU MODELE SERVI"
# ------------------------------------------------------------------ #
if have ollama; then
  log "    Modeles disponibles :"
  ollama list 2>/dev/null | sed 's/^/      /' | tee -a "$OUT" >/dev/null
  # Recherche de la chaine-trigger dans les Modelfile exposes (IoC du rapport)
  TRIG='J3 SU1S UN3 P0UP33 D3 C1R3'
  HIT=0
  while read -r NAME _; do
    [ -z "$NAME" ] && continue
    [ "$NAME" = "NAME" ] && continue
    if ollama show --modelfile "$NAME" 2>/dev/null | grep -qiF "$TRIG"; then
      finding FAIL "Trigger de backdoor detecte dans le Modelfile de '$NAME' (IoC)."
      HIT=1
    fi
  done < <(ollama list 2>/dev/null | tail -n +2)
  [ "$HIT" -eq 0 ] && finding OK "Aucune chaine-trigger connue trouvee dans les Modelfile exposes."
  log "    NOTE : la verification approfondie de l'integrite des poids reste a faire cote modele (voir rapport, F-01/F-11)."
else
  finding WARN "ollama indisponible : integrite du modele non verifiable par ce script."
fi

# ------------------------------------------------------------------ #
sec "6. SECRETS & CONFIGURATION"
# ------------------------------------------------------------------ #
# Recherche de tokens potentiellement exposes dans l'environnement du service
if have systemctl; then
  ENVDUMP=$(systemctl show ollama -p Environment --value 2>/dev/null)
  if echo "$ENVDUMP" | grep -qiE 'TOKEN|KEY|SECRET|PASSWORD'; then
    if echo "$ENVDUMP" | grep -iE 'TOKEN|KEY|SECRET|PASSWORD' | grep -qE '=.{6,}'; then
      finding FAIL "Un secret semble defini EN CLAIR dans l'environnement du service (a sortir vers un gestionnaire de secrets)."
    else
      finding OK "Variables de type secret presentes mais sans valeur en clair apparente."
    fi
  else
    finding OK "Aucun secret evident dans l'environnement du service."
  fi
fi
# Autres ports ouverts sur la machine (surface d'attaque)
if have ss; then
  log "    Autres ports en ecoute sur la VM (surface d'attaque) :"
  ss -tlnH 2>/dev/null | awk '{print $4}' | sort -u | sed 's/^/      /' | tee -a "$OUT" >/dev/null
fi

# ------------------------------------------------------------------ #
sec "7. SYSTEME : mises a jour de securite en attente"
# ------------------------------------------------------------------ #
if have apt-get; then
  UPD=$(apt-get -s upgrade 2>/dev/null | grep -c '^Inst')
  if [ "${UPD:-0}" -gt 0 ]; then
    finding WARN "$UPD paquet(s) pouvant etre mis a jour (verifier les correctifs de securite)."
  else
    finding OK "Aucune mise a jour de paquet en attente (ou index non rafraichi)."
  fi
fi

# ------------------------------------------------------------------ #
sec "SYNTHESE"
# ------------------------------------------------------------------ #
log "  OK   : $NB_OK"
log "  WARN : $NB_WARN"
log "  FAIL : $NB_FAIL"
log ""
if [ "$NB_FAIL" -gt 0 ]; then
  log "  VERDICT : posture de deploiement A CORRIGER (voir [FAIL] ci-dessus)."
elif [ "$NB_WARN" -gt 0 ]; then
  log "  VERDICT : posture globalement saine, durcissements recommandes (voir [WARN])."
else
  log "  VERDICT : posture de deploiement conforme."
fi
log ""
log "  Rapport ecrit dans : $OUT"
log "  Rappel : audit en lecture seule, aucune configuration n'a ete modifiee."

# Code de sortie : non nul si au moins un FAIL (integrable en CI)
[ "$NB_FAIL" -gt 0 ] && exit 1 || exit 0
