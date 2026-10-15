#!/bin/bash
# 把本地 skill 同步到本仓库并推送到 GitHub（云端与本地保持一致的镜像）
set -euo pipefail
cd "$(dirname "$0")"

EXCLUDES=(--exclude='.git' --exclude='__pycache__' --exclude='.DS_Store')

rsync -a --delete "${EXCLUDES[@]}" "$HOME/.agents/skills/"    .agents/skills/
rsync -a --delete "${EXCLUDES[@]}" "$HOME/.kimi-code/skills/" .kimi-code/skills/

git add -A
if git diff --cached --quiet; then
  echo "没有变化，云端已是最新"
  exit 0
fi
git commit -m "sync skills $(date '+%Y-%m-%d %H:%M:%S')"
GIT_SSH_COMMAND="ssh -i ~/.ssh/id_ed25519_xhs -o IdentitiesOnly=yes" git push origin HEAD
echo "已推送到 GitHub"
