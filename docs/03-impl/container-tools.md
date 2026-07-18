---
id: container-tools
layer: impl
title: container-tools 実装説明書
version: 1.0.0
updated: 2026-07-18
verified:
  at: 2026-07-18
  version: 1.0.0
  against:
    - doc: docs/02-design/system.md
      version: 1.0
summary: >
  コンテナ内でユーザが使う 2 つの資産の実装説明。レート制限リセット待ちユーティリティ
  wait-limit-reset.sh と、実行時に ~/.tmux.conf へマウントされる tmux 設定 tmux.conf。
keywords: [container-tools, wait-limit-reset, tmux, レート制限, prefix, ~/.tmux.conf]
depends_on: []
source:
  - docs/02-design/system.md
---

# 実装説明書:container-tools

## 概要

container-tools は「コンテナ内でユーザが直接使う資産」を束ねるモジュールである（上流:
[全体設計](../02-design/system.md) の分割定義 container-tools 行）。構成は 2 ファイル。
`scripts/wait-limit-reset.sh` は Claude のレート制限（利用上限）がリセットされる時刻まで
待機し、時刻到達時に tmux 経由で作業を再開させる補助ユーティリティ。`scripts/tmux.conf`
は CLI が起動時にコンテナ内 `~/.tmux.conf` へマウントする tmux 設定で、通常ターミナルとの
操作差を最小化しつつセッションを永続化する（core/1 tmux 体験）。どちらもユーザ操作を助ける
だけで、システムの制御フローには関与しない。

## ファイル構成

| パス | 役割 |
|---|---|
| scripts/wait-limit-reset.sh | 指定時刻（HH:MM）までスリープし、到達後に tmux ウィンドウへ再開キーを送るユーティリティ。イメージに同梱され PATH 上に配置される |
| scripts/tmux.conf | 実行時に `~/.tmux.conf` へマウントされる tmux 設定（prefix・キーバインド・ステータスバー等） |

## モジュール別実装詳細

### wait-limit-reset.sh（scripts/wait-limit-reset.sh）

- **責務:** Claude の利用上限がリセットされる時刻まで待機し、時刻到達で作業を自動再開させる
  （設計書 container-tools「レート制限リセット待ち」）。
- **公開インターフェース（CLI）:**

```
wait-limit-reset.sh HH:MM
```

- **処理の要点:**
  - 第 1 引数（`HH:MM`）が未指定なら usage とエラーメッセージを stderr に出して `exit 1`。
  - `date -d "today $time"` で当日の該当時刻を UNIX 秒（`target`）に変換する。
  - 現在時刻（`now`）が `target` 以上（＝指定時刻が既に過ぎている）なら、`date -d
    "tomorrow $time"` で翌日の同時刻へ繰り上げる。これにより「今から次に来る HH:MM」まで
    待つ挙動になる。
  - `** waiting until HH:MM` を出力後、`sleep $(( target - now ))` で残り秒数だけ待機。
  - 到達後 `FIRE!!!` を出力し、`tmux send-keys -t :1 "go on" Enter` で tmux のウィンドウ 1
    に文字列 `go on` と Enter を送信し、待機していた Claude セッションを再開させる。
- **実装上の判断:** 送信先は tmux ウィンドウ番号 `:1` 固定（tmux.conf の `base-index 1` に
  対応）。日付跨ぎは「今日→過ぎていれば明日」の単純な繰り上げのみで、秒指定やタイムゾーン
  指定は扱わない。

### tmux.conf（scripts/tmux.conf）

- **責務:** コンテナ内 tmux のキー操作・表示・永続化を定義する（core/1 tmux 体験）。CLI が
  起動時にこのファイルをコンテナ内の `~/.tmux.conf` へマウントして反映する。
- **処理の要点（主要設定）:**
  - **プレフィックスキー:** `C-_`（`Ctrl-_`）。既定の `C-b` は `unbind`、`C-_ send-prefix`
    を bind。通常ターミナルとの衝突を避ける狙い。
  - **シェル／端末:** `default-shell` / `default-command` ともに `/bin/zsh`。
    `history-limit 50000`、`default-terminal screen-256color` + truecolor override
    （`terminal-overrides ",*256col*:Tc"`）。
  - **操作性:** `mouse on`（タッチパッドスクロール可）、`escape-time 0`（ESC 遅延解消）。
  - **ウィンドウ:** `base-index 1` / `pane-base-index 1` / `renumber-windows on`。
  - **ステータスバー（最小限）:** 左にセッション名、右に時刻。status-right の先頭に
    `@vm_health` を条件表示する（`#{?#{@vm_health},...,}`）。この tmux ユーザ変数は VM モードの
    vm-healthd が資源逼迫時に set・復帰時に unset する別モジュールの資産で、非 VM モードでは
    常に未設定＝非表示。
  - **永続化:** `detach-on-destroy off`（セッション破棄時にクライアントを落とさずデタッチ）。
- **実装上の判断:** キーバインドは prefix 再定義のみで、ペイン分割等の独自バインドは追加せず
  tmux 既定の操作感を残す。

## データアクセス

（永続データストアへのアクセスなし）

## API実装詳細

（外部公開 API なし）

## 設定・環境変数

| 名前 | 用途 | デフォルト | 必須 |
|---|---|---|---|
| （なし） | wait-limit-reset.sh は引数 `HH:MM`、tmux.conf は環境変数を参照しない | — | — |

## エラーハンドリング実装

| 異常系 | 実装箇所 | 実際の振る舞い | 対応する要件 |
|---|---|---|---|
| 待機時刻の引数欠落 | wait-limit-reset.sh L3-7 | usage とエラーを stderr に出力し `exit 1` | 運用補助 |
| 指定時刻が既に経過 | wait-limit-reset.sh L15-19 | 翌日の同時刻へ繰り上げて待機継続 | 運用補助 |

## テスト

自動テストは持たない。以下の実機確認による。

| テスト(ファイル::ケース名) | レベル | 検証内容 | 対応する受け入れ基準/契約 |
|---|---|---|---|
| 実機確認::引数なし起動 | 単体 | usage 表示と `exit 1` | 運用補助 |
| 実機確認::HH:MM 指定 | 単体 | 指定時刻まで待機し、到達後 tmux ウィンドウ 1 に `go on`+Enter が送られ再開する | core/1(tmux) |
| 実機確認::tmux 起動 | 単体 | `~/.tmux.conf` マウント後、prefix が `Ctrl-_` になり、ステータスバー・シェルが設定どおり | core/1(tmux) |

実行方法: 自動テストコマンドなし。`~/.tmux.conf` 反映後に tmux を起動して確認、
`wait-limit-reset.sh HH:MM` を tmux セッション内で実行して挙動を確認する。

## 既知の制限・技術的負債

- wait-limit-reset.sh は再開先を tmux ウィンドウ `:1` 固定で送信するため、Claude が別ウィンドウ
  にある構成では再開が届かない。
- `HH:MM` の解釈はローカルタイムゾーン依存。秒・日付の明示指定はできない。

## 運用メモ

- tmux 設定は 2 種類が別モジュールに存在し、本モジュールが扱うのは `scripts/tmux.conf`
  （実行時に `~/.tmux.conf` へマウントする実セッション設定）のみ。イメージに焼き込まれる
  `.devcontainer/tmux.conf`（`/etc/tmux.conf`）は devcontainer モジュールの資産で別物。
- wait-limit-reset.sh はイメージへ同梱され PATH 上に配置される（同梱は devcontainer モジュール
  の担当）。
