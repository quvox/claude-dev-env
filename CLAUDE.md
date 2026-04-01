# CLAUDE.md - コンテナ内開発環境

## 環境情報

- Docker コンテナ内で実行中
- `--dangerously-skip-permissions` 有効（コンテナ隔離が安全境界）

## 注意事項

- Docker Socket Proxy 経由で docker / docker compose コマンドが利用可能（生ソケットは非マウント）
- git でコミットする前にファイルの状態を確認すること
- 必ず公式の最新情報、最新仕様を調べて、それを適用すること

## プロジェクト固有の指示

<!-- claude-dev-auto-start -->

## 注意事項

- 必ず公式の最新情報、最新仕様を調べて、それを適用すること

## Web アプリの動作確認（重要）

- コンテナ内で Google Chrome が動作している。ユーザーは noVNC 経由でブラウザ画面をリアルタイムに確認できる
- Claude Code の組み込みブラウザツール（computer use）で Chrome を直接操作すること
- **ヘッドレスブラウザを別途起動しないこと**（`chromium.launch()` 等は禁止）

### 動作確認の手順

1. 開発サーバーを起動する（`0.0.0.0` にバインドすること）
2. 組み込みブラウザツールで Chrome を操作する（ページ遷移、クリック、入力、スクリーンショット等）
3. ユーザーは noVNC 画面で操作をリアルタイムに確認できる

### 注意事項
- 開発サーバーは `0.0.0.0` にバインドする（`--host 0.0.0.0` 等）
- コンテナ内の Chrome からは `localhost` で開発サーバーにアクセスできる

## Docker ネットワーク（重要）

- このシェルは Docker コンテナ `claude-dev-env` 内で動作している
- `localhost` / `127.0.0.1` では他のコンテナにアクセスできない。必ず**コンテナ名**を使うこと
  - 例: `curl http://localhost:8000` → `curl http://claude-dev-env:8000`
- 自コンテナ内のサーバーへのアクセスは `localhost` で可
- `docker ps` でコンテナ名を確認できる
- 全コンテナは Docker ネットワーク `claude-dev-net` に接続されている

<!-- claude-dev-auto-end -->
