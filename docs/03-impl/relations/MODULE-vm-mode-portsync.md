---
id: MODULE-vm-mode-portsync
module: MOD-vm-mode
kind: tool
sync: sync
impl: scripts/vm-portsync.sh::main#--loop, scripts/vm-portsync.sh::main
callers: なし
callees: なし
contracts: なし
design: DSN-mod-01, DSN-mod-03, DSN-arch-01
requirements: FR-env-06, FR-env-08
tests: なし(未実装。シェル実装のため自動テストランナーが無く実機確認で代替する。静的検証として `bash -n` は緑)
updated: 2026-08-02
summary: ゲストの公開ポートを QMP hostfwd_add で 127.0.0.1 へ転送する
---

# MODULE-vm-mode-portsync VM モードのポート同期

## 目的

ゲスト dockerd が公開したポートを、claude コンテナの `127.0.0.1:PORT` から叩けるようにする
(FR-env-06・FR-env-08)。DooD 版の `MODULE-portsync-dood` に対応する VM 版で、こちらは socat では
なく QEMU の hostfwd を動的に足す。

## 処理の流れ

1. `published_ports`: `docker -H tcp://127.0.0.1:2375 ps --format '{{.Ports}}'` の出力から
   `0.0.0.0:PORT` と `[::]:PORT` のポート番号を抜き、一意化する。
2. `sync_once`: QMP ソケットと pidfile が有効なとき、各公開ポートについて未追加であれば
   QMP の `human-monitor-command` 経由で HMP コマンド
   `hostfwd_add n0 tcp:127.0.0.1:PORT-:PORT` を実行する。
3. 追加済みのポートは `/run/vm/portsync.forwarded` に `<qemu_pid>:<port>` の形で記録し、
   重複追加を避ける。VM を再起動して pid が変われば記録が自然に無効になり、張り直される。
4. `--loop` 指定時は `VM_PORTSYNC_INTERVAL`(既定5秒)間隔で `sync_once` を繰り返す。

## 呼び出され方

- 契機: `MODULE-vm-mode-up` が dockerd の準備完了後に `--loop` で常駐起動する。
  利用者が `MODULE-vm-mode-cli` の `vm portsync` から一発実行することもある。
- 前提条件: QEMU が `-qmp unix:/run/vm/qmp.sock` で動いていること。
- 引数:

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| `--loop` | フラグ | 任意 | 常駐して定期同期する |
| `VM_PORTSYNC_INTERVAL` | 環境変数 | 任意 | ループ間隔の秒数(既定5) |

- 認可: コンテナ内のユーザ。

## 連携先と連携内容

連携先なし(QMP は Unix ソケット越しの制御、`docker` は外部コマンド実行)。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | 0。`--loop` は終了しない |
| 永続化 | **`/run/vm/portsync.forwarded`**(`<qemu_pid>:<port>` の記録)。QEMU の hostfwd 設定(プロセス外の状態) |
| 発火するイベント | なし |
| ログ | `${HOME}/.claude-dev-vm/logs/portsync.log` |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| ゲスト dockerd に一時的に到達できない | `set -u` のみで `-e` を付けていないためループは止まらず、次の周回で再試行する | 転送が遅れるだけ |
| QMP ソケットまたは pidfile が無い | その周回をスキップする | VM が停止しているときは何もしない |
| VM を再起動して QEMU の pid が変わった | 記録が一致しなくなり、すべての転送を張り直す | 数秒で復旧する |
| 同じポートを二重に追加しようとした | 記録済みならスキップする | なし |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | `hostfwd_add` は HMP のコマンドなので、QMP から直接ではなく `human-monitor-command` でラップして送る。接続ごとに `qmp_capabilities` のネゴシエーションを行う | D0-scope-04 |
| 2 | `set -e` を付けない(一時的な docker / QMP の失敗で常駐ループを落とさないため) | D0-scope-04 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| 転送の削除を行わない(追加のみ) | ゲスト側でコンテナを止めても hostfwd は残る(害は無いが増え続ける) | なし |
