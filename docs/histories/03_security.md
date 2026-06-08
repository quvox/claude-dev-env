# 変更履歴: 03_security.md

> 対応文書: `docs/03_security.md`（旧 `docs/security.md`）

## 2026-06-08
- `docs/security.md` → `docs/03_security.md` にリネーム（番号付け整理）。
- 冒頭に「この文書の役割」を追記。
- 完全性確認に伴う実装整合修正:
  - Docker Socket Proxy のエンドポイントポリシーを実装に一致させた。`/containers/{id}/attach` は「明示的に拒否」ではなく接続ハイジャックによる中継（許可）であると訂正。全面拒否は `/swarm`・`/plugins`・`/configs`・`/secrets` のパス前方一致のみと明記し、privileged exec の拒否も追記。
  - 認証情報の保護（§2）の図を実装に一致させた。`start` 時の認証ファイルコピーは claude-dev CLI 側、entrypoint は symlink 化・パーミッション調整・書き戻しを担当、と修正。
- 「KVM デバイスの扱いと特権の非対称性」セクションを追加。デバイス渡しの条件・用途・proxy の Devices 拒否との非対称性・リスク評価を記載。
