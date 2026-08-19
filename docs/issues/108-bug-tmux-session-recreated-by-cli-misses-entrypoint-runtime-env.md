---
id: 108-bug-tmux-session-recreated-by-cli-misses-entrypoint-runtime-env
type: bug
severity: 中
origin_layer: 02
found: 2026-08-19
found_in: /doc-check(02⇄03比較)
related: FR-env-07-13, FR-env-14-11, CTR-cli-container, MODULE-cli-start, MODULE-entrypoint-claude, AC-03
closes_when: 稼働中コンテナで tmux セッションが失われた状態から `claude-dev start` が作り直した tmux の窓で、VM モードなら `DOCKER_HOST` がゲスト VM(`tcp://127.0.0.1:2375`)を指し、macOS 経路なら `SSH_AUTH_SOCK` が値を持つこと
pattern: なし
pattern_survey: なし
summary: ホスト CLI が作り直す tmux セッションは entrypoint が実行時に export した値(VM の DOCKER_HOST / macOS の SSH_AUTH_SOCK)を引き継がない
---

# 108 CLI が作り直した tmux の窓に entrypoint の実行時の値が届かない

## 事象

tmux サーバを作る経路は2つある。

1. コンテナ初回起動時に entrypoint が起こす経路(`scripts/entrypoint-claude.sh:791`。
   `su "$USERNAME" -s /bin/zsh -c "… tmux … new-session -d -s main …"`)。
2. **稼働中のコンテナに `main` セッションが無いときに、ホスト CLI が作り直す経路**
   (`claude-dev:1465` / `claude-dev-mac:1542`。
   `docker exec -u "$CUSER" "$NAME" tmux new-session -d -s main`)。

経路2 の `docker exec` が引き継ぐのは**コンテナ設定の env**(`docker run -e` とイメージの `ENV`)
だけで、**entrypoint が実行時に自分の環境へ `export` した値は引き継がない**。該当するのは2つ:

- **VM モードの `DOCKER_HOST`**(`scripts/entrypoint-claude.sh:492` が
  `tcp://127.0.0.1:2375` を export する)。経路2 で作った窓は中継先
  (`tcp://claude-dev-docker-proxy:2375`)のままになる。
- **macOS 経路の `SSH_AUTH_SOCK`**(同 `:111`。macOS では CLI が `-e` を付けず、
  entrypoint が socat でソケットを作ってから export する)。経路2 で作った窓には値が無い。

再現手順:

1. VM モード(または macOS)でコンテナを起動し、tmux にアタッチできることを確認する。
2. コンテナは動かしたまま `docker exec <name> tmux kill-server` で tmux サーバだけを落とす。
3. `claude-dev start` を実行する(経路2 に入る)。
4. 立ち上がった窓で `printenv DOCKER_HOST`(VM モード)/ `printenv SSH_AUTH_SOCK`(macOS)を見る。
   → **VM の値でない / 空である。**

## 影響

VM モードでは、作り直した窓からの `docker` がゲスト VM ではなく docker-proxy を相手にする。
`CTR-cli-container` が「VM モードでは entrypoint がゲスト VM 側の値へ上書きする」と
**1つの値しか認めていない**のに、窓によって2つの値が同居する。
macOS では、作り直した窓から SSH agent が使えず、git over SSH が鍵を見つけられない。

severity の根拠: **中**。仕様どおりに動く経路(初回起動)は正しく、`AC-03` も `AC-08` も
この経路で不合格にはならない(コンテナ設定の env はそのまま届くため、予約名も env ファイルの組も
窓の中で見える)。壊れるのは entrypoint が実行時に決めた2つの値だけで、コンテナを作り直せば揃う。

## 原因の見当

`docker exec` はコンテナ作成時の env を使う。PID 1 がその後に `export` した値は反映されない
(推測ではなく docker の仕様)。`task-fix-tmux-server-drops-reserved-env` が
`CTR-cli-container`「渡す環境変数」へ足す到達の義務は、**受け側を「entrypoint」と名指している**ため、
ホスト CLI が作る経路2 をそのまま覆っていない。

## 正はどちらか

| 観点 | 実装(03)はどう言っているか | 要件・設計(00〜02)はどう言っているか | 判定 |
|---|---|---|---|
| 誰が到達を保証するか | `MODULE-entrypoint-claude` 手順20 だけが引き継ぎを担う。`MODULE-cli-start` の再接続経路は tmux セッションの作り直しを書くだけで、環境について何も言わない | `FR-env-07-13` は「起動経路を問わない」と書き、`CTR-cli-container` は「受け側(entrypoint)は…引き継ぐようにしなければならない」と受け側を entrypoint に限定している | **要件・設計が正**(条項は経路を問わないと言っているのに、契約の義務が entrypoint だけに掛かっている。02 起点) |

## 対処案

| 案 | 内容 | 影響範囲の見込み |
|---|---|---|
| A | `CTR-cli-container` の義務の主語を「コンテナ内でプロセスの木を新しく起こす側」に広げ、`MODULE-cli-start` の再接続経路が `docker exec -e` で VM の `DOCKER_HOST` と `SSH_AUTH_SOCK` を渡す | 02 契約1節 + `MODULE-cli-start` + `claude-dev` / `claude-dev-mac` 各1行 |
| B | 経路2 をやめ、`main` セッションが無いときはコンテナ内の1本のスクリプトへ委ね、entrypoint と同じ形で起こす | 経路が1本になるが、entrypoint の環境は既に失われているので値の出どころを別に用意する必要がある |
| C | entrypoint が VM の値と `SSH_AUTH_SOCK` をコンテナ内のファイル(`/etc/claude-dev/vm.env` は既に在る)へ書き、経路2 がそれを読んでから `tmux` を起こす | `claude-dev` / `claude-dev-mac` 各1行と、読む先の取り決めを 02 に1行 |

**どの案を採るかは決めない。**

## 経緯

- 2026-08-19 `task-fix-tmux-server-drops-reserved-env` のフェーズ2 `/doc-check`(独立レビュー Codex
  の指摘 L-03 を裁定)で検出。同タスクは初回起動の経路(経路1)を直したが、経路2 は範囲外である。
  同タスクへ畳み込むかどうかは人間の裁定を要する(畳み込まないなら本 issue のまま残す)。
