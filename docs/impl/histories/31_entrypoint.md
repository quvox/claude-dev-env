# 変更履歴: 31_entrypoint.md

> 対応文書: `docs/impl/31_entrypoint.md`

## 2026-06-08
- 新規作成。`scripts/entrypoint-claude.sh` の前提環境変数と処理シーケンス（UID/GID 追従・認証共有・設定マージ・FW・CLAUDE.md 追記・MCP 設定・VNC/Chrome 起動・tmux 開始）を記述。
- `COMPOSE_PROJECT_NAME` の一意化処理を追加（処理シーケンスに新ステップ 6 を挿入、後続を繰り下げ）。複数プロジェクトを同時起動した際に `docker compose` の既定プロジェクト名が全コンテナで `workspace` になり、コンテナ名・ネットワーク名が衝突する問題を防ぐため、コンテナのホスト名を compose 互換名へ正規化して `COMPOSE_PROJECT_NAME` を全シェルに設定する仕様を反映。注意点にも追記。
