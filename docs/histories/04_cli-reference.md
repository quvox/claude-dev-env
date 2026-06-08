# 変更履歴: 04_cli-reference.md

> 対応文書: `docs/04_cli-reference.md`（旧 `docs/cli-reference.md`）

## 2026-06-08
- `docs/cli-reference.md` → `docs/04_cli-reference.md` にリネーム（番号付け整理）。
- 冒頭に「この文書の役割」を追記し、実装仕様（`docs/impl/10_cli.md`）への参照を追加。
- 完全性確認に伴う実装整合修正:
  - Makefile ターゲット表を実装に一致させた（`build-claude` は `--target base` のみ、`build-claude-vnc` を追加）。
  - `claude-dev login` の説明を修正。`claude-dev-auth` は `~/.claude-shared/` にマウントし `~/.claude/` へコピー、`/exit` で書き戻す方式に訂正（「`~/.claude/` に直接マウントしそのまま永続化」は誤り）。
  - `claude-dev start` の「認証情報がなければエラーで停止」を削除（実装は認証が無くても起動する）。
  - `ports` / `list` の出力例を実際の出力形式に一致させた。
  - `logout` に Docker Socket Proxy コンテナの停止を追記。
- `start` の動作説明に KVM デバイス渡しを追記。その後、KVM を `--kvm` オプトインに変更したのに合わせ、`start` のオプション例と動作説明を「`--kvm` 指定時のみデバイスを渡す／既定では渡さない／稼働中コンテナへの後付け不可」に更新。
