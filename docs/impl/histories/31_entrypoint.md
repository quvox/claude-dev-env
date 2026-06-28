# 変更履歴: 31_entrypoint.md

> 対応文書: `docs/impl/31_entrypoint.md`

## 2026-06-08
- 新規作成。`scripts/entrypoint-claude.sh` の前提環境変数と処理シーケンス（UID/GID 追従・認証共有・設定マージ・FW・CLAUDE.md 追記・MCP 設定・VNC/Chrome 起動・tmux 開始）を記述。
- `COMPOSE_PROJECT_NAME` の一意化処理を追加（処理シーケンスに新ステップ 6 を挿入、後続を繰り下げ）。複数プロジェクトを同時起動した際に `docker compose` の既定プロジェクト名が全コンテナで `workspace` になり、コンテナ名・ネットワーク名が衝突する問題を防ぐため、コンテナのホスト名を compose 互換名へ正規化して `COMPOSE_PROJECT_NAME` を全シェルに設定する仕様を反映。注意点にも追記。
- MCP 設定（ステップ14）に computer-use の登録を追加。`rmcp-xdotool` バイナリが存在する場合のみ `.mcp.json` に `computer-use` エントリを定義する（`enabledMcpjsonServers` には追加せず既定無効）仕様を反映。デスクトップ操作（Linux デスクトップ制御の方式 C）向け。
- CLAUDE.md 自動追記（ステップ13）に「KVM / 仮想化（重要）」セクションを追加。`/dev/kvm` が存在する時（`--kvm` 起動時）のみ、KVM 加速の有効化方法・QEMU 起動例・GUI VM を `:99` に表示する方法・computer-use/scrot での操作・ネットワーク・ディスクイメージ配置の注意を Claude Code 向けに書き込む。マーカー範囲内のため `--kvm` の付け外しに追従する。
