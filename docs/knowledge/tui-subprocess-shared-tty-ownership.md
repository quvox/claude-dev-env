---
title: 全画面 TUI を共有 TTY で起動したら端末モードは自前で所有・復元する
summary: 対話 claude 等の全画面 TUI は終了しても TTY を raw のまま残す。親コントローラが stty で復元を所有し、キー入力は VMIN/VTIME で非ブロック読みする
---

## 状況

`claude-dev orchestrate` の壁打ち（全画面 TUI の対話 `claude`）を `/exit` した後、worker が全く
進まず、ダッシュボードのキー入力 `d`/`q`/`p` も無反応になる報告があった。pty 上の実機 `claude`
で確認すると、対話 claude は共有 TTY を非カノニカル（raw, `ICANON=False ECHO=False`）に切り替え、
**終了時もカノニカルへ戻さない**。同じ TTY を使う親コントローラの行バッファ読み取りが破綻していた。

- raw モードでは Enter が `\n`(0x0A) でなく `\r`(0x0D)。`ReadString('\n')` は `\n` を待って永久ブロック。
- これが「キー無反応」と「確認入力を受け付けられず executing へ遷移できず worker 不起動」の単一原因。

## 判断

端末モードを子（claude）任せにせず、**コントローラが自前で所有**する方式に変更した。外部 Go
モジュールを足さず `stty` 呼び出しのみで実装:

- 対話 claude 終了直後に `ttyRestoreSane()` でカノニカルへ復元。`main.go` に `defer ttyRestoreSane()`
  を置きシグナル経路も含めて最終復元。
- ダッシュボードのキー読みは `rawKeyMode()`（`-icanon -echo min 0 time 1`）で自前設定し 1 バイト読み。
  `VMIN=0/VTIME=1` により無入力時に約 0.1 秒ごと `(0, io.EOF)` が返り、`ctx` キャンセルを取りこぼさず
  goroutine も残さない。`isig` は無効化しない（Ctrl-C → シグナルハンドラ → state flush を維持）。
- `stty` は固定引数のみ・状態遷移時のみ呼ぶ（毎ティックではない）。ユーザ入力を引数に渡さない
  （コマンドインジェクションなし）。

## 一般化した教訓（今後どう活かすか）

- **共有 TTY 上で全画面 TUI の子プロセスを起動する設計では、子が端末状態を元に戻す保証は無い**と
  前提する。親が「起動前の状態を覚え、子の終了後・シグナル経路・`defer` で必ず復元」する責任を持つ。
- 復元後にブロッキング行読み（`ReadString('\n')`）を使うと raw 残留や `\r` 送出で永久ブロックし得る。
  対話 UI のキー入力は `VMIN=0/VTIME` の非ブロック 1 バイト読みにすると、Enter 不要の即時反応と
  `ctx` キャンセル検知（goroutine リーク無し）を同時に満たせる。
- stdlib + `stty` で足りる端末制御に外部依存を足さない（依存ゼロは Dockerfile の `go.sum` 不要にも波及）。
