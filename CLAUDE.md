# CLAUDE.md - コンテナ内開発環境

## 環境情報

- Docker コンテナ内で実行中
- `--dangerously-skip-permissions` 有効（コンテナ隔離が安全境界）

## 注意事項

- Docker ソケットはホストからマウント。docker / docker compose コマンドが利用可能
- git でコミットする前にファイルの状態を確認すること

## プロジェクト固有の指示

<!-- claude-dev-auto-start -->

## Web アプリの動作確認（重要）

- **ヘッドレスブラウザを直接起動しないこと**（`chromium.launch()` 等は禁止）
- 別コンテナ `claude-dev-chrome` で Google Chrome が起動している。ユーザーは noVNC 経由でブラウザ画面をリアルタイムに確認できる
- Chrome DevTools MCP が設定済みで、MCP ツール経由で noVNC の Chrome を直接操作できる

### 動作確認の手順

1. 開発サーバーを起動する（`0.0.0.0` にバインドすること）
2. MCP ツールで Chrome を操作する（ページ遷移、クリック、入力、スクリーンショット等）
3. ユーザーは noVNC 画面で操作をリアルタイムに確認できる

### 利用可能な主要 MCP ツール

- `navigate_page` — URL に遷移する
- `take_screenshot` — スクリーンショットを撮る
- `click` — 要素をクリックする
- `fill` — 入力欄にテキストを入力する
- `fill_form` — 複数のフォーム要素を一括入力する
- `press_key` — キーボード操作を送信する
- `evaluate_script` — JavaScript を実行する
- `list_console_messages` — コンソール出力を取得する
- `list_network_requests` — ネットワークリクエストを確認する
- `take_snapshot` — DOM スナップショットを取得する

### 注意事項
- URL には `localhost` ではなく**コンテナ名**を使うこと（例: `http://claude-dev-env:3000`）
- 開発サーバーは `0.0.0.0` にバインドする（`--host 0.0.0.0` 等）

## Docker ネットワーク（重要）

- このシェルは Docker コンテナ `claude-dev-env` 内で動作している
- `localhost` / `127.0.0.1` では他のコンテナにアクセスできない。必ず**コンテナ名**を使うこと
  - 例: `curl http://localhost:8000` → `curl http://claude-dev-env:8000`
- 自コンテナ内のサーバーへのアクセスは `localhost` で可
- `docker ps` でコンテナ名を確認できる
- 全コンテナは Docker ネットワーク `claude-dev-net` に接続されている

<!-- claude-dev-auto-end -->
