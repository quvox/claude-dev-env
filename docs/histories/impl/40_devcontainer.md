# 変更履歴: impl/40_devcontainer.md

> 対応文書: `docs/impl/40_devcontainer.md`（対応コード: `.devcontainer/Dockerfile.claude` ほか）

## 2026-07-06
- base ステージに **GitHub CLI（`gh`）** を追加。GitHub 公式 APT リポジトリ（`cli.github.com`、keyring は `/etc/apt/keyrings/githubcli-archive-keyring.gpg`、`arch=$(dpkg --print-architecture)` で amd64/arm64 両対応）を Docker CLI 導入ブロックに続けて追加し `gh` を導入。冒頭のツール一覧コメントにも `gh` を追記。
- 認証は CLI 側（`claude-dev` / `claude-dev-mac`）でホストの `~/.config/gh` を RO マウントして共有する（[10_cli.md](../../impl/10_cli.md) / [11_cli-mac.md](../../impl/11_cli-mac.md)）。
