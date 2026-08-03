---
target: docs/03-impl/relations/MODULE-orchestrator-main.md
change: add
reason: 新体系の機能間連携仕様書。旧 `03-impl/<module>.md` を機能単位へ解体し、コールグラフとコード本文から導出した(記法: .claude/directions/change-set.md 例外2)
id: MODULE-orchestrator-main
module: MOD-orchestrator
kind: tool
sync: sync
impl: orchestrator/main.go::main
callers: なし
callees: MODULE-orchestrator-config, MODULE-orchestrator-controller, MODULE-orchestrator-plan, MODULE-orchestrator-session, MODULE-orchestrator-slack, MODULE-orchestrator-state, MODULE-orchestrator-term, MODULE-orchestrator-worktree
contracts: CTR-cli-orchestrator
design: DSN-mod-01, DSN-orch-01, DSN-orch-02
requirements: FR-orch-01, FR-orch-02, FR-orch-05
tests: なし(未実装。main.go に対応する単体テストは無く、E2E-4 / E2E-5 の実機確認で代替する)
updated: 2026-08-02
summary: フラグを解釈し実行環境を組み立てて制御ループを起動する
---

# MODULE-orchestrator-main エントリポイント

## 目的

`claude-orchestrator` プロセスの起点。契約 `CTR-cli-orchestrator` が定める起動オプションを解釈し、
状態ストア・セッション管理・通知を組み立てて制御ループへ渡す(FR-orch-01)。再開/新規の判定
(FR-orch-05)もここで行う。

## 処理の流れ

1. フラグを解析する: `--workspace`(`filepath.Abs` で絶対化。相対だと worktree パスが二重ネストして
   `git worktree add` が exit 128 になる)、`--fresh`、`--start-executing`、`--instructions`、
   `--print-main-session`。
2. `--print-main-session` ならセッション名だけを出力して終了する(CLI の生存判定に使われる)。
3. `MODULE-orchestrator-config` で設定を読み込む(組込既定 → `~/.config/claude-dev.yaml` の
   `orchestrator:` → `/workspace/.orchestrator/config.yaml` の順にマージ)。
4. `MODULE-orchestrator-state` の `NewStore` で状態ストアを開き、`MODULE-orchestrator-session` の
   `NewSessionManager` でセッション管理を作る。
5. `MODULE-orchestrator-slack` の `NewSlackNotifier` で通知先を用意する(未設定なら no-op)。
6. `MODULE-orchestrator-worktree` の `CleanOrchWorktrees` で前回の残骸を掃除する。
7. **再開/新規の判定**: `state.json` / `plan.json` を読み、`MODULE-orchestrator-plan` の `AllDone` で
   完了状況を見る。未完了 plan が残る(`AllDone == false`)ならその run を継続し、`plan.Ready` なら
   executing、未 ready なら brainstorming で始める。`AllDone == true` または plan 不在なら新規開始。
   `--fresh` なら現 run を `history/` へ退避してから新規。`--start-executing` と ready な seed plan が
   あれば executing から直接始める(検証専用)。
8. `MODULE-orchestrator-controller` の `newRunID` で run ID を採番し、`Controller.Run` を起動する。
9. SIGINT / SIGTERM ハンドラを張り、経路によらず `defer ttyRestoreSane()`
   (`MODULE-orchestrator-term`)で端末をカノニカルモードへ戻す。

## 呼び出され方

- 契機: コンテナ内で `claude-orchestrator --workspace /workspace [--fresh] ["<goal>"]` が実行されたとき
  (`MODULE-cli-orchestrate` が tmux ウィンドウの中で起動する)。
- 前提条件: コンテナ内で tmux・`claude` CLI・git が使えること。
- 引数:

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| `--workspace` | パス | 必須 | 絶対化される。ここが git リポジトリのルート |
| `--fresh` | フラグ | 任意 | 現 run を `history/` へ退避して新規開始 |
| `--start-executing` | フラグ | 任意 | ready な seed plan があれば executing から開始(検証専用) |
| `--instructions` | パス | 任意 | 指示テンプレートの置き場所を上書きする |
| `--print-main-session` | フラグ | 任意 | メインセッション名だけを出力して終了する |
| `<goal>` | 文字列 | 任意 | 位置引数。ブレインストーミングの初期ゴール |

- 認可: コンテナ内のユーザ。

## 連携先と連携内容

### MODULE-orchestrator-config

- 何のために呼ぶか: `max_workers` などの実行設定を確定するため。 / 何を渡すか: workspace パス。
- 何を受け取るか: マージ済みの設定構造体。
- **失敗したときどうなるか**: 読めない設定は無視され、組込既定が使われる(起動は止めない)。

### MODULE-orchestrator-state

