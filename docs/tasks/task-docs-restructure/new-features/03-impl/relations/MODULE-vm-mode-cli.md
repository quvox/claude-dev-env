---
target: docs/03-impl/relations/MODULE-vm-mode-cli.md
change: add
reason: 新体系の機能間連携仕様書。旧 `03-impl/<module>.md` を機能単位へ解体し、コールグラフとコード本文から導出した(記法: .claude/directions/change-set.md 例外2)
id: MODULE-vm-mode-cli
module: MOD-vm-mode
kind: tool
sync: sync
impl: scripts/vm::main
callers: なし
callees: なし
contracts: なし
design: DSN-mod-01, DSN-mod-03, DSN-arch-01
requirements: FR-env-08, NFR-ops-01
tests: なし(未実装。シェル実装のため自動テストランナーが無く実機確認で代替する。静的検証として `bash -n` は緑)
updated: 2026-08-02
summary: VM の起動状態・health・ポート同期を操作するヘルパー
---

# MODULE-vm-mode-cli vm ヘルパーコマンド

## 目的

コンテナ内から VM を操作・観測する入口(FR-env-08・NFR-ops-01)。ゲストの状態を見る、入る、
作り直す、といった日常操作を1コマンドに束ねる。

## 処理の流れ

第1引数のサブコマンドで分岐する(省略時は `status`)。

1. `status`: QEMU プロセスの生存(pidfile + `kill -0`)、`virtiofsd` の生存(`pgrep`)、
   ゲスト dockerd の到達性(`docker -H tcp://127.0.0.1:2375 info`)を表示する。加えて health ファイルを
   読み `STATE` / `CPU` / `CEIL` と `TS` から算出した最終更新経過秒を表示する。health が無いときは
   `vm-healthd.sh --loop` の生存を見て「monitor starting」と「not running」を出し分ける。
2. `shell`: `ssh -p 2222 -i <id_vm>`(`StrictHostKeyChecking=no` 等)で `dev@127.0.0.1` に入る。
   `vm shell -- <cmd>` で単発実行もできる。
3. `restart`: `vm down` の後に `vm-up.sh` を再実行する。
4. `down`: QMP ソケットと `socat` があれば `system_powerdown` でグレースフル停止を最大15秒待ち、
   残っていれば `kill` する。`virtiofsd` は `pkill` する。
5. `rebuild`: `env VM_FRESH=1 vm-up.sh`(overlay と seed を破棄して再 provision。cloud image は残す)。
6. `portsync`: `vm-portsync.sh` を一発実行する(即時同期)。
7. `logs`: `vm-up.log` / `qemu-serial.log` / `virtiofsd.log` の末尾を tail する
   (既定100行。第2引数で行数を指定できる)。

## 呼び出され方

- 契機: 利用者がコンテナ内で `vm [status|shell|restart|down|rebuild|portsync|logs]` を実行したとき。
- 前提条件: VM モードで起動していること(`/usr/local/bin/vm` はイメージに同梱される)。
- 引数:

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| `$1` | 文字列 | 任意 | `status`(既定) / `shell` / `restart` / `down` / `rebuild` / `portsync` / `logs` |
| `$2` | 整数 | 任意 | `logs` のときの行数(既定100) |

- 認可: コンテナ内のユーザ。

## 連携先と連携内容

連携先なし(`vm-up.sh` / `vm-portsync.sh` は別プロセスとして起動するため、コールグラフの
機能間の辺には現れない)。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | サブコマンドの結果に応じた終了ステータス |
| 永続化 | `down` / `rebuild` は `/run/vm/` の制御ファイルと `${HOME}/.claude-dev-vm/` の overlay・seed に影響する。**読む資源は `${VM_HOME}/health`**(書式の持ち主は `MODULE-vm-mode-healthd`) |
| 発火するイベント | `restart` / `rebuild` が `vm-up.sh` を、`portsync` が `vm-portsync.sh` を起動する |
| ログ | 標準出力へ状態表示。`logs` はログファイルの内容 |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| QEMU が起動していない | `status` が停止として表示する。`shell` は ssh 接続に失敗する | 利用者が `vm restart` する |
| health ファイルが無い | `vm-healthd.sh --loop` の生存で「monitor starting」/「not running」を出し分ける | なし |
| `down` でグレースフル停止が15秒以内に終わらない | `kill` で強制停止する | ゲストのファイルシステムが不整合になりうる |
| QMP ソケットまたは `socat` が無い | `system_powerdown` を諦めて `kill` にフォールバックする | 同上 |
| 未知のサブコマンド | 使い方を表示する | なし |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | `down` は QMP 経由の powerdown を優先し、失敗・不在のときだけシグナル kill にフォールバックする | D0-scope-04 |
| 2 | `rebuild` は cloud image を残す(再取得に時間がかかるため)。完全リセットは CLI の `--vm-fresh` が担う | D0-scope-04 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| `logs` が tail する対象は3ファイル固定 | `portsync.log` / `vm-healthd.log` は手で見る必要がある | なし |
