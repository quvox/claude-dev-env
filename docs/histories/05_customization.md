# 変更履歴: 05_customization.md

> 対応文書: `docs/05_customization.md`（旧 `docs/customization.md`）

## 2026-06-08
- `docs/customization.md` → `docs/05_customization.md` にリネーム（番号付け整理）。
- 冒頭に「この文書の役割」を追記。
- 完全性確認に伴う実装整合修正:
  - Claude Code のインストーラを実装に一致させた（`curl -fsSL https://claude.ai/install.sh | sh` → `| bash`）。
  - 再ビルド手順の `make build-claude` の説明を実装に一致させた（ベースイメージのみ、VNC は `make build-claude-vnc`）。
- 「Linux デスクトップの操作」セクションを追加。方式 A（`xdotool`/`scrot` でコンテナ内デスクトップを直接操作、追加導入不要）と方式 C（KVM VM のデスクトップを computer-use MCP〔`rmcp-xdotool`〕+ `scrot` で操作）の手順・有効化方法・使い分けを記載。
