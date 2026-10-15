# my_skill

我的 Kimi Code / Claude Code 等 agent 工具的 skill 备份仓库。目录结构与本地 `~` 下的路径一一对应，方便直接还原：

| 仓库内路径 | 本地路径 |
| --- | --- |
| `.agents/skills/` | `~/.agents/skills/` |
| `.kimi-code/skills/` | `~/.kimi-code/skills/` |

## 同步（本地 → 云端）

```bash
./sync.sh
```

把本地 skill 全量镜像到仓库（多余文件会删除，保证云端与本地完全一致），提交并推送到 GitHub。

## 还原（云端 → 本地）

```bash
git clone git@github.com:flyinthesky1020/my_skill.git
cd my_skill
./restore.sh
```

把仓库内容还原到 `~/.agents/skills/` 和 `~/.kimi-code/skills/`。注意：`--delete` 会删除本地同名目录下不在仓库中的文件，如需保留请先备份。

## 备注

- git 推送使用 `~/.ssh/id_ed25519_xhs` 这把 key 认证 GitHub（账号 flyinthesky1020）。
