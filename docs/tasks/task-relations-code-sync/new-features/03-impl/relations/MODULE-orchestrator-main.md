---
target: docs/03-impl/relations/MODULE-orchestrator-main.md
change: replace
sections:
  - "## 処理の流れ"
  - "## 呼び出され方"
  - "## 戻り値・副作用"
deletes: []
reason: --workspace を必須かつ git ルートと書くが既定値があり検証も無い(docs/issues/032 #7)。手順の順序と --fresh 限定の掃除・最小 plan の保存が実態と違う(同 #8)。判定結果の出力先が標準出力である(同 #18)
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
tests: orchestrator/term_test.go::TestTerminalConfirm_NonTTYContinue
updated: 2026-08-05
summary: フラグを解釈し実行環境を組み立てて制御ループを起動する
---

<!-- 変更指示。反映後の最終形を書く。version / verified は持たない。
     tests を「なし(未実装)」から実名へ改めた: orchestrator/term_test.go::TestTerminalConfirm_NonTTYContinue は
     main.go:194 の terminalConfirm を検証しており、MODULE-orchestrator-term の tests に入っていた
     (D0-scope-06 の委任内。038 #29 と同じ性質の付け替え)。 -->

## 処理の流れ

1. フラグを解析する(`orchestrator/main.go:24`〜`:30`): `--workspace`(**既定値は
   `defaultWorkspace()` の戻り値**なので指定は任意)、`--instructions`、`--fresh`、
   `--start-executing`、`--print-main-session`。位置引数の並びを空白で連結したものが `<goal>`。
2. `--print-main-session` ならセッション名だけを標準出力へ出して終了する(`:35`〜`:38`。
   CLI の生存判定に使われる)。
3. `run(...)` の先頭で `--workspace` を `filepath.Abs` で絶対化する(`:55`〜`:57`。
   相対だと worktree パスが二重ネストして `git worktree add` が exit 128 になる)。
   **git リポジトリのルートかどうかは検証しない**(リポジトリでなければ後段の
   `git worktree add` が失敗して初めて分かる)。
4. **`MODULE-orchestrator-state` の `NewStore` で状態ストアを開く**(`:58`)。
   **設定の読み込みより先である。**
5. `MODULE-orchestrator-config` で設定を読み込む(組込既定 → `~/.config/claude-dev.yaml` の
   `orchestrator:` → `<workspace>/.orchestrator/config.yaml` の順にマージ)。
6. **`--fresh` を指定したときだけ** `MODULE-orchestrator-worktree` の `CleanOrchWorktrees` で
   前回の残骸を掃除し、`ArchiveRun` で現 run を `history/` へ退避する(`:80`〜`:87`)。
   **通常の起動と再開では掃除も退避も行わない。**
7. **再開/新規の判定**: `state.json` / `plan.json` を読み、`MODULE-orchestrator-plan` の `AllDone` で
   完了状況を見る。未完了 plan が残る(`AllDone == false`)ならその run を継続し、`plan.Ready` なら
   executing、未 ready なら brainstorming で始める。`AllDone == true` または plan 不在なら新規開始。
   `--start-executing` と ready な seed plan があれば executing から直接始める(検証専用。
   このときは退避しない)。
8. **`<goal>` が非空で `plan.json` が無いときだけ、最小の `Plan{Goal: <goal>, Ready: false}` を
   保存する**(`:133`〜`:137`)。ブレインストーミングの出発点を与えるためで、
   **対話側がこの `plan.json` を上書きしてよい**。
9. `MODULE-orchestrator-session` の `NewSessionManager` でセッション管理を作り、
   `MODULE-orchestrator-slack` の `NewSlackNotifier` で通知先を用意する(未設定なら no-op)。
10. `MODULE-orchestrator-controller` の `newRunID` で run ID を採番し、`Controller.Run` を起動する。
11. SIGINT / SIGTERM ハンドラを張り、経路によらず `defer ttyRestoreSane()`
    (`MODULE-orchestrator-term`)で端末をカノニカルモードへ戻す。

## 呼び出され方

- 契機: コンテナ内で `claude-orchestrator --workspace /workspace [--fresh] ["<goal>"]` が実行されたとき
  (`MODULE-cli-orchestrate` が tmux ウィンドウの中で起動する)。
- 前提条件: コンテナ内で tmux・`claude` CLI・git が使えること。
- 引数:

| 引数 | 型 | 必須 | 制約 |
|---|---|---|---|
| `--workspace` | パス | **任意**(既定は `defaultWorkspace()`) | `filepath.Abs` で絶対化される。**git リポジトリのルートであることは検証しない**(リポジトリでなければ後段の `git worktree add` が失敗する) |
| `--fresh` | フラグ | 任意 | 現 run を `history/` へ退避して新規開始 |
| `--start-executing` | フラグ | 任意 | ready な seed plan があれば executing から開始(検証専用) |
| `--instructions` | パス | 任意 | 指示テンプレートの置き場所を上書きする |
| `--print-main-session` | フラグ | 任意 | メインセッション名だけを出力して終了する |
| `<goal>` | 文字列 | 任意 | 位置引数。ブレインストーミングの初期ゴール |

- 認可: コンテナ内のユーザ。

## 戻り値・副作用

| 種別 | 内容 |
|---|---|
| 戻り値 | プロセス終了コード。中断(`errSuspended`)を含む正常系は 0 |
| 永続化 | `/workspace/.orchestrator/` 配下(`state.json`・`plan.json`・`history/<run_id>/`)。実体の書き込みは state 側が行う。**この機能自身が書くのは1件だけ**: `<goal>` が非空で plan が無いときの最小 `Plan`(`main.go:133`〜`:137`) |
| 発火するイベント | なし |
| ログ | **起動時の判定結果はすべて標準出力**(`fmt.Println` / `fmt.Printf` の7箇所。`main.go:36`・`:83`・`:94`・`:105`・`:117`・`:122`・`:127`)。**`os.Stderr` への書き込みは 0 件**である。致命的エラーだけは `log.Fatalf`(`:45`)経由で標準エラーへ出る。`--print-main-session` のときは標準出力へセッション名のみ |
