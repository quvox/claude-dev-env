---
target: docs/03-impl/relations/MODULE-portsync-dood.md
change: add
reason: 新体系の機能間連携仕様書。旧 `03-impl/<module>.md` を機能単位へ解体し、コールグラフとコード本文から導出した(記法: .claude/directions/change-set.md 例外2)
id: MODULE-portsync-dood
module: MOD-portsync
kind: tool
sync: sync
impl: scripts/dood-portsync.sh::main#--loop, scripts/dood-portsync.sh::main
callers: MODULE-entrypoint-claude
callees: なし
contracts: なし
design: DSN-mod-01, DSN-mod-03, DSN-arch-01
requirements: FR-env-06, FR-env-07
tests: なし(未実装。シェル実装のため自動テストランナーが無く実機確認で代替する)
updated: 2026-08-02
summary: DooD 環境で公開ポートを検出し socat で 127.0.0.1 へ転送する
---

# MODULE-portsync-dood DooD ポート同期

## 目的

DooD(Docker outside of Docker)では、claude コンテナ内から起動したコンテナはホストの Docker
デーモンで動き、公開ポートはホストの `0.0.0.0:PORT` に出る。claude コンテナは別の network
namespace なので、コンテナ内のテストが叩く `127.0.0.1:PORT` には届かない。このギャップを埋める
のが本機能である(FR-env-06・FR-env-07)。VM モードの `MODULE-vm-mode-portsync` の DooD 版に当たる。

## 処理の流れ

1. **前提チェック**: `socat` の存在と、デフォルトゲートウェイ(`ip route` の `default` 行の
   第3フィールド)が引けることを確認する。どちらか欠けると `FATAL` をログに出して `exit 1`。
2. **公開ポート検出(`published_ports`)**: `docker ps --format '{{.Ports}}'`
   (`DOCKER_HOST` は socket proxy 経由)の出力から `0.0.0.0:PORT` を `grep` で抜き、
   PORT を `sort -un` で昇順一意に並べる。
3. **除外(`is_excluded`)**: claude コンテナ自身の内部サービス(noVNC `6080` / VNC `5999` /
   Chrome `9222`。既定の `EXCLUDE`)は転送しない。ホスト側の別コンテナが同じ番号を `0.0.0.0`
   公開していると、転送先の `127.0.0.1:PORT` が自前サービスの bind と競合するため(とくに VNC 起動
   より前に走ると noVNC の 6080 を先取りして websockify の起動を失敗させる)。
4. **同期(`sync_once`)**: 各ポートについて、(1) `STATE`(`/tmp/dood-portsync/forwarded`。1行1ポート)に
   記録済みならスキップ、(2) 除外対象ならスキップ、(3) `127.0.0.1:PORT` が既にローカルで待ち受け中
   (`local_listening` = `/dev/tcp/127.0.0.1/PORT` への接続可否で判定)なら `STATE` に記録してスキップ、
   (4) いずれでもなければ
   `setsid socat "TCP-LISTEN:PORT,fork,reuseaddr,bind=127.0.0.1" "TCP:<GW>:PORT"` を
   バックグラウンド常駐で起動し、`STATE` に記録してログへ出す。
   **リスナーは `bind=127.0.0.1` に限定**しており、ホストへ新規公開はしない。
5. **起動形態**: `--loop` 指定時は `STATE` を空にしてから `sync_once` → `sleep INTERVAL` を無限に
   繰り返す(`INTERVAL` 既定5秒。`CLAUDE_DEV_DOOD_PORTSYNC_INTERVAL` で上書き)。
   引数なしのときは1回だけ同期し、ホスト公開ポート数を日本語で表示する。

## 呼び出され方

- 契機: `MODULE-entrypoint-claude` が、非 VM かつ `DOCKER_HOST` が socket proxy を指す(DooD)場合に
  `--loop` で常駐起動する。利用者が引数なしで手動実行して1回だけ同期することもできる。
- 前提条件: `socat` がイメージに同梱されていること。`DOCKER_HOST` が docker-proxy を指すこと。
- 引数:

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| `--loop` | フラグ | 任意 | 常駐して定期同期する。省略時は1回だけ |

- 認可: コンテナ内のユーザ。

## 連携先と連携内容

連携先なし(`docker ps` は `MODULE-docker-proxy-serve` 越しの HTTP Docker API 呼び出しだが、
コールグラフの機能間の辺としては現れない)。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | 0(前提チェック失敗時は 1)。`--loop` は終了しない |
| 永続化 | **`/tmp/dood-portsync/forwarded`**(転送済みポートの記録。1行1ポート)と **`/tmp/dood-portsync/dood-portsync.log`**。socat の常駐プロセス |
| 発火するイベント | なし |
| ログ | `/tmp/dood-portsync/dood-portsync.log` |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| `socat` が無い | `FATAL: socat not found` をログへ出して `exit 1` | 転送が張られない。entrypoint は起動を続ける |
| デフォルトゲートウェイを引けない | `FATAL: default gateway not found` をログへ出して `exit 1` | 同上 |
| 内部サービスポートの先取り競合 | `EXCLUDE`(既定 `6080 5999 9222`。`CLAUDE_DEV_DOOD_PORTSYNC_EXCLUDE` で上書き)に列挙されたポートを転送対象から外す | noVNC / VNC / Chrome が正常に起動する |
| 同じポートの二重転送 | `STATE` に記録済み、またはローカル待ち受け中ならスキップする | なし |
| `CLAUDE_DEV_DOOD_PORTSYNC=0` | entrypoint が起動しない | 転送なしで動く |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | ローカル待ち受け判定(`local_listening`)だけでは起動順序に依存して内部サービスの先取りを防ぎきれないため、`EXCLUDE` による明示除外を併用する | D0-scope-02 |
| 2 | リスナーを `bind=127.0.0.1` に限定する(ホストへ新規のポートを公開しない) | D0-sec-01 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| DooD の性質上、サービスの実ポートはホストの `0.0.0.0:PORT` に公開済み | ホストから見え、別プロジェクトと同じポートは衝突しうる。ポート隔離が要るなら VM モードを使う | なし |
| `local_listening` が起動順序に依存する | 先取り防止は `EXCLUDE` の明示列挙に頼っている | なし |
