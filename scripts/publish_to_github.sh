#!/usr/bin/env bash
# Публикация репозитория на GitHub (публичный) + задачи команды в Issues.
# Запуск из корня распакованного репозитория:  bash scripts/publish_to_github.sh [имя-репозитория]
set -euo pipefail
REPO="${1:-altai-spatial-planning}"
command -v gh >/dev/null || { echo "Установите GitHub CLI: https://cli.github.com"; exit 1; }
gh auth status >/dev/null 2>&1 || gh auth login
LOGIN=$(gh api user -q .login); ID=$(gh api user -q .id)
NOREPLY="${ID}+${LOGIN}@users.noreply.github.com"

# 1) личная почта не попадёт в публичную историю: заменяем на служебный адрес GitHub
FILTER_BRANCH_SQUELCH_WARNING=1 git filter-branch -f --env-filter "
  export GIT_AUTHOR_EMAIL='${NOREPLY}'; export GIT_COMMITTER_EMAIL='${NOREPLY}'" -- --all
rm -rf .git/refs/original
git config user.email "${NOREPLY}"

# 2) ссылка «Открыть в Colab» с вашим логином
sed -i.bak "s#__GH_LOGIN__#${LOGIN}#g; s#__GH_REPO__#${REPO}#g" README.md && rm -f README.md.bak
git add README.md && git commit -qm "README: ссылки на репозиторий" || true

# 3) публичный репозиторий
gh repo create "${REPO}" --public --source=. --remote=origin --push \
  --description "Концепция пространственного развития Республики Алтай — команда «Приморск», ИДУ ИТМО"
gh repo edit "${LOGIN}/${REPO}" --enable-issues --enable-wiki=false

# 4) метки и задачи
for L in "роль:глава" "роль:расселение" "роль:экономика" "роль:транспорт" "роль:природа" "роль:жильё-жкх" "роль:наследие" "совместно"; do
  gh label create "$L" --repo "${LOGIN}/${REPO}" --force >/dev/null
done
python3 - "$LOGIN/$REPO" <<'PY'
import json, subprocess, sys
repo = sys.argv[1]
for t in json.load(open('.github/tasks/index.json')):
    subprocess.run(['gh', 'issue', 'create', '--repo', repo, '--title', t['title'],
                    '--label', t['label'], '--body-file', f".github/tasks/{t['file']}"], check=True)
PY
echo "Готово: https://github.com/${LOGIN}/${REPO}"
echo "Добавить коллег в соавторы: gh api -X PUT repos/${LOGIN}/${REPO}/collaborators/ЛОГИН_КОЛЛЕГИ"
