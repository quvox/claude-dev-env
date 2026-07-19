---
id: portsync
layer: impl
title: portsync 実装説明書
version: 1.0.0
updated: 2026-07-18
verified:
  at: 2026-07-19
  version: 1.0.0
  against:
    - doc: docs/02-design/system.md
      version: 1.1
summary: >
  DooD モードでホスト公開されたコンテナポートを claude コンテナの 127.0.0.1 へ届かせる
  実行時ネットワークヘルパ。dood-portsync.sh が docker ps で 0.0.0.0:PORT を検出し、
  socat で 127.0.0.1:PORT → デフォルトGW(=ホスト):PORT を張る。entrypoint が常駐起動する。
keywords: [DooD, portsync, socat, ポートフォワード, 127.0.0.1, デフォルトゲートウェイ, entrypoint]
depends_on: []
source:
  - docs/02-design/system.md
---

# 実装説明書:portsync

## 概要

DooD（Docker outside of Docker）モードでは、claude コンテナ内から起動したコンテナはホストの
Docker デーモン（socket proxy 経由）で動き、公開ポートはホストの `0.0.0.0:PORT` に出る。claude
コンテナは別 network namespace のため、コンテナ内テスト等が叩く `127.0.0.1:PORT` にはこれが届かない。
`portsync` はこのギャップを埋める実行時ネットワークヘルパで、ホスト公開ポートを検出し、
`127.0.0.1:PORT`（コンテナ内ループバック限定）→ デフォルトゲートウェイ（＝ホスト）:PORT の socat
転送を張る。VM モードの `vm-portsync`（vm-mode）の DooD 版に相当する。上流: [全体設計](../02-design/system.md)
（`portsync` 行・要件 core/6）。

## ファイル構成

| パス | 役割 |
|---|---|
| scripts/dood-portsync.sh | DooD 実行時ポート同期ヘルパ本体。イメージビルド時に同梱され、entrypoint が起動する |

## モジュール別実装詳細

### dood-portsync.sh(scripts/dood-portsync.sh)

- **責務:** DooD モードでホスト公開ポート（`0.0.0.0:PORT`）を検出し、claude コンテナの
  `127.0.0.1:PORT` からホストへ到達させる socat 転送を張る（設計書 分割定義の `portsync`）。
- **公開インターフェース:**

```
dood-portsync.sh           # 一度だけ同期して同期件数を表示
dood-portsync.sh --loop    # 常駐し INTERVAL 秒ごとに定期同期（entrypoint が DooD 時に起動）
```

- **処理の要点:**
  - **前提チェック:** `socat` の存在と、デフォルトゲートウェイ（`ip route` の `default` 行の第3フィールド）
    が引けることを確認。いずれか欠けると `FATAL` ログを出して `exit 1`。
  - **ホスト公開ポート検出（`published_ports`）:** `docker ps --format '{{.Ports}}'`（`DOCKER_HOST`＝
    socket proxy 経由）の出力から `0.0.0.0:PORT` を `grep` で抜き、PORT を昇順一意（`sort -un`）で列挙。
  - **除外（`is_excluded`）:** claude コンテナ自身の内部サービス（noVNC `6080` / VNC `5999` /
    Chrome `9222`、既定値 `EXCLUDE`）は転送しない。ホスト側の別コンテナが同番ポートを `0.0.0.0`
    公開していると、その転送先 `127.0.0.1:PORT` が自前サービスの bind と競合する（特に VNC 起動より
    前に走ると noVNC の 6080 を先取りして websockify 起動を失敗させる）ため、明示除外で防ぐ。
  - **同期ループ（`sync_once`）:** 各ポートについて、(1) `STATE`（`/tmp/dood-portsync/forwarded`、
    1行1ポート）に記録済みならスキップ、(2) 除外対象ならスキップ、(3) `127.0.0.1:PORT` が既にローカル
    待受中（`local_listening`＝`/dev/tcp/127.0.0.1/PORT` への接続可否で判定。ローカルサーバ・noVNC・
    既存の自転送を含む）なら `STATE` に記録してスキップ、(4) いずれでもなければ
    `setsid socat "TCP-LISTEN:PORT,fork,reuseaddr,bind=127.0.0.1" "TCP:<GW>:PORT"` をバックグラウンド
    常駐起動し、`STATE` に記録してログ出力。**リスナーは `bind=127.0.0.1` 限定**でホストへは新規公開しない。
  - **起動形態(`case`):** `--loop` 指定時は `STATE` を空にしてから `sync_once`→`sleep INTERVAL` を無限
    反復（`INTERVAL` 既定 5 秒、`CLAUDE_DEV_DOOD_PORTSYNC_INTERVAL` で上書き）。引数なしは 1 回だけ同期し、
    ホスト公開ポート数を日本語で表示。
  - **状態/ログ:** `/tmp/dood-portsync/` 配下に `forwarded`（転送済み記録）と `dood-portsync.log`。
