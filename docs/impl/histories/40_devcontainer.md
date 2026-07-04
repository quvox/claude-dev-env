# 変更履歴: 40_devcontainer.md

> 対応文書: `docs/impl/40_devcontainer.md`

## 2026-06-08
- 新規作成。`Dockerfile.claude`（base/vnc 2 ステージ）、`Dockerfile.docker-proxy`、`.devcontainer/tmux.conf`、`.zshrc` のビルド仕様を記述。zrt-tools 削除後の最終状態（zrt-tools の COPY/build ブロックなし）を反映。
- vnc ステージに computer-use MCP（`rmcp-xdotool` を `cargo install` で `/usr/local/bin` に配置、ビルド失敗は非致命的）を追加した旨を反映。デスクトップ操作（方式 C）向け。
- 上記 `cargo install` の `su` 配下で `$HOME`/PATH が解決されず `cargo: command not found` になっていたため、`HOME`/`CARGO_HOME`/`PATH` を `${USER_HOME}` 絶対パスで明示する形に修正（実ビルドで `rmcp-xdotool v0.2.0` のインストール成功を確認）。

## 2026-06-28
- AI オーケストレーター実装に伴い、`base` の前に Go ビルドステージ `orch-builder`（`FROM golang:1.24-alpine`）を追加した旨を追記（`orchestrator/` を stdlib のみでビルド、`go.sum` 不要）。`base` 内で `claude-orchestrator` バイナリと `orchestrator/instructions/` を COPY する旨も追記。詳細は 60_orchestrator.md。

## 2026-07-01（pyenv 追加）
- Dockerfile.claude に pyenv を追加。apt に CPython ソースビルド依存（libssl-dev/zlib1g-dev/libbz2-dev/libreadline-dev/libsqlite3-dev/libncursesw5-dev/tk-dev/libxml2-dev/libxmlsec1-dev/libffi-dev/liblzma-dev）を追加（実行時の追加バージョンビルド用に保持）。
- 言語ランタイム節（USER 権限）で `~/.pyenv` に git clone、ARG `PYTHON_VERSION`（既定 3.13）の最新パッチを `pyenv latest -k` で解決してソースビルドし `pyenv global` に設定。C 拡張ビルドはベストエフォート。
- システム rc（/etc/zsh/zshrc・/etc/bash.bashrc）の PATH ブロックに pyenv 初期化（PYENV_ROOT・bin を PATH・`pyenv init -`）を追加。ルート `.zshrc`（~/.zshrc.default）にも二重初期化ガード付きで pyenv 初期化を追加（利用者要望）。

## 2026-07-04（vm-healthd.sh を COPY）
- `Dockerfile.claude` に `scripts/vm-healthd.sh` を `/usr/local/bin` へ COPY＋実行権付与を追加（VM モードの資源監視常駐。80 §7.2）。あわせて本文の VM スクリプト COPY 記述に vm-portsync.sh/vm-healthd.sh を明記。

## 2026-07-04（DooD ポート転送 dood-portsync 追加）
- Dockerfile.claude に scripts/dood-portsync.sh の COPY＋実行権付与を追加（socat は既存）。
