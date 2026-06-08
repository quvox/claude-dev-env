# 変更履歴: 05_customization.md

> 対応文書: `docs/05_customization.md`（旧 `docs/customization.md`）

## 2026-06-08
- `docs/customization.md` → `docs/05_customization.md` にリネーム（番号付け整理）。
- 冒頭に「この文書の役割」を追記。
- 完全性確認に伴う実装整合修正:
  - Claude Code のインストーラを実装に一致させた（`curl -fsSL https://claude.ai/install.sh | sh` → `| bash`）。
  - 再ビルド手順の `make build-claude` の説明を実装に一致させた（ベースイメージのみ、VNC は `make build-claude-vnc`）。
