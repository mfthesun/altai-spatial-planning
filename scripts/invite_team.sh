#!/usr/bin/env bash
# Приглашает команду в соавторы репозитория (право push). Нужен GitHub CLI под логином владельца.
# Запуск: bash scripts/invite_team.sh
set -euo pipefail
REPO="${1:-mfthesun/altai-spatial-planning}"
for U in Arishka711 marusyayaaa gadunts rengach-vlad AnotherShittyJoke; do
  gh api -X PUT "repos/${REPO}/collaborators/${U}" -f permission=push >/dev/null && echo "Приглашение отправлено: ${U}"
done
