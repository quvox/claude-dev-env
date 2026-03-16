# CLAUDE.md - コンテナ内開発環境

## 環境情報

- Docker コンテナ内で実行中
- `--dangerously-skip-permissions` 有効（コンテナ隔離が安全境界）

## 注意事項

- Docker ソケットへのアクセスなし。docker コマンドは使用不可
- git でコミットする前にファイルの状態を確認すること

## プロジェクト固有の指示

