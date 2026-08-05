---
target: docs/03-impl/relations/MODULE-orchestrator-mode.md
change: replace
sections:
  - "## 処理の流れ"
  - "## 既知の制限"
deletes: []
reason: 「独立ウィンドウ方式では ResolveArgsOne を使う」と書くが製品コードからの呼び出しが無く、コントローラは IntervenePrompt と WriteLaunchScript を使う(docs/issues/038 #22)
reflected: 2026-08-05
id: MODULE-orchestrator-mode
module: MOD-orchestrator
kind: function-call
sync: sync
impl: orchestrator/mode.go::Mode.RunInteractive, orchestrator/mode.go::Mode.BrainstormingArgs, orchestrator/mode.go::Mode.ResolveArgs, orchestrator/mode.go::Mode.ResolveArgsOne, orchestrator/mode.go::Mode.IntervenePrompt, orchestrator/mode.go::Mode.WriteLaunchScript, orchestrator/mode.go::Mode.brainstormingInstr, orchestrator/mode.go::Mode.interveneInstr, orchestrator/mode.go::Mode.instructionPath, orchestrator/mode.go::readFileOr, orchestrator/mode.go::shellSingleQuote
callers: MODULE-orchestrator-controller, MODULE-orchestrator-session
callees: MODULE-orchestrator-claude-exec, MODULE-orchestrator-state, MODULE-orchestrator-state-intervention, MODULE-orchestrator-state-io, MODULE-orchestrator-term
contracts: CTR-orchestrator-prompt
design: DSN-mod-01, DSN-orch-01
requirements: FR-orch-01, FR-orch-04
tests: orchestrator/mode_test.go::TestWriteLaunchScript, orchestrator/mode_test.go::TestWriteLaunchScript_NoPromptOmitsPositional, orchestrator/mode_test.go::TestShellSingleQuote, orchestrator/policy_test.go::TestModeArgs_IncludePolicyWhenPresent
updated: 2026-08-05
summary: 対話モードの起動引数・指示テンプレート・起動スクリプトを決める
---

<!-- 変更指示。反映後の最終形を書く。version / verified は持たない。frontmatter は `updated` の日付以外変更なし
     (ResolveArgsOne は到達不能だが impl から外さない = 実在するシンボルであり CG4 を誘発しない)。 -->

## 処理の流れ

1. `instructionPath(name)` が指示テンプレート(`instructions/brainstorming.md` /
   `instructions/intervene.md`。イメージ同梱)の位置を解決し、`readFileOr` が読み込む。
   `brainstormingInstr` / `interveneInstr` がそれぞれの本文を返す。
2. `BrainstormingArgs()` がブレインストーミング用の `claude` 引数を組み立てる。
   `handoff_note.md` があれば先頭に前置し、消費後に削除する。
   返すのは **`--append-system-prompt <指示テンプレート>` だけ**(指示が空なら空スライス)。
   **model / effort はここでは付けない** — `brainstormingProfile`(opus / high)は呼び出し元が
   `ModelProfile` として `WriteLaunchScript` に渡し、そこで `--model` / `--effort` になる。
3. `ResolveArgs(ids []string)` が**未解決の介入をまとめて**解決するための引数を組み立てる。
   `MODULE-orchestrator-state-intervention` の `ReadQuestion` で各 `id` の質問文を読み、
   2件以上なら件数の前置を付けて `===== 介入 <id> =====` の区切りで連結する。
   **製品コードから呼ばれるのは `ResolveArgs` の方だけ**である(`controller.go:843` の前景
   フォールバック経路 `RunInteractive(ctx, ResolveArgs(ids)...)`)。
   `ResolveArgsOne(id string)`(`orchestrator/mode.go:191`)は**1件だけ**を対象にする版だが、
   **製品コードからの呼び出しは無い**: 独立ウィンドウ方式でコントローラが使うのは
   `IntervenePrompt(id)` と `WriteLaunchScript` の組(`controller.go:929`)であり、
   `ResolveArgsOne` はその経路に入っていない(到達不能シンボル。`docs/issues/001` と同種)。
   `ResolveArgs` / `ResolveArgsOne` はいずれも `MODULE-orchestrator-state` の
   `LoadProjectPolicy`(`ORCHESTRATOR.md`)と `VMModePreamble` を指示の先頭へ前置する。
4. `IntervenePrompt(id string)` が介入1件について **(システムプロンプト, 初回プロンプト)** の
   組を返す(初回プロンプトはその介入の `question.md`)。
5. `WriteLaunchScript(key string, prof ModelProfile, sysPrompt, prompt string)`
   (`orchestrator/mode.go:116`)が `.orchestrator/sessions/<key>.sh` に launcher を生成する。
   `prof` から `--model` / `--effort` を組み立てる。中身は VM env の source、`claude` の PATH 解決
   (`MODULE-orchestrator-claude-exec` の `claudePath`)、`SLACK_BOT_TOKEN` の除去、workspace への
   `cd`、巨大なプロンプトを `.sys` / `.prompt` サイドカーから `$(cat)` で読む形。
   **原子的に書かれるのは `.sys` / `.prompt` サイドカーだけ**(`MODULE-orchestrator-state-io` の
   `writeAtomic`。`:124` / `:127`)で、**`<key>.sh` 本体は `os.WriteFile`(0o755)で直接書く**(`:153`)。
6. `RunInteractive(ctx)` は tmux が無いときの前景フォールバック。子プロセスの終了までブロックし、
   戻ったら `MODULE-orchestrator-term` の `ttyRestoreSane` で端末を戻す。
7. `shellSingleQuote(s)` が文字列を `'` で囲み、**中の `'` を `'\''` に置換**して `/bin/sh` の
   コマンド行へ埋め込める形にする(`MODULE-orchestrator-session` も使う)。

## 既知の制限

| 制限 | 影響 | 関連 issue |
|---|---|---|
| `Mode.RunInteractive` の `cmd.Run()`(mode.go:51)が、静的解析では `Controller.Run` / `SessionManager.Run` への呼び出し候補として現れる | 実在しない候補辺が立つ。コードを読むと標準ライブラリの `*exec.Cmd.Run` であり、**棄却した** | なし |
| **`ResolveArgsOne` が製品コードから呼ばれていない** | 介入1件を前景で解決する経路が実装に無い(独立ウィンドウ方式は `IntervenePrompt` + `WriteLaunchScript` を使い、前景フォールバックは複数件まとめての `ResolveArgs` を使う)。静的解析では到達不能に見える | `docs/issues/001-modify-orchestrator-test-only-symbols.md`(同種の到達不能シンボル) |
