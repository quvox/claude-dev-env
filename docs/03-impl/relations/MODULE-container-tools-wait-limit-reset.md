---
id: MODULE-container-tools-wait-limit-reset
module: MOD-container-tools
kind: tool
sync: sync
impl: scripts/wait-limit-reset.sh::main
callers: なし
callees: なし
contracts: なし
design: DSN-mod-01, DSN-mod-03
requirements: FR-env-01
tests: なし(未実装。シェル実装のため自動テストランナーが無く実機確認で代替する)
updated: 2026-08-05
summary: Claude のレート制限解除時刻まで待機し tmux 経由で作業を再開させる
---

# MODULE-container-tools-wait-limit-reset レート制限リセット待ち

## 目的

Claude の利用上限に当たったとき、リセット時刻まで待って自動で作業を再開させる補助道具。
**tmux セッションで作業を続ける体験(FR-env-01)を、上限で中断させないためのもの**である。
システムの制御フローには関与しない。

## 処理の流れ

1. 第1引数(`HH:MM`)が未指定なら usage とエラーメッセージを stderr に出して `exit 1`。
2. `date -d "today <HH:MM>"` で当日の該当時刻を UNIX 秒(`target`)へ変換する。
3. 現在時刻が `target` 以上(= 指定時刻を既に過ぎている)なら、`date -d "tomorrow <HH:MM>"` で
   翌日の同時刻へ繰り上げる(「今から次に来る HH:MM」まで待つ挙動になる)。
4. `** waiting until HH:MM` を出力し、`sleep $(( target - now ))` で残り秒数だけ待つ。
5. 到達したら `FIRE!!!` を出力し、`tmux send-keys -t :1 "go on" Enter` で tmux のウィンドウ1へ
   `go on` と Enter を送り、待機していた Claude セッションを再開させる。

## 呼び出され方

- 契機: コンテナ内で利用者が `wait-limit-reset.sh HH:MM` を実行したとき。
- 前提条件: tmux セッション内で実行すること。イメージに同梱され PATH 上にあること。
- 引数:

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| `$1` | 文字列 | 必須 | `HH:MM` 形式。秒・日付・タイムゾーンは指定できない |

- 認可: コンテナ内のユーザ。

## 連携先と連携内容

連携先なし(`tmux send-keys` は外部コマンド実行であり、機能間の辺には現れない)。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | 0(引数欠落時は 1) |
| 永続化 | なし。tmux ウィンドウ `:1` へキー入力を送る(プロセス外の状態を変える) |
| 発火するイベント | なし |
| ログ | 標準出力へ `** waiting until HH:MM` と `FIRE!!!` |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| 引数が無い | usage とエラーを stderr へ出して `exit 1` | 何も待たない |
| 指定時刻が既に過ぎている | 翌日の同時刻へ繰り上げて待機を続ける | 意図せず約24時間待つことがある |
| `HH:MM` として解釈できない文字列 | `date -d` が失敗し、`target` が空のまま `sleep` の算術で失敗する | 異常終了する |
| tmux ウィンドウ `:1` に Claude がいない | キーは送られるが再開しない | 気づかないまま止まる |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | 送信先を tmux ウィンドウ `:1` 固定にする(`scripts/tmux.conf` の `base-index 1` に対応) | D0-scope-02 |
| 2 | 日付跨ぎは「今日 → 過ぎていれば明日」の単純な繰り上げだけにする | D0-scope-02 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| 再開先が tmux ウィンドウ `:1` 固定 | Claude が別ウィンドウにある構成では再開が届かない | なし |
| `HH:MM` の解釈がローカルタイムゾーン依存 | 秒・日付の明示指定はできない | なし |