- **実装上の判断:** ローカル待受判定（`local_listening`）だけでは起動順序に依存し内部サービスの
  先取りを確実に防げないため、内部サービスポートは `EXCLUDE` による明示除外を併用する（コード内コメント準拠）。

## 設定・環境変数

| 名前 | 用途 | デフォルト | 必須 |
|---|---|---|---|
| CLAUDE_DEV_DOOD_PORTSYNC | entrypoint がこのヘルパを常駐起動するか（`0` で無効化）。既定オン | 1 | 任意 |
| CLAUDE_DEV_DOOD_PORTSYNC_INTERVAL | `--loop` 常駐時の同期間隔（秒） | 5 | 任意 |
| CLAUDE_DEV_DOOD_PORTSYNC_EXCLUDE | 転送しない内部サービスポート（空白区切り） | `6080 5999 9222` | 任意 |

- 自動起動: `entrypoint` が非 VM かつ `DOCKER_HOST` が socket proxy を指す（DooD）場合に `--loop` を
  常駐起動する。多重起動は entrypoint 側で防止する。`CLAUDE_DEV_DOOD_PORTSYNC=0` で起動を抑止する。

## エラーハンドリング実装

| 異常系 | 実装箇所 | 実際の振る舞い | 対応する要件 |
|---|---|---|---|
| socat 不在 | 前提チェック | `FATAL: socat not found` をログ出力し `exit 1` | core/6 |
| デフォルトGW を引けない | 前提チェック | `FATAL: default gateway not found` をログ出力し `exit 1` | core/6 |
| 内部サービスポートの先取り競合 | `is_excluded`/`EXCLUDE` | 6080/5999/9222 等を転送対象から除外し bind 競合を回避 | core/6, core/11 |
| 同一ポートの二重転送 | `STATE`/`local_listening` | 記録済み・ローカル待受中はスキップ | core/6 |

## テスト

シェルスクリプトのため自動テストは持たない（設計書テスト戦略「シェル系は自動テストなし＝実機確認」）。
下表は実機確認による検証内容。

| テスト(ファイル::ケース名) | レベル | 検証内容 | 対応する受け入れ基準/契約 |
|---|---|---|---|
| 実機確認::ホスト公開ポート到達 | 実機 | DooD でホスト公開されたコンテナポートへ claude コンテナ内 `127.0.0.1:PORT` から到達できる | core/6 ポートフォワード |
| 実機確認::内部サービス非干渉 | 実機 | noVNC(6080)/VNC(5999)/Chrome(9222) が転送に先取りされず正常起動する | core/6, core/11 |

実行方法: 自動テストコマンドなし。claude コンテナを DooD で起動し、ホスト公開ポートを持つコンテナを
起動したうえでコンテナ内から `127.0.0.1:PORT` へアクセスして確認する。

## 既知の制限・技術的負債

- DooD の性質上、サービスの実ポートはホストの `0.0.0.0:PORT` に公開済み（ホスト可視・別プロジェクトと
  同一ポートは衝突しうる）。ホスト非公開・ポート隔離が必要なら VM モードを使う。
- `local_listening` は起動順序に依存するため、内部サービスの先取り防止は `EXCLUDE` の明示除外に頼る。

## 運用メモ

- ログは `/tmp/dood-portsync/dood-portsync.log`、転送済みポート記録は `/tmp/dood-portsync/forwarded`。
- 転送が張られない場合は、socat 導入・デフォルトGW・`DOCKER_HOST`（socket proxy 経由）・
  `CLAUDE_DEV_DOOD_PORTSYNC` の有効/無効を確認する。