- 何のために呼ぶか: `/workspace/.orchestrator/` の状態ストアを開き、`plan.json` を読むため。
- 何を渡すか: workspace パス。 / 何を受け取るか: `Store` と `Plan`。
- **失敗したときどうなるか**: `plan.json` が読めなければ plan 不在として新規開始に倒れる。

### MODULE-orchestrator-plan

- 何のために呼ぶか: 読み込んだ plan が完了済みかを判定して再開/新規を決めるため。
- 何を渡すか: `Plan`。 / 何を受け取るか: `AllDone` の真偽。
- **失敗したときどうなるか**: 判定不能な状態は無いが、plan が空なら `AllDone == true` として新規開始する。

### MODULE-orchestrator-session

- 何のために呼ぶか: tmux セッション名を決め、ウィンドウ管理を制御ループへ注入するため。
- 何を渡すか: コンテナ名(`COMPOSE_PROJECT_NAME` 由来)。 / 何を受け取るか: `SessionManager` とメインセッション名。
- **失敗したときどうなるか**: tmux が無い環境では対話が `RunInteractive` の前景フォールバックになる。

### MODULE-orchestrator-slack

- 何のために呼ぶか: 節目の通知先を用意するため。 / 何を渡すか: `SLACK_BOT_TOKEN` / `SLACK_CHANNEL`。
- 何を受け取るか: `Notifier`(未設定なら `NopNotifier`)。
- **失敗したときどうなるか**: 通知は行われないが実行は続く。

### MODULE-orchestrator-worktree

- 何のために呼ぶか: 前回 run の worktree 残骸を掃除するため。 / 何を渡すか: workspace パス。
- 何を受け取るか: なし。
- **失敗したときどうなるか**: 残骸が残る。次の `git worktree add` が既存ディレクトリを再利用する。

### MODULE-orchestrator-controller

- 何のために呼ぶか: 制御ループ本体を回すため。 / 何を渡すか: `Store` / `SessionManager` / `Notifier` / 設定 / run ID。
- 何を受け取るか: 終了理由(`errSuspended` を含む)。
- **失敗したときどうなるか**: `errSuspended` は正常終了(コード 0)として扱う。それ以外のエラーはログに出して非0で終わる。

### MODULE-orchestrator-term

- 何のために呼ぶか: 終了時に端末をカノニカルモードへ戻すため。 / 何を渡すか: なし。 / 何を受け取るか: なし。
- **失敗したときどうなるか**: 端末が raw のまま残り、Enter が `\r` のままになって行バッファ読み取りが
  永久にブロックする。そのため経路によらず `defer` で必ず通す。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | プロセス終了コード。中断(`errSuspended`)を含む正常系は 0 |
| 永続化 | `/workspace/.orchestrator/` 配下(`state.json`・`plan.json`・`history/<run_id>/`)。実体の書き込みは state 側が行う |
| 発火するイベント | なし |
| ログ | 標準エラーへ起動時の判定結果。`--print-main-session` のときは標準出力へセッション名のみ |

## 異常系

| 条件 | 実際の振る舞い | 呼び出し元への影響 |
|---|---|---|
| `--workspace` が相対パス | `filepath.Abs` で絶対化する(そのままだと worktree パスが二重ネストして `git worktree add` が exit 128 になる) | なし |
| SIGINT / SIGTERM | in-flight worker へ `worker_grace_seconds` の中間コミット猶予を与えて停止し、状態を `executing` のまま保存して終了コード 0 で終わる | `claude-dev orchestrate` の再実行で resume できる |
| `plan.json` が壊れている | 読み込みに失敗し、plan 不在として新規開始へ倒れる | 前の run は `history/` に退避されない可能性がある |
| tmux が無い | 対話は `MODULE-orchestrator-mode` の `RunInteractive` による前景フォールバックになる | ダッシュボード TUI は起動しない |

## 実装上の判断

| # | 判断内容 | 根拠(委任ID) |
|---|---|---|
| 1 | 再開/新規を「plan の完了状況」で判定する(フラグや別のマーカーを増やさない) | D0-orch-02 |
| 2 | 中断を `log.Fatal` ではなく `errSuspended` の戻り値で扱い、終了コード 0 でクリーンに終える | D0-orch-02 |
| 3 | `--print-main-session` を用意し、CLI 側の生存判定がセッション名を推測しなくて済むようにする | D0-orch-01 |

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| main.go に単体テストが無い | 起動判定の回帰は E2E-4 / E2E-5 の実機確認に依存する | なし |
| `terminalConfirm` は関数値(`Confirm: terminalConfirm`)経由で渡すためコールグラフに辺が出ない | 静的解析では未到達に見える(Tier 2 の限界) | なし |
