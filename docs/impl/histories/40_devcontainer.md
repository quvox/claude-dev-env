# 変更履歴: 40_devcontainer.md

> 対応文書: `docs/impl/40_devcontainer.md`

## 2026-06-08
- 新規作成。`Dockerfile.claude`（base/vnc 2 ステージ）、`Dockerfile.docker-proxy`、`.devcontainer/tmux.conf`、`.zshrc` のビルド仕様を記述。zrt-tools 削除後の最終状態（zrt-tools の COPY/build ブロックなし）を反映。
- vnc ステージに computer-use MCP（`rmcp-xdotool` を `cargo install` で `/usr/local/bin` に配置、ビルド失敗は非致命的）を追加した旨を反映。デスクトップ操作（方式 C）向け。
- 上記 `cargo install` の `su` 配下で `$HOME`/PATH が解決されず `cargo: command not found` になっていたため、`HOME`/`CARGO_HOME`/`PATH` を `${USER_HOME}` 絶対パスで明示する形に修正（実ビルドで `rmcp-xdotool v0.2.0` のインストール成功を確認）。
