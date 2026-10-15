#!/bin/bash
# 从本仓库把 skill 还原到本地（会覆盖本地同名 skill，本地多余 skill 会被删除）
set -euo pipefail
cd "$(dirname "$0")"

EXCLUDES=(--exclude='.git' --exclude='__pycache__' --exclude='.DS_Store')

mkdir -p "$HOME/.agents/skills" "$HOME/.kimi-code/skills"
rsync -a --delete "${EXCLUDES[@]}" .agents/skills/    "$HOME/.agents/skills/"
rsync -a --delete "${EXCLUDES[@]}" .kimi-code/skills/ "$HOME/.kimi-code/skills/"

echo "已还原到 ~/.agents/skills 和 ~/.kimi-code/skills"
